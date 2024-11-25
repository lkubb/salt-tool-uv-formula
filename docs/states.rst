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


