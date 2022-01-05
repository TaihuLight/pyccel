from collections import OrderedDict
from pyccel.ast.core import create_incremented_string
from pyccel.ast.variable import Variable


class Scope(object):
    """ Class representing all objects defined within a given
    scope

    Parameters
    ----------
    decorators : OrderedDict
                 A dictionary of any decorators which operate on
                 objects in this scope
    """
    __slots__ = ('_imports','_locals','parent_scope','_sons_scopes',
            '_used_symbols','_is_loop','_loops','_temporary_variables')

    def __init__(self, *, decorators=None, is_loop = False,
                    parent_scope = None):

        keys = ('functions','variables','classes',
                'imports','symbolic_functions',
                'macros','templates','headers','decorators',
                'static_functions','cls_constructs')

        self._imports = OrderedDict((k,OrderedDict()) for k in keys)

        self._locals  = OrderedDict((k,OrderedDict()) for k in keys)

        self._temporary_variables = []

        if decorators:
            self._locals['decorators'].update(decorators)

        # TODO use another name for headers
        #      => reserved keyword, or use __
        self.parent_scope        = parent_scope
        self._sons_scopes        = OrderedDict()

        self._used_symbols = set()

        self._is_loop = is_loop
        # scoping for loops
        self._loops = []

    def new_child_scope(self, name, **kwargs):
        """
        Create a new child Scope object which has the current object as parent.

        The parent scope can access the child scope through the '_sons_scopes'
        dictionary, using the provided name as key. Conversely, the child scope
        can access the parent scope through the 'parent_scope' attribute.

        Parameters
        ----------
        name : str
            Name of the new scope, used as a key to retrieve the new scope.

        kwargs : dict
            Keyword arguments passed to __init__() for object initialization.

        Returns
        -------
        child : Scope
            New child scope, which has the current object as parent.

        """

        child = Scope(**kwargs, parent_scope = self)

        self._sons_scopes[name] = child
        child.parent_scope = self

        return child

    @property
    def imports(self):
        """ A dictionary of objects imported in this scope
        """
        return self._imports

    @property
    def variables(self):
        """ A dictionary of variables defined in this scope
        """
        return self._locals['variables']

    @property
    def classes(self):
        """ A dictionary of classes defined in this scope
        """
        return self._locals['classes']

    @property
    def functions(self):
        """ A dictionary of functions defined in this scope
        """
        return self._locals['functions']

    @property
    def macros(self):
        """ A dictionary of macros defined in this scope
        """
        return self._locals['macros']

    @property
    def headers(self):
        """A dictionary of user defined headers which may
        be applied to functions in this scope"""
        return self._locals['headers']

    @property
    def templates(self):
        """A dictionary of user defined templates which may
        be applied to functions in this scope"""
        return self._locals['templates']

    @property
    def decorators(self):
        """Dictionary of Pyccel decorators which may be
        applied to a function definition in this scope."""
        return self._locals['decorators']

    @property
    def static_functions(self):
        """ A dictionary of static functions defined in this scope
        """
        return self._locals['static_functions']

    @property
    def cls_constructs(self):
        """ A dictionary of datatypes for the classes defined in
        this scope
        """
        return self._locals['cls_constructs']

    @property
    def sons_scopes(self):
        """ A dictionary of all the scopes contained within the
        current scope
        """
        return self._sons_scopes

    @property
    def symbolic_functions(self):
        """ 
        """
        return self._locals['symbolic_functions']

    def find_in_scope(self, name, location = None):
        """ Find and return the specified object in the scope
        If the object cannot be found then None is returned
        """
        for l in ([location] if location else self._locals.keys()):
            if name in self._locals[l]:
                return self._locals[l][name]

            if name in self.imports[l]:
                return self.imports[l][name]

        # Walk up the tree of Scope objects, until the root if needed
        if self.parent_scope:
            return self.parent_scope.find_in_scope(name, location)
        else:
            None

    @property
    def is_loop(self):
        return self._is_loop

    @property
    def loops(self):
        return self._loops

    def create_new_loop_scope(self):
        """ Create a new Scope within the current scope describing
        a loop (For/While/etc)
        """
        new_scope = Scope(decorators=self.decorators, is_loop = True,
                        parent_scope = self)
        self._loops.append(new_scope)
        return new_scope

    def insert_variable(self, var, name = None, python_scoping = True):
        """ Add a variable to the current scope

        Parameters
        ----------
        var  : Variable
                The variable to be inserted into the current scope
        name : str
                The name of the variable in the python code
                Default : var.name
        python_scope : bool
                If true then we assume that python scoping applies.
                In this case variables declared in loops exist beyond
                the end of the loop. Otherwise variables may be local
                to loops
                Default : True
        """
        if not isinstance(var, Variable):
            raise TypeError('variable must be of type Variable')

        if name is None:
            name = var.name

        if python_scoping and self.is_loop:
            self.parent_scope.insert_variable(var, name, python_scoping)
        else:
            if name in self._locals['variables']:
                raise RuntimeError('New variable already exists in scope')
            self._locals['variables'][name] = var
            self._temporary_variables.append(var)
            #TODO: make lower if case-sensitive
            self._used_symbols.add(var.name)

    def remove_variable(self, var, name = None, python_scoping = True):
        """ Remove a variable from anywhere in scope

        Parameters
        ----------
        var  : Variable
                The variable to be removed
        name : str
                The name of the variable in the python code
                Default : var.name
        python_scope : bool
                If true then we assume that python scoping applies.
                In this case variables declared in loops exist beyond
                the end of the loop. Otherwise variables may be local
                to loops
                Default : True
        """
        if name is None:
            name = var.name

        if name in self._locals['variables']:
            self._locals['variables'].pop(name)
            self._used_symbols.remove(name)
        elif self.parent_scope:
            self.parent_scope.remove_variable(var, name, python_scoping)
        else:
            raise RuntimeError("Variable not found in scope")

    def insert_class(self, cls):
        """ Add a class to the current scope

        Parameters
        ----------
        cls  : ClassDef
                The class to be inserted into the current scope
        """
        if not isinstance(cls, ClassDef):
            raise TypeError('class must be of type ClassDef')

        name = cls.name

        if self.is_loop:
            self.parent_scope.insert_class(cls)
        else:
            if name in self._locals['classes']:
                raise RuntimeError('New class already exists in scope')
            self._locals['classes'][name] = cls
            #TODO: make lower if case-sensitive
            self._used_symbols.add(name)