Variable Scope
==============

A variable is usually only available in the scope in which it is defined.

For example, consider the following code:

.. code-block:: python
    :linenos:

    def scope_test():
        # this variable has is in the scope of function scope_test()
        my_value = 10 
        print(my_value)

    my_value = 5
    scope_test()
    print(my_value)

This code will print 10 (from inside scope_test) and then 5 
(from outside scope_test). This demonstrates that there are two
instances of ``my_value``. One is scoped inside scope_test and the other is
scoped outside scope_test (the global scope).

Scoping is very useful because it means we do not need to always choose 
unique names for variables. I can use the variable name ``my_value`` in
multiple functions and they will not interfere with each other.

See here for a more detailed explanation:

    https://www.w3schools.com/python/python_scope.asp