.. _readme:

uv Formula
==========

Manages uv in the user environment.

.. contents:: **Table of Contents**
   :depth: 1

Usage
-----
Applying ``tool_uv`` will make sure ``uv`` is configured as specified.

Execution and state module
~~~~~~~~~~~~~~~~~~~~~~~~~~
This formula provides a custom execution module and state to manage packages installed with uv. The functions are self-explanatory, please see the source code or the rendered docs at :ref:`em_uv` and :ref:`sm_uv`.

Configuration
-------------

This formula
~~~~~~~~~~~~
The general configuration structure is in line with all other formulae from the `tool` suite, for details see :ref:`toolsuite`. An example pillar is provided, see :ref:`pillar.example`. Note that you do not need to specify everything by pillar. Often, it's much easier and less resource-heavy to use the ``parameters/<grain>/<value>.yaml`` files for non-sensitive settings. The underlying logic is explained in :ref:`map.jinja`.

User-specific
^^^^^^^^^^^^^
The following shows an example of ``tool_uv`` per-user configuration. If provided by pillar, namespace it to ``tool_global:users`` and/or ``tool_uv:users``. For the ``parameters`` YAML file variant, it needs to be nested under a ``values`` parent key. The YAML files are expected to be found in

1. ``salt://tool_uv/parameters/<grain>/<value>.yaml`` or
2. ``salt://tool_global/parameters/<grain>/<value>.yaml``.

.. code-block:: yaml

  user:

      # Force the usage of XDG directories for this user.
    xdg: true

      # Put shell completions into this directory, relative to user home.
    completions: '.config/zsh/completions'

      # Sync this user's config from a dotfiles repo.
      # The available paths and their priority can be found in the
      # rendered `config/sync.sls` file (currently, @TODO docs).
      # Overview in descending priority:
      # salt://dotconfig/<minion_id>/<user>/uv
      # salt://dotconfig/<minion_id>/uv
      # salt://dotconfig/<os_family>/<user>/uv
      # salt://dotconfig/<os_family>/uv
      # salt://dotconfig/default/<user>/uv
      # salt://dotconfig/default/uv
    dotconfig:              # can be bool or mapping
      file_mode: '0600'     # default: keep destination or salt umask (new)
      dir_mode: '0700'      # default: 0700
      clean: false          # delete files in target. default: false

      # Persist environment variables used by this formula for this
      # user to this file (will be appended to a file relative to $HOME)
    persistenv: '.config/zsh/zshenv'

      # Add runcom hooks specific to this formula to this file
      # for this user (will be appended to a file relative to $HOME)
    rchook: '.config/zsh/zshrc'

      # This user's configuration for this formula. Will be overridden by
      # user-specific configuration in `tool_uv:users`.
      # Set this to `false` to disable configuration for this user.
    uv:
        # Per-user uv configuration
      config: {}
        # A mapping of tools to install for this user to parameters for
        # `uv_tool.installed` state.
      tools: {}

Formula-specific
^^^^^^^^^^^^^^^^

.. code-block:: yaml

  tool_uv:

      # Specify an explicit version (works on most Linux distributions) or
      # keep the packages updated to their latest version on subsequent runs
      # by leaving version empty or setting it to 'latest'
      # (again for Linux, brew does that anyways).
    version: latest
      # Global uv configuration
    config: {}
      # Choose how uv is installed. Either `releases` (from GitHub releases, default)
      # or `pkg` (requires a `uv` package to be installable via the package manager,
      # works with Homebrew at least)
    install_method: releases
      # A mapping of tools to install globally to parameters for `uv_tool.installed`
      # state.
    tools: {}

      # Default formula configuration for all users.
    defaults:
      config: default value for all users

Config file serialization
~~~~~~~~~~~~~~~~~~~~~~~~~
This formula serializes configuration into a config file. A default one is provided with the formula, but can be overridden via the TOFS pattern. See :ref:`tofs_pattern` for details.

