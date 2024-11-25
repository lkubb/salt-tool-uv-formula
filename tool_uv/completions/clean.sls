# vim: ft=sls

{#-
    Removes uv completions for all managed users.
#}

{%- set tplroot = tpldir.split("/")[0] %}
{%- from tplroot ~ "/map.jinja" import mapdata as uv with context %}


{%- for user in uv.users | selectattr("completions", "defined") | selectattr("completions") %}

uv shell completions are absent for user '{{ user.name }}':
  file.absent:
    - name: {{ user.home | path_join(user.completions, "_uv") }}
{%- endfor %}
