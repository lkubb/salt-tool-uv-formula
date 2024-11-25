# vim: ft=sls

{%- set tplroot = tpldir.split("/")[0] %}
{%- from tplroot ~ "/map.jinja" import mapdata as uv with context %}

include:
  - {{ tplroot }}.package.install


{%- for package, config in uv.tools.items() %}

uv tool '{{ package }}' is installed globally:
  uv_tool.installed:
    - name: {{ package }}
    - system: true
{%-   for param, val in config.items() %}
    - {{ param }}: {{ val | json }}
{%-   endfor %}
    - require:
      - uv setup is completed
{%- endfor %}


{%- for user in uv.users | selectattr("uv.tools", "defined") %}
{%-   for package, config in user.uv.tools.items() %}

uv tool '{{ package }}' is installed for user '{{ user.name }}':
  uv_tool.installed:
    - name: {{ package }}
    - user: {{ user.name }}
{%-     for param, val in config.items() %}
    - {{ param }}: {{ val | json }}
{%-     endfor %}
    - require:
      - uv setup is completed
{%-   endfor %}
{%- endfor %}
