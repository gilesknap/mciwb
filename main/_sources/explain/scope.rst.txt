Variable Scope
==============

A variable is usually only available in the scope in which it is defined.

For example the following code will fail:

.. code-block:: python
    :linenos:

    def scope_test():
        # this variable has is in the scope of function scope_test()
        my_value = 10 
        print(my_value)

    scope_test()
    print(my_value) # this will fail

See here for a more detailed explanation:

    https://www.w3schools.com/python/python_scope.asp