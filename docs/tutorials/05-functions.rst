Functions
=========

Introduction
------------

In this tutorial we are going to create a few houses for our village. 

To do this we will learn to use functions to packaged up our code into
reusable chunks. We will also learn to save our code in Python modules
so that we don't need to typing or pasting code all of the time.

Simple Function
---------------

A function is a named block of code with some parameters and a return value.
Parameters are variables that are set by the code that calls the function. 
The return value is passed back to the calling code.

Try typing (or pasting) this very simple function

.. code-block:: python

    def age(birth_year, current_year=2022):
        calculated_age = current_year - birth_year
        return calculated_age

When you hit enter after typing the function definition above nothing appears
to happen. But you have created a function which you can now call like this:

.. code-block:: python

    my_age = age(1965)
    print(my_age)

If you substitute your  own birth_year value this function will print your 
age at the end of the year 2022.

``age(1965)`` calls the function defined above and passes 1965 for the 
value of ``birth_year``. It does not pass a value for the parameter 
``current_year``. The default value for ``current_year`` was set to 2022.

The function performs a ``-`` subtraction operation, taking the value of 
``current_year`` and subtracting the value of ``birth_year``. The result
is assigned into ``calculated_age`` with ``=``.

The function uses ``return`` to pass the value of ``calculated_age`` back to
the caller. Our caller assigns the returned value to a variable called 
``my_age`` and prints it out. 

Now if you don't want to use the default of 2022 (when this tutorial was
written) you can pass your own value for ``current_year``. e.g. to find
out how old you were when the first Apple Mac was released:


.. code-block:: python

    print(age(1965, current_year=1984))
    19

Obviously if unlike me, you were born after 1984 you would get a negative 
result.

Variable Naming
---------------

Notice the use of ``_`` in the variable names. This is used to separate words
in the variable name. Typically variable names are lowercase with words separated
by underscores. It is also legal to use uppercase letters and numbers in variable
names (but a number must not be the first character).

Tower Function
--------------

Lets create a function that will create a tower. We are going to use the 
following function. Don't type it in yet, we are going to create a file for it.
Also do not worry too much about the details of this function
yet but notice that it has the following parameters that the caller can supply:

- ``height`` - the height of the tower
- ``width`` - the width of the tower
- ``world`` - a world object that we can use to create blocks in the world
- ``pos`` - the position of the tower

.. literalinclude :: ../../src/demo/tower.py
   :language: python

TODO continue
