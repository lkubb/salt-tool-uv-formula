# vim: ft=sls

{%- set tplroot = tpldir.split("/")[0] %}
{%- from tplroot ~ "/map.jinja" import mapdata as uv with context %}
{%- set version = uv.get("version") or "latest" %}

{%- if uv.install_method == "pkg" %}

uv is installed:
  pkg.installed:
    - name: {{ uv.lookup.pkg.name }}
    - version: {{ version }}
    - require_in:
      - uv setup is completed

{%- elif uv.install_method == "releases" %}
{%-   if version == "latest" %}
{%-     set version = salt["cmd.run_stdout"](
          "curl -ILs -o /dev/null -w %{url_effective} '" ~ uv.lookup.pkg_src.latest ~
          "' | grep -o '[^/]*$' | sed 's/v//'",
          python_shell=true
        )
-%}
{%-   endif %}
{%-   set kernel_libc = uv.lookup.kernel %}
{%-   if uv.lookup.libc %}
{%-     set kernel_libc = kernel_libc ~ "-{}".format(uv.lookup.libc) %}
{%-   endif %}

uv is installed:
  file.managed:
    - name: {{ uv.lookup.paths.bin }}
    - source: {{ uv.lookup.pkg_src.source.format(version=version, arch=uv.lookup.arch, typ=uv.lookup.typ, kernel_libc=kernel_libc) }}
    - source_hash: {{ uv.lookup.pkg_src.source_hash.format(version=version, arch=uv.lookup.arch, typ=uv.lookup.typ, kernel_libc=kernel_libc) }}
    - user: root
    - group: {{ uv.lookup.rootgroup }}
    - mode: '0755'
    - makedirs: true
    - require_in:
      - uv setup is completed

{%- else %}
{%-   do salt["test.exception"]("Unknown install_method: {}".format(uv.install_method)) %}
{%- endif %}

uv setup is completed:
  test.nop:
    - name: Hooray, uv setup has finished.
