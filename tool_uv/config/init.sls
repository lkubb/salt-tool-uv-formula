# vim: ft=sls

{#-
    Manages the uv package configuration by

    * recursively syncing from a dotfiles repo
    * managing/serializing the config file afterwards

    Has a dependency on `tool_uv.package`_.
#}

include:
  - .sync
  - .file
