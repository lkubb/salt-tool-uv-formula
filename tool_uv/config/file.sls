# vim: ft=sls

{#-
    Manages the uv package configuration.
    Has a dependency on `tool_uv.package`_.
#}

{%- set tplroot = tpldir.split("/")[0] %}
{%- set sls_package_install = tplroot ~ ".package.install" %}
{%- from tplroot ~ "/map.jinja" import mapdata as uv with context %}

include:
  - {{ sls_package_install }}


uv global configuration is managed:
  file.serialize:
    - name: {{ uv.lookup.paths.global_conf }}
    - user: root
    - group: {{ uv.lookup.rootgroup }}
    - mode: '0644'
    - makedirs: true
    - serializer: toml
    - dataset: {{ uv.config | json }}
    - require:
      - sls: {{ sls_package_install }}

{%- for user in uv.users | selectattr("uv.config", "defined") | selectattr("uv.config") %}

uv config file is managed for user '{{ user.name }}':
  file.serialize:
    - name: {{ user["_uv"].conffile }}
    - mode: '0600'
    - user: {{ user.name }}
    - group: {{ user.group }}
    - makedirs: true
    - dir_mode: '0700'
    - serializer: toml
    - dataset: {{ user.uv.config | json }}
    - require:
      - sls: {{ sls_package_install }}
{%- endfor %}
