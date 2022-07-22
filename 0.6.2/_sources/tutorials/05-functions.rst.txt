Functions
=========

Introduction
------------

In this tutorial we are going to start to create a few buildings for our village.
We will expand on the types of buildings in later tutorials as we learn new 
features of python.

.. warning::

    Before starting it is worth making a backup of your world. We will be 
    creating lost of test buildings and it would be good to be able to 
    reset back to the original state. See `backups`.


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

Pagoda Function
---------------

Lets create a function that will create a pagoda. This function will have 
the following parameters that the caller can supply:

- ``pos`` - the position of center of the base of the pagoda
- ``width`` - the width of the pagoda's base (defaults to 9)
- ``floor_height`` - the height of each floor (defaults to 4) 
- ``item`` - what blocks to use (defaults to gold block)

Try copying and pasting this function into your Python console.

.. literalinclude :: ../../src/demo/pagoda.py
   :language: python

Now type in the following code to call your pagoda function:

.. code-block:: python

    from pagoda import build_pagoda
    pagoda_pos=Vec3(585,71,-1728)
    pagoda(pagoda_pos, width=30)

If your player then looks to the North from our spawn point you should 
see this:

.. image:: ../images/pagoda.png
    :alt: pagoda
    :width: 800px

Let's take a look at the things that are new in the above code.

.. code-block:: python

    from mciwb import Direction, Item, get_client

The import function makes code from another module available to your code.
