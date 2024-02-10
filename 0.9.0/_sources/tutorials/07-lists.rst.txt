Lists
=====
Python lists are used to store a collection of items. They are ordered, changeable,
and allow duplicate values. You can create a list by enclosing items in square
brackets [], separated by commas. Here’s an example:

.. code-block:: python

   fruits = ["apple", "banana", "cherry"]

You can access the items of a list by referring to its index number. The index starts at 0 for the first item, 1 for the second item, and so on. Here’s an example:


.. code-block:: python

   print(fruits[1])

This will output ``banana``.

You can also change the value of a specific item by referring to its index number.
Here’s an example:

.. code-block:: python

   fruits[1] = "kiwi"

This will change the second item of the ``fruits`` list to ``kiwi``.

You can add an item to the end of a list using the append() method. Here’s
an example:

.. code-block:: python

   fruits.append("orange")

This will add ``orange`` to the end of the ``fruits`` list.

You can remove an item from a list using the remove() method.
Here’s an example:


.. code-block:: python

   fruits.remove("banana")

This will remove ``banana`` from the fruits list.

TODO: Build on the above until we demonstrate by building castle walls around
our village using this code:

.. literalinclude :: ../../src/demo/walls.py
   :language: python

