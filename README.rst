|code_ci| |docs_ci| |coverage| |pypi_version| |license|


Minecraft Interactive World Builder
===================================

This project is intended as a fun way to learn the Python Programming Language.

Experienced Python programmers can also use this library to create
Minecraft worlds with interactive Python features.


For the Reddit discussion see  
`HERE <https://www.reddit.com/r/Minecraftbuilds/comments/11rqauh/build_things_using_python>`_

Quick Start
-----------

To get started learning Python, see
`Introduction <https://gilesknap.github.io/mciwb/main/user/tutorials/00-prereq.html>`_

For existing Python developers, see
`API documentation  <https://gilesknap.github.io/mciwb/main/user/reference/api.html>`_

Example Build
-------------

The pagoda and castle with working portcullis were all created programmatically
with Python and the current version of MCIWB.

.. figure:: https://gilesknap.github.io/mciwb/main/_images/castle.png
   :alt: castle
   :align: center
   :width: 600px

   Example Build

Goals
-----

Minecraft Interactive World Builder's goals are:

 - Use Python to create anything inside of Minecraft worlds.
 - Call Python code when events occur inside the world.
 - Use an iPython prompt to interact with the world by typing Python commands
 - Have your player inside the world execute Python code by placing command
   signs or activating switches/levers with Python actions.

All instructions on how to set up a Minecraft Server and the Python developer
environment are included. There are step by step tutorials to
introduce Python Programming and the features of Minecraft Interactive World
Builder.

.. note::

    This is a work in progress. There are now enough tutorials to learn the
    fundamentals of Python and enough functionality to have some fun
    interacting with Minecraft from Python code.

    I will continue to expand the tutorials and add more features to the
    library.

Credits
-------

This project would not be possible without `mcipc <https://github.com/conqp/mcipc/>`_,
which provides the client library for Minecraft RCON.

Links
-----

============== ==============================================================
PyPI           ``pip install mciwb``
Source code    https://github.com/gilesknap/mciwb
Documentation  https://gilesknap.github.io/mciwb
Releases       https://github.com/gilesknap/mciwb/releases
============== ==============================================================


.. |code_ci| image:: https://github.com/gilesknap/mciwb/actions/workflows/code.yml/badge.svg?branch=main
    :target: https://github.com/gilesknap/mciwb/actions/workflows/code.yml
    :alt: Code CI

.. |docs_ci| image:: https://github.com/gilesknap/mciwb/actions/workflows/docs.yml/badge.svg?branch=main
    :target: https://github.com/gilesknap/mciwb/actions/workflows/docs.yml
    :alt: Docs CI

.. |coverage| image:: https://app.codacy.com/project/badge/Coverage/4c514b64299e4ccd8c569d3e787245c7
    :target: https://www.codacy.com/gh/gilesknap/mciwb/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=gilesknap/mciwb&amp;utm_campaign=Badge_Coverage
    :alt: Test Coverage

.. |pypi_version| image:: https://img.shields.io/pypi/v/mciwb.svg
    :target: https://pypi.org/project/mciwb
    :alt: Latest PyPI version

.. |license| image:: https://img.shields.io/badge/License-Apache%202.0-blue.svg
    :target: https://opensource.org/licenses/Apache-2.0
    :alt: Apache License

..
    Anything below this line is used when viewing README.rst and will be replaced
    when included in index.rst

