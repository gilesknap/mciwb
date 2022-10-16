MCIWB API
=========

This is the public API reference for MCIWB

MCIWB is built upon further libraries.
The dependencies look like this:

.. list-table:: Libraries
   :widths: 10 25 70
   :header-rows: 1

   * - Library
     - URL
     - Function
   * - RCON
     - https://github.com/conqp/rcon/
     - Provides the raw RCON interface to Minecraft
   * - MCIPC
     - https://github.com/conqp/mcipc/
     - Adds useful types to RCON creating a neat Python API for Minecraft 
   * - MCWB
     - https://github.com/mcipc-tools/mcwb
     - Adds a world builder API to MCIPC that creates complex objects in the world
   * - MCIWB
     - https://github.com/gilesknap/mciwb
     - Adds interactive features to MCWB


.. automodule mciwb

``mciwb``
~~~~~~~~~

.. data:: mciwb.__version__
    :type: str

    Version number as calculated by https://github.com/pypa/setuptools_scm

``mciwb.iwb``
----------------

.. automodule:: mciwb.iwb
    :members:

``mciwb.player``
----------------

.. automodule:: mciwb.player
    :members:


``mciwb.server``
----------------

.. automodule:: mciwb.server
    :members:


``mciwb.monitor``
-----------------

.. automodule:: mciwb.monitor
    :members:


``mciwb.backup``
----------------

.. automodule:: mciwb.backup
    :members:


``mciwb.signs``
----------------

.. automodule:: mciwb.signs
    :members:


``mciwb.copier``
----------------

.. automodule:: mciwb.copier
    :members:


``mciwb.switch``
----------------

.. automodule:: mciwb.switch
    :members:


``mciwb.threads``
-----------------

.. automodule:: mciwb.threads
    :members:

