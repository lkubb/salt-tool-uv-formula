"""
Interface with ``uv``.

Common parameters
-----------------
In addition to the documented parameters, there are some common
parameters that have an effect.

General
~~~~~~~
Each function additionally respects:

env
    A mapping of environment variables to set when calling ``uv``.

native_tls
    Whether to load TLS certificates from the platform's native certificate store.

    By default, uv loads certificates from the bundled ``webpki-roots`` crate. The ``webpki-roots`` are a reliable
    set of trust roots from Mozilla, and including them in uv improves portability and performance (especially on
    macOS).

    However, in some cases, you may want to use the platform's native certificate store, especially if you're
    relying on a corporate trust root (e.g., for a mandatory proxy) that's included in your system's certificate
    store.

    [env: UV_NATIVE_TLS=]

offline
    Disable network access.

    When disabled, uv will only use locally cached data and locally available files.

no_cache
    Avoid reading from or writing to the cache, instead using a temporary directory
    for the duration of the operation.

cache_dir
    Path to the cache directory.

directory
    Change to the given directory prior to running the command.

    Relative paths are resolved with the given directory as the base.

    See ``project`` to only change the project root directory.

project
    Run the command within the given project directory.

    All ``pyproject.toml``, ``uv.toml``, and ``.python-version`` files will be discovered by walking up the directory
    tree from the project root, as will the project's virtual environment (``.venv``).

    Other command-line arguments (such as relative paths) will be resolved relative to the current working
    directory.

    See ``directory`` to change the working directory entirely.

config_file
    The path to a ``uv.toml`` file to use for configuration.

    While uv configuration can be included in a ``pyproject.toml`` file, it is not allowed in this context.

    [env: UV_CONFIG_FILE=]

no_config
    Avoid discovering configuration files (``pyproject.toml``, ``uv.toml``).

    Normally, configuration files are discovered in the current directory, parent directories, or user
    configuration directories.

    [env: UV_NO_CONFIG=]

python_preference
    Whether to prefer uv-managed or system Python installations.

    By default, uv prefers using Python versions it manages. However, it will use system Python installations if
    a uv-managed Python is not installed. This option allows prioritizing or ignoring system Python
    installations.

    [env: UV_PYTHON_PREFERENCE=]

    Possible values:
    - only-managed: Only use managed Python installations; never use system Python installations
    - managed:      Prefer managed Python installations over system Python installations
    - system:       Prefer system Python installations over managed Python installations
    - only-system:  Only use system Python installations; never use managed Python installations

no_python_downloads
    Disable automatic downloads of Python. [env: "UV_PYTHON_DOWNLOADS=never"]

Tool-specific
~~~~~~~~~~~~~
Each ``tool_*`` function additionally respects:

tool_bin_dir
    The target directory for installed tool executables.
    Effectively sets the ``UV_TOOL_BIN_DIR`` variable.
    Used by default when installing system-wide packages, where it is
    set to ``/usr/local/bin``.

tool_dir
    The target directory for installed tool virtual environments.
    Effectively sets the ``UV_TOOL_DIR`` variable.
    Used by default when installing system-wide packages, where it is
    set to ``/opt/uv/tools``.
"""

import logging
import os
import re
import shlex
from pathlib import Path

import salt.utils.json
import salt.utils.platform
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from salt.exceptions import CommandExecutionError, SaltInvocationError

__virtualname__ = "uv"

log = logging.getLogger(__name__)

LIST_REGEX = re.compile(
    r"^(?P<tool>\S+)\s+v?(?P<version>\S+)(?:\s+\[required: (?P<req>[^\]]*)\])?\s+\((?P<venv>.*)\)$"
)


def __virtual__():
    # In case a user has installed uv, but it's not installed globally,
    # we still want to load, so don't try to discover uv in the current $PATH.
    return __virtualname__


