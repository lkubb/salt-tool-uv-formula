# vim: ft=sls

{#-
    Removes the uv package.
    Has a dependency on `tool_uv.config.clean`_.
#}

{%- set tplroot = tpldir.split("/")[0] %}
{%- set sls_config_clean = tplroot ~ ".config.clean" %}
{%- from tplroot ~ "/map.jinja" import mapdata as uv with context %}

include:
  - {{ sls_config_clean }}


{%- if uv.install_method == "pkg" %}

uv is removed:
  pkg.removed:
    - name: {{ uv.lookup.pkg.name }}
    - require:
      - sls: {{ sls_config_clean }}

{%- elif uv.install_method == "releases" %}

uv is removed:
  file.absent:
    - names:
      - {{ uv.lookup.paths.install_dir }}
      - {{ uv.lookup.paths.bin_dir | path_join("uv") }}
      - {{ uv.lookup.paths.bin_dir | path_join("uvx") }}
    - require:
      - sls: {{ sls_config_clean }}

{%- else %}
{%-   do salt["test.exception"]("Unknown install_method: {}".format(uv.install_method)) %}
{%- endif %}
