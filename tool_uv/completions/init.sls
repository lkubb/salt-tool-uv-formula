# vim: ft=sls

{#-
    Installs uv completions for all managed users.
    Has a dependency on `tool_uv.package`_.
#}

{%- set tplroot = tpldir.split("/")[0] %}
{%- set sls_package_install = tplroot ~ ".package.install" %}
{%- from tplroot ~ "/map.jinja" import mapdata as uv with context %}

include:
  - {{ sls_package_install }}


{#- Homebrew manages the completions already. #}
{%- if uv.install_method != "pkg" or grains.kernel != "Darwin" %}
{%-   for user in uv.users | selectattr("completions", "defined") | selectattr("completions") %}

Completions directory for uv is available for user '{{ user.name }}':
  file.directory:
    - name: {{ user.home | path_join(user.completions) }}
    - user: {{ user.name }}
    - group: {{ user.group }}
    - mode: '0700'
    - makedirs: true

uv shell completions are available for user '{{ user.name }}':
  cmd.run:
    - name: uv generate-shell-completion {{ user.shell }} > {{ user.home | path_join(user.completions, "_uv") }}
    - creates: {{ user.home | path_join(user.completions, "_uv") }}
    - onchanges:
      - uv is installed
    - runas: {{ user.name }}
    - require:
      - uv is installed
      - Completions directory for uv is available for user '{{ user.name }}'
{%-   endfor %}
{%- endif %}