def _uv(
    cmd,
    *params,
    options=None,
    native_tls=False,
    offline=False,
    no_cache=False,
    cache_dir=None,
    directory=None,
    project=None,
    config_file=None,
    no_config=None,
    python_preference=None,
    no_python_downloads=False,
    user=None,
    env=None,
    json=False,
    **kwargs,
):
    if kwargs and not all(kwarg.startswith("__") for kwarg in kwargs):
        raise SaltInvocationError(
            "The following keyword arguments are invalid: "
            + ", ".join(kwarg for kwarg in kwargs if not kwarg.startswith("__"))
        )
    full_cmd = ["uv"] + cmd + (options or [])

    for bool_opt, bool_val in (
        ("no-cache", no_cache),
        ("no-config", no_config),
        ("native-tls", native_tls),
        ("offline", offline),
        ("no-python-downloads", no_python_downloads),
    ):
        if bool_val is True:
            full_cmd.append(f"--{bool_opt}")

    for opt, val in (
        ("cache-dir", cache_dir),
        ("directory", directory),
        ("project", project),
        ("config-file", config_file),
        ("python-preference", python_preference),
    ):
        if val is not None:
            full_cmd.extend((f"--{opt}", val))

    full_cmd.extend(params)

    log.debug("Running command %r with env %r and user %s", full_cmd, env, user)
    res = __salt__["cmd.run_all"](shlex.join(full_cmd), env=env, runas=user)
    if res["retcode"]:
        raise CommandExecutionError(
            f"Failed running '{shlex.join(full_cmd)}': {res['stderr'] or res['stdout']}"
        )
    if not json:
        return res["stdout"]
    return salt.utils.json.loads(res["stdout"])


def _uv_tool(
    cmd,
    *params,
    system=None,
    tool_bin_dir=None,
    tool_dir=None,
    env=None,
    user=None,
    **kwargs,
):
    env = env or {}
    if system is None and user is None and os.getuid() == 0:
        system = True
    if system:
        tool_bin_dir = tool_bin_dir or "/usr/local/bin"
        tool_dir = tool_dir or "/opt/uv/tools"
    if tool_bin_dir is not None:
        env["UV_TOOL_BIN_DIR"] = tool_bin_dir
    if tool_dir is not None:
        env["UV_TOOL_DIR"] = tool_dir
    return _uv(["tool", cmd], *params, env=env, user=user, **kwargs)


def tool_is_installed(name, **kwargs):
    """
    Checks whether a tool with this name is installed by uv.

    CLI Example:

    .. code-block:: bash

        salt '*' uv.tool_is_installed copier user=user

    name
        The name of the package to check.

    system
        Whether to operate on globally installed tools.
        Effectively, this defaults tool_bin_dir to ``/usr/local/bin`` and
        ``tool_dir`` to ``/opt/uv/tools``.
        If this command is executed as root and no ``user`` is specified,
        defaults to true, otherwise to false.

    user
        The username to check installation status for. Defaults to Salt user.
    """
    return bool(tool_list([name], **kwargs))


def get_latest_version(name, spec=None, endpoint="https://pypi.org/pypi/{}/json"):
    """
    Lookup the latest stable release of a package.

    CLI Example:

    .. code-block:: bash

        salt '*' uv.get_latest_version copier
        salt '*' uv.get_latest_version copier '<10'

    name
        The name of the package to look up.

    spec
        A version specifier to restrict the versions to consider.
        If unspecified, returns the latest stable release.

    endpoint
        JSON endpoint to query, containing a marker for the package name.
        Defaults to ``https://pypi.org/pypi/{}/json``.
    """
    # for simplicity, this uses the pypi json endpoint,
    # not the simple API (ironically) because it's html
    # the latter would be preferred for compatibility reasons
    api_url = endpoint.format(name)
    log.info("Looking up version for %s at %s", name, api_url)
    response = __salt__["http.query"](api_url, decode=True, decode_type="json")
    if spec is None:
        latest = response["dict"]["info"]["version"]
    else:
        version_spec = SpecifierSet(spec)
        latest = next(
            iter(
                sorted(
                    (
                        version
                        for version in response["dict"]["releases"]
                        if (parsed := Version(version)) in version_spec
                        and not parsed.is_prerelease
                        and not parsed.is_devrelease
                        and not parsed.is_postrelease
                    ),
                    reverse=True,
                )
            )
        )
    log.info("Latest version: %s", latest)
    return latest


def tool_is_outdated(
    name,
    spec=None,
    endpoint="https://pypi.org/pypi/{}/json",
    get_versions=False,
    user=None,
    **kwargs,
):
    """
    Checks whether a tool installed with uv can be upgraded.

    CLI Example:

    .. code-block:: bash

        salt '*' uv.tool_is_outdated copier user=user

    name
        The name of the package to check.

    spec
        A version specification the latest check should fulfill.
        If unspecified, either defaults to the specification the tool was
        installed with initially or nothing.

    endpoint
        JSON endpoint to query, containing a marker for the package name.
        Defaults to ``https://pypi.org/pypi/{}/json``.

    get_versions
        Return a tuple of result, current version and latest version.
        Defaults to false.

    system
        Whether to operate on globally installed tools.
        Effectively, this defaults tool_bin_dir to ``/usr/local/bin`` and
        ``tool_dir`` to ``/opt/uv/tools``.
        If this command is executed as root and no ``user`` is specified,
        defaults to true, otherwise to false.

    user
        The username to check the package for. Defaults to Salt user.
    """

    current = tool_list([name], user=user, **kwargs)
    if not current:
        raise CommandExecutionError(f"{name} is not installed for user {user}.")

    if spec is False:
        spec = None
    elif spec is None:
        spec = current["install_spec"] or None

    latest = get_latest_version(name, spec=spec, endpoint=endpoint)

    res = Version(current["version"]) < Version(latest)
    if get_versions:
        return res, current["version"], latest
    return res


