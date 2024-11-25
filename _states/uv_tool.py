"""
Statefully manage tools installed via ``uv``.
"""

import json
import logging
import os
from pathlib import Path

from packaging.specifiers import SpecifierSet
from packaging.version import Version
from salt.exceptions import CommandExecutionError, SaltInvocationError

log = logging.getLogger(__name__)

__virtualname__ = "uv_tool"


def __virtual__():
    return __virtualname__


def installed(
    name,
    version_spec=None,
    upgrade=False,
    extras=None,
    refresh=False,
    refresh_package=None,
    force=False,
    python=None,
    system=None,
    user=None,
    **kwargs,
):
    """
    Ensure a tool is installed with uv.

    .. note::

        There are additional undocumented parameters, see the ``uv``
        execution module for details.

    name
        The name of the tool to install, if not installed already.

    version_spec
        An optional version specifier (e.g. ``==1.2.1``, ``>=2.0,<3``) to use
        when installing the tool.

    upgrade
        Ensure the tool is at the latest version ``version_spec`` allows.
        Defaults to false.

        If this is false, the state installs once and keeps the tool version
        the same after installation, unless the current version does not match
        ``version_spec``. This does not hold for dependencies and ``extras``,
        which are reinstalled each time something, e.g. ``python``, changes.

    extras
        A list of additional packages to inject into the tool's virtual environment.
        List items can be a string (the package name only) or a single-keyed
        mapping, where the key is the name of the package and the value
        a version specifier.

    refresh
        Refresh all cached data. Defaults to false.

    refresh_package
        Refresh cached data for specific package(s).

    force
        Force installation of the tool (overwrites existing executables).
        Defaults to false.

    python
        Specify the Python interpreter the tool environment
        should use. Optional.

    system
        Whether to operate on globally installed tools.
        Effectively, this defaults tool_bin_dir to ``/usr/local/bin`` and
        ``tool_dir`` to ``/opt/uv/tools``.
        If this command is executed as root and no ``user`` is specified,
        defaults to true, otherwise to false.

    tool_bin_dir
        The directory that should contain the installed executables.

    tool_dir
        The directory that contains virtual environments for installed tools.

    user
        The username to install the package for. Defaults to Salt user.
    """

    ret = {
        "name": name,
        "result": True,
        "comment": "The tool is installed as specified",
        "changes": {},
    }

    def _check_changes(curr):
        changes = {}
        requires_install = False
        if python is not None and curr["python"] != str(Path(python).resolve()):
            changes["python"] = {"old": curr["python"], "new": python}
        if extras is not None:
            extra_misses = {}
            for extra in extras if isinstance(extras, list) else [extras]:
                if isinstance(extra, str):
                    extra_pkg, extra_spec = extra, None
                else:
                    extra_pkg, extra_spec = next(iter(extra.items()))
                if extra_pkg not in curr["pkgs"]:
                    extra_misses[extra_pkg] = {
                        "old": None,
                        "new": __salt__["uv.get_latest_version"](
                            extra_pkg, spec=extra_spec
                        ),
                    }
                    continue
                if extra_spec is not None and Version(
                    curr["pkgs"][extra_pkg]
                ) not in SpecifierSet(extra_spec):
                    extra_misses[extra_pkg] = {
                        "old": curr["pkgs"][extra_pkg],
                        "new": __salt__["uv.get_latest_version"](
                            extra_pkg, spec=extra_spec
                        ),
                    }
                    continue
                if upgrade:
                    new_version = __salt__["uv.get_latest_version"](
                        extra_pkg, spec=extra_spec
                    )
                    if Version(curr["pkgs"][extra_pkg]) < Version(new_version):
                        extra_misses[extra_pkg] = {
                            "old": curr["pkgs"][extra_pkg],
                            "new": new_version,
                        }
                        continue

            if extra_misses:
                changes["extras"] = extra_misses
                requires_install = True

        if curr["install_spec"] != version_spec:
            changes["version_spec"] = {"old": curr["install_spec"], "new": version_spec}
            requires_install = True
            new_version = __salt__["uv.get_latest_version"](name, spec=version_spec)
            if Version(curr["version"]) != Version(new_version):
                changes["version"] = {"old": curr["version"], "new": new_version}

        if version_spec is not None and "version_spec" not in changes:
            if Version(curr["version"]) not in SpecifierSet(version_spec):
                # This should not happen usually since it would be a bug in uv,
                # but let's check it anyways (maybe the venv was mutated manually)
                changes["version"] = {
                    "old": curr["version"],
                    "new": __salt__["uv.get_latest_version"](name, spec=version_spec),
                }
                requires_install = True

        if upgrade and "version" not in changes:
            needs_upgrade, curr_ver, latest_ver = __salt__["uv.tool_is_outdated"](
                name,
                spec=version_spec or False,
                system=system,
                user=user,
                get_versions=True,
                **kwargs,
            )
            if needs_upgrade:
                changes["version"] = {"old": curr_ver, "new": latest_ver}
        return changes, requires_install

    try:
        if system is None and user is None and os.getuid() == 0:
            system = True
        curr = __salt__["uv.tool_list"]([name], system=system, user=user, **kwargs)
        changes = {}
        if curr:
            changes, requires_install = _check_changes(curr)
        else:
            changes["installed"] = name
            requires_install = True
        if not changes:
            return ret
        if __opts__["test"]:
            ret["result"] = None
            ret[
                "comment"
            ] = f"The tool would have been {'re' if curr else ''}installed " + (
                "globally" if system else f"for user {user}"
            )
            ret["changes"] = changes
            return ret
        cmd_kwargs = kwargs.copy()
        cmd_kwargs.update(
            {
                "python": python,
                "system": system,
                "user": user,
            }
        )
        if requires_install:
            cmd = "install"
            cmd_kwargs.update(
                {
                    "refresh": refresh,
                    "refresh_package": refresh_package,
                    "reinstall": bool(curr),
                    "force": force,
                }
            )
            if extras is not None:
                cmd_kwargs["extras"] = [
                    "".join(next(iter(extra.items())))
                    if isinstance(extra, dict)
                    else extra
                    for extra in (extras if isinstance(extras, list) else [extras])
                ]
        else:
            cmd = "upgrade"
            cmd_kwargs["upgrade"] = upgrade

        __salt__[f"uv.tool_{cmd}"](name, **cmd_kwargs)
        new = __salt__["uv.tool_list"]([name], system=system, user=user, **kwargs)
        if not new:
            raise CommandExecutionError(
                f"There were no errors during installation, but '{name}' is still not installed"
            )

        if new_changes := _check_changes(new)[0]:
            raise CommandExecutionError(
                f"Installation succeeded, but there are still pending changes: {json.dumps(new_changes)}"
            )
        ret["comment"] = f"The tool has been {'re' if curr else ''}installed " + (
            "globally" if system else f"for user {user}"
        )
        ret["changes"] = changes
    except (CommandExecutionError, SaltInvocationError) as err:
        ret["result"] = False
        ret["comment"] = str(err)

    return ret


