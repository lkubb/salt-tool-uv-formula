# vim: ft=sls

{#-
    Removes configured uv tools globally and per-user.
#}

{%- set tplroot = tpldir.split("/")[0] %}
{%- from tplroot ~ "/map.jinja" import mapdata as uv with context %}


{%- for package in uv.tools %}

uv package '{{ package }}' is removed globally:
  uv_tool.absent:
    - name: {{ package }}
    - system: true
{%- endfor %}


{%- for user in uv.users | selectattr("uv.tools", "defined") %}
{%-   for package in user.uv.tools %}

uv package '{{ package }}' is removed for user '{{ user.name }}':
  uv_tool.absent:
    - name: {{ package }}
    - user: {{ user.name }}
{%-   endfor %}
{%- endfor %}