Dotfiles
~~~~~~~~
``tool_uv.config.sync`` will recursively apply templates from

* ``salt://dotconfig/<minion_id>/<user>/uv``
* ``salt://dotconfig/<minion_id>/uv``
* ``salt://dotconfig/<os_family>/<user>/uv``
* ``salt://dotconfig/<os_family>/uv``
* ``salt://dotconfig/default/<user>/uv``
* ``salt://dotconfig/default/uv``

to the user's config dir for every user that has it enabled (see ``user.dotconfig``). The target folder will not be cleaned by default (ie files in the target that are absent from the user's dotconfig will stay).

The URL list above is in descending priority. This means user-specific configuration from wider scopes will be overridden by more system-specific general configuration.


Available states
----------------

The following states are found in this formula:

.. contents::
   :local:


``tool_uv``
~~~~~~~~~~~
*Meta-state*.

Performs all operations described in this formula according to the specified configuration.


``tool_uv.package``
~~~~~~~~~~~~~~~~~~~
Installs the uv package only.


``tool_uv.config``
~~~~~~~~~~~~~~~~~~
Manages the uv package configuration by

* recursively syncing from a dotfiles repo
* managing/serializing the config file afterwards

Has a dependency on `tool_uv.package`_.


``tool_uv.config.file``
~~~~~~~~~~~~~~~~~~~~~~~
Manages the uv package configuration.
Has a dependency on `tool_uv.package`_.


``tool_uv.config.sync``
~~~~~~~~~~~~~~~~~~~~~~~
Syncs the uv package configuration
with a dotfiles repo.
Has a dependency on `tool_uv.package`_.


``tool_uv.completions``
~~~~~~~~~~~~~~~~~~~~~~~
Installs uv completions for all managed users.
Has a dependency on `tool_uv.package`_.


``tool_uv.packages``
~~~~~~~~~~~~~~~~~~~~
Installs uv tools globally and per-user.


``tool_uv.clean``
~~~~~~~~~~~~~~~~~
*Meta-state*.

Undoes everything performed in the ``tool_uv`` meta-state
in reverse order.


``tool_uv.package.clean``
~~~~~~~~~~~~~~~~~~~~~~~~~
Removes the uv package.
Has a dependency on `tool_uv.config.clean`_.


``tool_uv.config.clean``
~~~~~~~~~~~~~~~~~~~~~~~~
Removes the configuration of the uv package.


``tool_uv.completions.clean``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Removes uv completions for all managed users.


``tool_uv.packages.clean``
~~~~~~~~~~~~~~~~~~~~~~~~~~
Removes configured uv tools globally and per-user.



Development
-----------

Contributing to this repo
~~~~~~~~~~~~~~~~~~~~~~~~~

Commit messages
^^^^^^^^^^^^^^^

Commit message formatting is significant.

Please see `How to contribute <https://github.com/saltstack-formulas/.github/blob/master/CONTRIBUTING.rst>`_ for more details.

pre-commit
^^^^^^^^^^

`pre-commit <https://pre-commit.com/>`_ is configured for this formula, which you may optionally use to ease the steps involved in submitting your changes.
First install  the ``pre-commit`` package manager using the appropriate `method <https://pre-commit.com/#installation>`_, then run ``bin/install-hooks`` and
now ``pre-commit`` will run automatically on each ``git commit``.

.. code-block:: console

  $ bin/install-hooks
  pre-commit installed at .git/hooks/pre-commit
  pre-commit installed at .git/hooks/commit-msg

State documentation
~~~~~~~~~~~~~~~~~~~
There is a script that semi-autodocuments available states: ``bin/slsdoc``.

If a ``.sls`` file begins with a Jinja comment, it will dump that into the docs. It can be configured differently depending on the formula. See the script source code for details currently.

This means if you feel a state should be documented, make sure to write a comment explaining it.