def tool_install(
    name,
    extras=None,
    with_requirements=None,
    refresh=False,
    refresh_package=None,
    reinstall=False,
    reinstall_package=None,
    force=False,
    **kwargs,
):
    """
    Installs tool with uv.

    CLI Example:

    .. code-block:: bash

        salt '*' uv.tool_install copier user=user
        salt '*' uv.tool_install copier extras='[copier-templates-extensions]' user=user

    name
        The name of the package to install.

    extras
        Inject additional packages into the tool's virtual environment.

    with_requirements
        Inject additional packages into the tool's virtual environment
        by reading them from ``requirements.txt`` file(s).

    refresh
        Refresh all cached data. Defaults to false.

    refresh_package
        Refresh cached data for specific package(s).

    reinstall
        Reinstall all packages, regardless of whether they're already installed. Implies ``refresh``.

    reinstall_package
        Reinstall specific package(s), regardless of whether  they're already installed. Implies ``--refresh-package``.

    force
        Force installation of the tool (overwrites existing executables).
        Defaults to false.

    upgrade
        Allow package upgrades, ignoring pinned versions in any existing output file.

    upgrade_package
        Allow upgrades for specific package(s), ignoring pinned versions in any existing output file.

    python
        Specify the Python interpreter the tool environment
        should use. Optional.

    system
        Whether to operate on globally installed tools.
        Effectively, this defaults tool_bin_dir to ``/usr/local/bin`` and
        ``tool_dir`` to ``/opt/uv/tools``.
        If this command is executed as root and no ``user`` is specified,
        defaults to true, otherwise to false.

    user
        The username to install the package for. Defaults to Salt user.
    """
    options = []
    if extras:
        for extra in extras if isinstance(extras, list) else [extras]:
            options.extend(("--with", extra))
    if with_requirements:
        for req in (
            with_requirements
            if isinstance(with_requirements, list)
            else [with_requirements]
        ):
            options.extend(("--with-requirements", req))
    if refresh_package:
        for pkg in (
            refresh_package if isinstance(refresh_package, list) else [refresh_package]
        ):
            options.extend(("--refresh-package", pkg))
    if reinstall_package:
        for pkg in (
            reinstall_package
            if isinstance(reinstall_package, list)
            else [reinstall_package]
        ):
            options.extend(("--reinstall-package", pkg))
    if refresh:
        options.append("--refresh")
    if reinstall:
        options.append("--reinstall")
    if force:
        options.append("--force")
    _tool_install_upgrade("install", name, **kwargs, options=options)
    return True


def tool_list(name=None, system=None, user=None, **kwargs):
    """
    List tools installed by uv.

    CLI Example:

    .. code-block:: bash

        salt '*' uv.tool_list user=user

    name
        A name or list of names of tools to list/show information for.
        If unspecified, lists all tools.

    system
        Whether to operate on globally installed tools.
        Effectively, this defaults tool_bin_dir to ``/usr/local/bin`` and
        ``tool_dir`` to ``/opt/uv/tools``.
        If this command is executed as root and no ``user`` is specified,
        defaults to true, otherwise to false.

    user
        The username to list installed packages for. Defaults to Salt user.
    """
    out = _uv_tool(
        "list",
        **kwargs,
        options=["--show-paths", "--show-version-specifiers"],
        system=system,
        user=user,
    )
    if "No tools installed" in out:
        return {}
    tools = {}
    if name is not None and not isinstance(name, list):
        name = [name]
    for line in out.splitlines():
        if line.startswith("-"):
            # lists executables
            continue
        if not (match := LIST_REGEX.match(line)):
            log.error(f"Failed parsing uv output: {line}")
            continue
        tool, version, spec, venv = match.groups()
        if name is not None and tool not in name:
            continue
        venv_pkgs = {}
        pip_list_opts = kwargs.copy()
        pip_list_opts["directory"] = venv
        for pkg in _uv(
            ["pip", "list"],
            **pip_list_opts,
            options=["--format", "json"],
            user=user,
            json=True,
        ):
            venv_pkgs[pkg["name"]] = pkg["version"]
        venv_py = (Path(venv) / "bin" / "python").resolve()
        venv_pyver = __salt__["cmd.run"](
            shlex.join((str(venv_py), "--version")), runas=user
        ).rsplit(" ", maxsplit=1)[-1]
        tools[tool] = {
            "python": str(venv_py),
            "python_version": venv_pyver,
            "install_spec": spec or None,
            "version": version,
            "venv_path": venv,
            "pkgs": venv_pkgs,
        }
    if name is not None and len(name) == 1 and tools:
        return tools[name[0]]
    return tools


