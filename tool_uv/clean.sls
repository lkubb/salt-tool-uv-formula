# vim: ft=sls

{#-
    *Meta-state*.

    Undoes everything performed in the ``tool_uv`` meta-state
    in reverse order.
#}

include:
  - .packages.clean
  - .completions.clean
  - .config.clean
  - .package.clean
