Classes
=======
In Python, a class is a blueprint for creating objects. It defines a set of attributes and methods that the objects of the class will have.

Here's an example of a simple class:


.. code-block:: python

   class Person:
      def __init__(self, name, age):
         self.name = name
         self.age = age

      def say_hello(self):
         print(f"Hello, my name is {self.name} and I am {self.age} years old.")

This class defines a ``Person`` object with a ``name`` and an ``age`` attribute, and a ``say_hello()`` method that prints a greeting.

You can create an instance of a class by calling the class as if it were a function, passing in any required arguments. Here's an example:


.. code-block:: python

   person1 = Person("Alice", 25)

This creates a ``Person`` object named ``person1`` with a ``name`` of ``"Alice"`` and an ``age`` of ``25``.

You can access the attributes of an object using the dot notation. Here's an example:


.. code-block:: python

   print(person1.name)

This will output ``"Alice"``.

You can call the methods of an object using the dot notation as well. Here's an example:


.. code-block:: python

   person1.say_hello()


This will output ``"Hello, my name is Alice and I am 25 years old."``.

I hope this helps! Let me know if you have any other questions.

TODO: elaborate on classes and demonstrate building all of the buildings
inside the castle walls with this code:

.. literalinclude :: ../../src/demo/house.py
   :language: python

Note that this code can now build a complete castle from previous steps.


.. literalinclude :: ../../src/demo/village.py
   :language: python