def tool_remove(name, **kwargs):
    """
    Uninstalls tool installed by uv.

    CLI Example:

    .. code-block:: bash

        salt '*' uv.tool_remove copier user=user

    name
        The name of the package to remove.

    system
        Whether to operate on globally installed tools.
        Effectively, this defaults tool_bin_dir to ``/usr/local/bin`` and
        ``tool_dir`` to ``/opt/uv/tools``.
        If this command is executed as root and no ``user`` is specified,
        defaults to true, otherwise to false.

    user
        The username to remove the package for. Defaults to Salt user.
    """
    _uv_tool("uninstall", name, **kwargs)
    return True


def tool_remove_all(**kwargs):
    """
    Uninstalls all tool installed by uv.

    CLI Example:

    .. code-block:: bash

        salt '*' uv.tool_remove_all user=user

    system
        Whether to operate on globally installed tools.
        Effectively, this defaults tool_bin_dir to ``/usr/local/bin`` and
        ``tool_dir`` to ``/opt/uv/tools``.
        If this command is executed as root and no ``user`` is specified,
        defaults to true, otherwise to false.

    user
        The username to remove all tools for. Defaults to Salt user.
    """
    _uv_tool("uninstall", **kwargs, options=["--all"])
    return True


def tool_upgrade(name, **kwargs):
    """
    Upgrades tool installed by uv.
    If the installation command included a version specifier,
    does not upgrade beyond it.
    If you want to upgrade beyond, reinstall the tool with a
    different specifier.

    CLI Example:

    .. code-block:: bash

        salt '*' uv.upgrade copier user=user

    name
        The name of the package to upgrade.

    python
        Specify the Python interpreter the tool environment
        should use. Optional.

    upgrade
        Allow package upgrades, ignoring pinned versions in any existing output file.

    upgrade_package
        Allow upgrades for specific package(s), ignoring pinned versions in any existing output file.

    system
        Whether to operate on globally installed tools.
        Effectively, this defaults tool_bin_dir to ``/usr/local/bin`` and
        ``tool_dir`` to ``/opt/uv/tools``.
        If this command is executed as root and no ``user`` is specified,
        defaults to true, otherwise to false.

    user
        The username to upgrade the package for. Defaults to Salt user.
    """
    return _tool_install_upgrade("upgrade", name, **kwargs)


def tool_upgrade_all(**kwargs):
    """
    Upgrades all tools installed by uv.
    If the installation command included a max version specifier,
    does not upgrade beyond it.
    If you want to upgrade beyond, reinstall the tool with a
    different specifier.

    CLI Example:

    .. code-block:: bash

        salt '*' uv.upgrade_all user=user

    python
        Specify the Python interpreter the tool environments
        should use. Optional.

    upgrade
        Allow package upgrades, ignoring pinned versions in any existing output file.

    upgrade_package
        Allow upgrades for specific package(s), ignoring pinned versions in any existing output file.

    system
        Whether to operate on globally installed tools.
        Effectively, this defaults tool_bin_dir to ``/usr/local/bin`` and
        ``tool_dir`` to ``/opt/uv/tools``.
        If this command is executed as root and no ``user`` is specified,
        defaults to true, otherwise to false.

    user
        The username to upgrade all tools for. Defaults to Salt user.
    """
    return _tool_install_upgrade("upgrade", **kwargs, options=["--all"])


def _tool_install_upgrade(
    cmd, *args, python=None, upgrade=False, upgrade_package=None, options=None, **kwargs
):
    # There's a bunch of options common to the install/upgrade interface,
    # consider their relevance.
    options = options or []
    if python is not None:
        options.extend(("--python", python))
    if upgrade:
        options.append("--upgrade")
    if upgrade_package:
        for pkg in (
            upgrade_package if isinstance(upgrade_package, list) else [upgrade_package]
        ):
            options.extend(("--upgrade-package", pkg))

    _uv_tool(cmd, *args, **kwargs, options=options)
    return True
