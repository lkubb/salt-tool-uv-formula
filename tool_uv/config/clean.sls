# vim: ft=sls

{#-
    Removes the configuration of the uv package.
#}

{%- set tplroot = tpldir.split("/")[0] %}
{%- from tplroot ~ "/map.jinja" import mapdata as uv with context %}


uv global config is absent:
  file.absent:
    - name: {{ uv.lookup.paths.global_conf }}

{%- for user in uv.users | selectattr("uv.config", "defined") | selectattr("uv.config") %}

uv config file is cleaned for user '{{ user.name }}':
  file.absent:
    - name: {{ user["_uv"].conffile }}

uv config dir is absent for user '{{ user.name }}':
  file.absent:
    - name: {{ user["_uv"].confdir }}
{%- endfor %}
