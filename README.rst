|code_ci| |docs_ci| |coverage| |quality| |pypi_version| |license|


Minecraft Interactive World Builder
===================================

.. warning::
    
    This is a work in progress. There are now enough tutorials to learn the
    fundamentals of Python and enough functionality to have some fun
    interacting with Minecraft from Python code.

    I will continue to expand the tutorials and add more features to the
    library.
    
This project is intended as a fun way to learn the Python Programming Language.
However, experienced Python programmers can also use this library to create 
Minecraft worlds with interactive Python features 
(TODO: API documentation is pending).

Minecraft Interactive World Builder has the following features:

 - Use Python to create anything inside of Minecraft worlds. 
 - Call Python code when events occur inside the world.
 - Use an iPython prompt to interact with the world by typing Python commands
 - Have your player inside the world execute Python code by placing command 
   signs or activating switches/levers with Python actions.

All instructions on how to set up a Minecraft Server and the Python developer
environment are included. There are step by step tutorials to
introduce Python Programming and the features of Minecraft Interactive World
Builder.


See 
`Introduction <https://gilesknap.github.io/mciwb/main/tutorials/00-prereq.html>`_ 
to begin.

============== ==============================================================
PyPI           ``pip install mciwb``
Source code    https://github.com/gilesknap/mciwb
Documentation  https://gilesknap.github.io/mciwb
Releases       https://github.com/gilesknap/mciwb/releases
============== ==============================================================

Credits
-------

This project would not be possible without `mcipc <https://github.com/conqp/mcipc/>`_,
which provides the client library for Minecraft RCON.



.. |code_ci| image:: https://github.com/gilesknap/mciwb/workflows/Code%20CI/badge.svg?branch=main
    :target: https://github.com/gilesknap/mciwb/actions?query=workflow%3A%22Code+CI%22
    :alt: Code CI

.. |docs_ci| image:: https://github.com/gilesknap/mciwb/workflows/Docs%20CI/badge.svg?branch=main
    :target: https://github.com/gilesknap/mciwb/actions?query=workflow%3A%22Docs+CI%22
    :alt: Docs CI

.. |quality| image:: https://app.codacy.com/project/badge/Grade/4c514b64299e4ccd8c569d3e787245c7    
    :target: https://www.codacy.com/gh/gilesknap/mciwb/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=gilesknap/mciwb&amp;utm_campaign=Badge_Grade
    :alt: Code Quality

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
