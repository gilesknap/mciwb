If - Else
=========

In this tutorial we will:

- learn about the Python ``if else`` statements
- learn how to load a volume of blocks into the world from a file

  - and how to save a volume of blocks to a file

- learn how to place buttons or levers in the world and have them
  call Python code when activated

Logical Operators and Boolean
-----------------------------

Here we will introduce a new type called a Boolean. A Boolean is
a value that can only be either True or False.

I can create boolean variables like this::

    b1 = True
    b2 = False

Python supports the logical operators that you are familiar with from maths.
These operators make comparisons between numbers and return True or False
(so return a Boolean).
e.g. try this in iPython::

    In [6]: a = 4

    In [7]: b = 6

    In [8]: a > b
    Out[8]: False

Common logical operators are:

- a > b (a is greater than b)
- a < b (a is less than b)
- a == b (a is equal to b)
- a != b (a is not equal to b)
- a >= b (a is greater than or equal to b)
- a <= b (a is less than or equal to b)

You can also assign the result of a logical operator to a variable. Try this    
in iPython (reusing values of a and b you assigned a moment ago)::

    In [9]: b1 = a < b

    In [10]: b1
    Out[10]: True

Above we compared a and b and assigned the result to b1. The value of b1
is True because a is less than b.

It is important to remember the difference between ``=`` and ``==``. The
``=`` operator is used to assign a value to a variable. The ``==`` operator is
used to compare two values. In written maths we do not have this distinction,
but it helps Python to be clear about the meaning of a statement.

Code Branching
--------------

Up to this point we have always executed all the lines of code we have 
written in the order they appear in the program. The ``for`` loop does allow
us to repeat sections of code. It is also very useful to have more than
one branch of code to execute. To achieve this is we use
``if else``.

This is reasonably easy to understand as it reads like an English sentence.

Consider this simple function and see if you can work out what it does:

.. code-block:: python

    def age_test(my_birth_year, your_birth_year):
        if my_birth_year > your_birth_year:
            print("You are older than me")
        else:
            print("I am older than you")

Lets try this with my birth date is 1964 and yours is 2012:

.. code-block:: python

    In [12]:     age_test(1964, 2012)
    I am older than you

There is a bug in our code at the moment. What if the birth years are the
same? Then the program can't tell which one is older without knowing 
the month and day of each birthday.

We could write the function like this:

.. code-block:: python

    def age_test(my_birth_year, your_birth_year):
        if my_birth_year == your_birth_year:
            print("We have the same birth year!")
        elif my_birth_year > your_birth_year:
            print("You are older than me")
        else:
            print("I am older than you")

In this function we first check for the same year. Then we use ``elif``. This
is short for "else if". So if the years are not the same then it does the 
second check for "if my_birth_year > your_birth_year".

Gate with Working Portcullis
----------------------------

Now lets use what we have learnt to make a working gate for our village. The 
following video is a demo of what we will make in this section:

.. raw:: html

    <iframe width="700" height="600" src="https://www.youtube.com/embed/6eFvjlkh6zQ" title="YouTube video player" frameborder="0" allowfullscreen></iframe>

.. centered:: *Gateway with Portcullis Demo*

The shape of the gate itself is going to be loaded in from a file that I 
will provide. You will be free to edit gate to look how you would like it.

The following commands need to be executed in a bash shell. They will
create a folder called blocks and download my sample ``gate.json`` file 
into that folder

.. code-block:: bash
    
    cd $HOME/my_world
    mkdir blocks
    cd blocks
    wget https://raw.githubusercontent.com/gilesknap/mciwb/main/blocks/gate.json

For the moment we don't need to look inside the gate.json file. Just know that
you can save and load a volume of blocks in the world to and from a file.
(Later when we learn about Python Lists we will look inside these files). 

Let's jump right in and make the gate and then go back to explain what we have 
done. Create a new module in your ``buildings`` package and name it ``gate.py``.
Here is a reminder of how to do that using your bash prompt:

.. code-block:: bash
    
    cd $HOME/my_world
    code buildings/gate.py

Paste this code into gate.py and save it.

.. literalinclude :: ../../src/demo/gate.py
   :language: python

Note that the ``build_gate`` function has a default value for position. I 
chose this as a likely entrance point to the village (we will add a 
drawbridge later!). If you want to change this you can pass a different
position to the make_gate function. For help in choosing position coordinates 
see `../how-to/coordinates`. 

To make the gate type this in iPython:

.. code-block:: python
    
    from buildings.gate import make_gate
    make_gate()

