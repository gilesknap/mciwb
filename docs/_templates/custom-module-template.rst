{{ ('``' + fullname + '``') | underline }}

{%- set filtered_members = [] %}
{%- for item in members %}
    {%- if item in functions + classes + exceptions + attributes %}
        {% set _ = filtered_members.append(item) %}
    {%- endif %}
{%- endfor %}

.. automodule:: {{ fullname }}
    :members:

    {% block modules %}
    {% if modules %}
    .. rubric:: Submodules

    .. autosummary::
        :toctree:
        :template: custom-module-template.rst
        :recursive:
    {% for item in modules %}
        {{ item }}
    {%- endfor %}
    {% endif %}
    {% endblock %}

    {% block members %}
    {% if filtered_members %}
    .. rubric:: Members

    .. autosummary::
        :nosignatures:
    {% for item in filtered_members %}
        {{ item }}
    {%- endfor %}
    {% endif %}
    {% endblock %}