def latest(
    name,
    version_spec=None,
    extras=None,
    force=False,
    python=None,
    system=None,
    user=None,
    **kwargs,
):
    """
    Ensure a tool is installed and at its latest version with uv.
    Alias for ``installed`` with ``upgrade=True``.

    .. note::

        There are additional undocumented parameters, see the ``uv``
        execution module for details.

    name
        The name of the tool to install, if not installed already.

    version_spec
        An optional version specifier (e.g. ``==1.2.1``, ``>=2.0,<3``) to use
        when installing the tool.

    extras
        A list of additional packages to inject into the tool's virtual environment.
        List items can be a string (the package name only) or a single-keyed
        mapping, where the key is the name of the package and the value
        a version specifier.

    force
        Force installation of the tool (overwrites existing executables).
        Defaults to false.

    python
        Specify the Python interpreter the tool environment
        should use. Optional.

    system
        Whether to operate on globally installed tools.
        Effectively, this defaults tool_bin_dir to ``/usr/local/bin`` and
        ``tool_dir`` to ``/opt/uv/tools``.
        If this command is executed as root and no ``user`` is specified,
        defaults to true, otherwise to false.

    tool_bin_dir
        The directory that should contain the installed executables.

    tool_dir
        The directory that contains virtual environments for installed tools.

    user
        The username to install the package for. Defaults to Salt user.
    """
    return installed(
        name,
        upgrade=True,
        version_spec=version_spec,
        extras=extras,
        force=force,
        python=python,
        system=system,
        user=user,
        **kwargs,
    )


def absent(name, system=None, user=None, **kwargs):
    """
    Ensure a tool is not installed with uv.

    .. note::

        There are additional undocumented parameters, see the ``uv``
        execution module for details.

    name
        The name of the tool to remove, if installed.

    system
        Whether to operate on globally installed tools.
        Effectively, this defaults tool_bin_dir to ``/usr/local/bin`` and
        ``tool_dir`` to ``/opt/uv/tools``.
        If this command is executed as root and no ``user`` is specified,
        defaults to true, otherwise to false.

    tool_bin_dir
        The directory that should contain the installed executables.

    tool_dir
        The directory that contains virtual environments for installed tools.

    user
        The username to remove the package for. Defaults to Salt user.
    """

    ret = {
        "name": name,
        "result": True,
        "comment": "The tool is already absent",
        "changes": {},
    }

    try:
        if system is None and user is None and os.getuid() == 0:
            system = True
        if not __salt__["uv.tool_is_installed"](
            name, system=system, user=user, **kwargs
        ):
            return ret
        if __opts__["test"]:
            ret["result"] = None
            ret["comment"] = "The tool would have been removed " + (
                "globally" if system else f"for user {user}"
            )
            ret["changes"] = {"removed": name}
            return ret
        __salt__["uv.tool_remove"](name, system=system, user=user, **kwargs)
        if __salt__["uv.tool_is_installed"](name, system=system, user=user, **kwargs):
            raise CommandExecutionError(
                "There were no errors during uninstallation, but the tool is still reported as installed"
            )
        ret["comment"] = "The tool has been removed " + (
            "globally" if system else f"for user {user}"
        )
        ret["changes"] = {"removed": name}
    except (CommandExecutionError, SaltInvocationError) as err:
        ret["result"] = False
        ret["comment"] = str(err)

    return ret
