# coding: utf-8


import importlib

from numpy import ndarray

from sympy import Lambda
from sympy.core.expr import Expr
from sympy.core import Symbol, Tuple
from sympy.core.relational import Equality, Relational,Ne,Eq
from sympy.logic.boolalg import And, Boolean, Not, Or, true, false
from sympy.core.singleton import Singleton
from sympy.core.basic import Basic
from sympy.core.function import Function
from sympy import sympify
from sympy import Symbol, Integer, Add, Mul,Pow
from sympy import Integer as sp_Integer
from sympy import Float   as sp_Float
from sympy.core.compatibility import with_metaclass
from sympy.core.compatibility import is_sequence
#from sympy.sets.fancysets import Range as sm_Range
from sympy.tensor import Idx, Indexed, IndexedBase
from sympy.matrices import ImmutableDenseMatrix
from sympy.matrices.expressions.matexpr import MatrixSymbol, MatrixElement
from sympy.utilities.iterables import iterable
from sympy.logic.boolalg import Boolean, BooleanTrue, BooleanFalse

from sympy.core.basic import Basic, Atom
from sympy.core.expr import Expr, AtomicExpr
from sympy.core.compatibility import string_types
from sympy.core.operations import LatticeOp
from sympy.core.function import Derivative
from sympy.core.function import _coeff_isneg
from sympy.core.singleton import S
from sympy import Integral, Symbol
from sympy.simplify.radsimp import fraction
from sympy.logic.boolalg import BooleanFunction

import collections
from sympy.core.compatibility import is_sequence

# TODO: add examples: Break, Len, Shape,
#                     Min, Max, Dot, Sign, Array,
# TODO - add EmptyStmt => empty lines
#      - update code examples
#      - add examples
#      - Function case
#      - Zeros, Ones, Array cases
#      - AnnotatedComment case
#      - Slice case
#      - Vector case
#      - use Tuple after checking the object is iterable:'funcs=Tuple(*funcs)'
#      - add a new Idx that uses Variable instead of Symbol

def subs(expr, a_old, a_new):
    """
    Substitutes old for new in an expression after sympifying args.

    a_old: str, Symbol, Variable
        name of the symbol to replace
    a_new: str, Symbol, Variable
        name of the new symbol

    Examples
    """
    a_new = a_old.clone(str(a_new))

    if iterable(expr):
        return [subs(i, a_old, a_new) for i in expr]
    elif isinstance(expr, Variable):
        if expr.name == str(a_old):
            return a_new
        else:
            return expr
    elif isinstance(expr, IndexedVariable):
        if str(expr) == str(a_old):
            return IndexedVariable(str(a_new))
        else:
            return expr
    elif isinstance(expr, IndexedElement):
        base    = subs(expr.base   , a_old, a_new)
        indices = subs(expr.indices, a_old, a_new)
        return base[indices]
    elif isinstance(expr, Expr):
        return expr.subs({a_old: a_new})
    elif isinstance(expr, Zeros):
        e_lhs   = subs(expr.lhs, a_old, a_new)
        e_shape = subs(expr.shape, a_old, a_new)
        return Zeros(e_lhs, e_shape)
    elif isinstance(expr, Ones):
        e_lhs   = subs(expr.lhs, a_old, a_new)
        e_shape = subs(expr.shape, a_old, a_new)
        return Ones(e_lhs, e_shape)
    elif isinstance(expr, ZerosLike):
        e_rhs = subs(expr.rhs, a_old, a_new)
        e_lhs = subs(expr.lhs, a_old, a_new)
        return ZerosLike(e_lhs, e_rhs)
    elif isinstance(expr, Assign):
        e_rhs = subs(expr.rhs, a_old, a_new)
        e_lhs = subs(expr.lhs, a_old, a_new)
        return Assign(e_lhs, e_rhs, strict=False)
    elif isinstance(expr, MultiAssign):
        e_rhs   = subs(expr.rhs, a_old, a_new)
        e_lhs   = subs(expr.lhs, a_old, a_new)
        return MultiAssign(e_lhs, e_rhs)
    elif isinstance(expr, While):
        test = subs(expr.test, a_old, a_new)
        body = subs(expr.body, a_old, a_new)
        return While(test, body)
    elif isinstance(expr, For):
        # TODO treat iter correctly
#        target   = subs(expr.target, a_old, a_new)
#        it       = subs(expr.iterable, a_old, a_new)
        target   = expr.target
        it       = expr.iterable
        body     = subs(expr.body, a_old, a_new)
        return For(target, it, body)
    elif isinstance(expr, If):
        args = []
        for block in expr.args:
            test  = block[0]
            stmts = block[1]
            t = subs(test,  a_old, a_new)
            s = subs(stmts, a_old, a_new)
            args.append((t,s))
        return If(*args)
    elif isinstance(expr, FunctionDef):
        name        = subs(expr.name, a_old, a_new)
        arguments   = subs(expr.arguments, a_old, a_new)
        results     = subs(expr.results, a_old, a_new)
        body        = subs(expr.body, a_old, a_new)
        local_vars  = subs(expr.local_vars, a_old, a_new)
        global_vars = subs(expr.global_vars, a_old, a_new)
        return FunctionDef(name, arguments, results, \
                           body, local_vars, global_vars)
    elif isinstance(expr, Declare):
        dtype     = subs(expr.dtype, a_old, a_new)
        variables = subs(expr.variables, a_old, a_new)
        return Declare(dtype, variables)
    else:
        return expr

def allocatable_like(expr, verbose=False):
    """
    finds attributs of an expression

    expr: Expr
        a pyccel expression

    verbose: bool
        talk more
    """
#    print ('>>>>> expr = ', expr)
#    print ('>>>>> type = ', type(expr))

    if isinstance(expr, (Variable, IndexedVariable, IndexedElement)):
        return expr
    elif isinstance(expr, str): # if the rhs is a string
        return expr
    elif isinstance(expr, Expr):
        args = [expr]
        while args:
            a = args.pop()
#            print (">>>> ", a, type(a))

            # XXX: This is a hack to support non-Basic args
            if isinstance(a, string_types):
                continue

            if a.is_Mul:
                if _coeff_isneg(a):
                    if a.args[0] is S.NegativeOne:
                        a = a.as_two_terms()[1]
                    else:
                        a = -a
                n, d = fraction(a)
                if n.is_Integer:
                    args.append(d)
                    continue  # won't be -Mul but could be Add
                elif d is not S.One:
                    if not d.is_Integer:
                        args.append(d)
                    args.append(n)
                    continue  # could be -Mul
            elif a.is_Add:
                aargs = list(a.args)
                negs = 0
                for i, ai in enumerate(aargs):
                    if _coeff_isneg(ai):
                        negs += 1
                        args.append(-ai)
                    else:
                        args.append(ai)
                continue
            if a.is_Pow and a.exp is S.NegativeOne:
                args.append(a.base)  # won't be -Mul but could be Add
                continue
            if (a.is_Mul or
                a.is_Pow or
                a.is_Function or
                isinstance(a, Derivative) or
                    isinstance(a, Integral)):

                o = Symbol(a.func.__name__.upper())
            if     (not a.is_Symbol) \
               and (not isinstance(a, (IndexedElement, Function))):
                args.extend(a.args)
            if isinstance(a, Function):
                if verbose:
                    print ("Functions not yet available")
                return None
            elif isinstance(a, (Variable, IndexedVariable, IndexedElement)):
                return a
            elif a.is_Symbol:
                raise TypeError("Found an unknown symbol {0}".format(str(a)))
    else:
        raise TypeError("Unexpected type {0}".format(type(expr)))

class DottedName(Basic):
    """
    Represents a dotted variable.

    Examples

    >>> from pyccel.ast.core import DottedName
    >>> DottedName('matrix', 'n_rows')
    matrix.n_rows
    >>> DottedName('pyccel', 'stdlib', 'parallel')
    pyccel.stdlib.parallel
    """
    def __new__(cls, *args):
        return Basic.__new__(cls, *args)

    @property
    def name(self):
        return self._args

    def __str__(self):
        return '.'.join(str(n) for n in self.name)

    def _sympystr(self, printer):
        sstr = printer.doprint
        return '.'.join(sstr(n) for n in self.name)




class List(Tuple):
    """Represent lists in the code with dynamic memory management."""
    pass


class Assign(Basic):
    """Represents variable assignment for code generation.

    lhs : Expr
        Sympy object representing the lhs of the expression. These should be
        singular objects, such as one would use in writing code. Notable types
        include Symbol, MatrixSymbol, MatrixElement, and Indexed. Types that
        subclass these types are also supported.

    rhs : Expr
        Sympy object representing the rhs of the expression. This can be any
        type, provided its shape corresponds to that of the lhs. For example,
        a Matrix type can be assigned to MatrixSymbol, but not to Symbol, as
        the dimensions will not align.

    strict: bool
        if True, we do some verifications. In general, this can be more
        complicated and is treated in pyccel.syntax.

    status: None, str
        if lhs is not allocatable, then status is None.
        otherwise, status is {'allocated', 'unallocated'}

    like: None, Variable
        contains the name of the variable from which the lhs will be cloned.

    Examples

    >>> from sympy import symbols, MatrixSymbol, Matrix
    >>> from pyccel.ast.core import Assign
    >>> x, y, z = symbols('x, y, z')
    >>> Assign(x, y)
    x := y
    >>> Assign(x, 0)
    x := 0
    >>> A = MatrixSymbol('A', 1, 3)
    >>> mat = Matrix([x, y, z]).T
    >>> Assign(A, mat)
    A := Matrix([[x, y, z]])
    >>> Assign(A[0, 1], x)
    A[0, 1] := x

    """

    def __new__(cls, lhs, rhs, strict=False, status=None, like=None):
        cls._strict = strict
        if strict:
            lhs = sympify(lhs)
            rhs = sympify(rhs)
            # Tuple of things that can be on the lhs of an assignment
            assignable = (Symbol, MatrixSymbol, MatrixElement, Indexed, Idx)
            #if not isinstance(lhs, assignable):
            #    raise TypeError("Cannot assign to lhs of type %s." % type(lhs))
            # Indexed types implement shape, but don't define it until later. This
            # causes issues in assignment validation. For now, matrices are defined
            # as anything with a shape that is not an Indexed
            lhs_is_mat = hasattr(lhs, 'shape') and not isinstance(lhs, Indexed)
            rhs_is_mat = hasattr(rhs, 'shape') and not isinstance(rhs, Indexed)
            # If lhs and rhs have same structure, then this assignment is ok
            if lhs_is_mat:
                if not rhs_is_mat:
                    raise ValueError("Cannot assign a scalar to a matrix.")
                elif lhs.shape != rhs.shape:
                    raise ValueError("Dimensions of lhs and rhs don't align.")
            elif rhs_is_mat and not lhs_is_mat:
                raise ValueError("Cannot assign a matrix to a scalar.")
        return Basic.__new__(cls, lhs, rhs, status, like)

    def _sympystr(self, printer):
        sstr = printer.doprint
        return '{0} := {1}'.format(sstr(self.lhs), sstr(self.rhs))

    @property
    def lhs(self):
        return self._args[0]

    @property
    def rhs(self):
        return self._args[1]

    # TODO : remove
    @property
    def expr(self):
        return self.rhs

    @property
    def status(self):
        return self._args[2]

    @property
    def like(self):
        return self._args[3]

    @property
    def strict(self):
        return self._strict

    @property
    def is_alias(self):
        """Returns True if the assignment is an alias."""
        # TODO to be improved when handling classes
        lhs = self.lhs
        rhs = self.rhs
        cond = isinstance(rhs, Variable) and (rhs.rank > 0)
        cond = cond or isinstance(rhs, IndexedElement)
        cond = cond or isinstance(rhs, IndexedVariable)
        cond = cond and isinstance(lhs, Symbol)
        return cond

    @property
    def is_symbolic_alias(self):
        """Returns True if the assignment is a symbolic alias."""
        # TODO to be improved when handling classes
        lhs = self.lhs
        rhs = self.rhs
        if isinstance(lhs, Variable):
            return isinstance(lhs.dtype, NativeSymbol)
        elif isinstance(lhs, Symbol):
            if isinstance(rhs, Range):
                return True
            elif isinstance(rhs, Variable):
                return isinstance(rhs.dtype, NativeSymbol)
            elif isinstance(rhs, Symbol):
                return True

        return False

class AliasAssign(Basic):
    """Represents aliasing for code generation. An alias is any statement of the
    form `lhs := rhs` where

    lhs : Symbol
        at this point we don't know yet all information about lhs, this is why a
        Symbol is the appropriate type.

    rhs : Variable, IndexedVariable, IndexedElement
        an assignable variable can be of any rank and any datatype, however its
        shape must be known (not None)

    Examples

    >>> from sympy import Symbol
    >>> from pyccel.ast.core import AliasAssign
    >>> from pyccel.ast.core import Variable
    >>> n = Variable('int', 'n')
    >>> x = Variable('int', 'x', rank=1, shape=[n])
    >>> y = Symbol('y')
    >>> AliasAssign(y, x)

    """

    def __new__(cls, lhs, rhs):
        return Basic.__new__(cls, lhs, rhs)

    def _sympystr(self, printer):
        sstr = printer.doprint
        return '{0} := {1}'.format(sstr(self.lhs), sstr(self.rhs))

    @property
    def lhs(self):
        return self._args[0]

    @property
    def rhs(self):
        return self._args[1]

class SymbolicAssign(Basic):
    """Represents symbolic aliasing for code generation. An alias is any statement of the
    form `lhs := rhs` where

    lhs : Symbol

    rhs : Range

    Examples

    >>> from sympy import Symbol
    >>> from pyccel.ast.core import SymbolicAssign
    >>> from pyccel.ast.core import Range
    >>> r = Range(0, 3)
    >>> y = Symbol('y')
    >>> SymbolicAssign(y, r)

    """

    def __new__(cls, lhs, rhs):
        return Basic.__new__(cls, lhs, rhs)

    def _sympystr(self, printer):
        sstr = printer.doprint
        return '{0} := {1}'.format(sstr(self.lhs), sstr(self.rhs))

    @property
    def lhs(self):
        return self._args[0]

    @property
    def rhs(self):
        return self._args[1]


# The following are defined to be sympy approved nodes. If there is something
# smaller that could be used, that would be preferable. We only use them as
# tokens.


class NativeOp(with_metaclass(Singleton, Basic)):
    """Base type for native operands."""
    pass


class AddOp(NativeOp):
    _symbol = '+'


class SubOp(NativeOp):
    _symbol = '-'


class MulOp(NativeOp):
    _symbol = '*'


class DivOp(NativeOp):
    _symbol = '/'


class ModOp(NativeOp):
    _symbol = '%'


op_registry = {'+': AddOp(),
               '-': SubOp(),
               '*': MulOp(),
               '/': DivOp(),
               '%': ModOp()}


def operator(op):
    """Returns the operator singleton for the given operator"""

    if op.lower() not in op_registry:
        raise ValueError("Unrecognized operator " + op)
    return op_registry[op]


class AugAssign(Basic):
    """
    Represents augmented variable assignment for code generation.

    lhs : Expr
        Sympy object representing the lhs of the expression. These should be
        singular objects, such as one would use in writing code. Notable types
        include Symbol, MatrixSymbol, MatrixElement, and Indexed. Types that
        subclass these types are also supported.

    op : NativeOp
        Operator (+, -, /, \*, %).

    rhs : Expr
        Sympy object representing the rhs of the expression. This can be any
        type, provided its shape corresponds to that of the lhs. For example,
        a Matrix type can be assigned to MatrixSymbol, but not to Symbol, as
        the dimensions will not align.

    strict: bool
        if True, we do some verifications. In general, this can be more
        complicated and is treated in pyccel.syntax.

    status: None, str
        if lhs is not allocatable, then status is None.
        otherwise, status is {'allocated', 'unallocated'}

    like: None, Variable
        contains the name of the variable from which the lhs will be cloned.

    Examples

    >>> from pyccel.ast.core import Variable
    >>> from pyccel.ast.core import AugAssign
    >>> s = Variable('int', 's')
    >>> t = Variable('int', 't')
    >>> AugAssign(s, '+', 2 * t + 1)
    s += 1 + 2*t
    """

    def __new__(cls, lhs, op, rhs, strict=False, status=None, like=None):
        cls._strict = strict
        if strict:
            lhs = sympify(lhs)
            rhs = sympify(rhs)
            # Tuple of things that can be on the lhs of an assignment
            assignable = (Symbol, MatrixSymbol, MatrixElement, Indexed)
            if not isinstance(lhs, assignable):
                raise TypeError("Cannot assign to lhs of type %s." % type(lhs))
            # Indexed types implement shape, but don't define it until later. This
            # causes issues in assignment validation. For now, matrices are defined
            # as anything with a shape that is not an Indexed
            lhs_is_mat = hasattr(lhs, 'shape') and not isinstance(lhs, Indexed)
            rhs_is_mat = hasattr(rhs, 'shape') and not isinstance(rhs, Indexed)
            # If lhs and rhs have same structure, then this assignment is ok
            if lhs_is_mat:
                if not rhs_is_mat:
                    raise ValueError("Cannot assign a scalar to a matrix.")
                elif lhs.shape != rhs.shape:
                    raise ValueError("Dimensions of lhs and rhs don't align.")
            elif rhs_is_mat and not lhs_is_mat:
                raise ValueError("Cannot assign a matrix to a scalar.")

        if isinstance(op, str):
            op = operator(op)
        elif op not in list(op_registry.values()):
            raise TypeError("Unrecognized Operator")

        return Basic.__new__(cls, lhs, op, rhs, status, like)

    def _sympystr(self, printer):
        sstr = printer.doprint
        return '{0} {1}= {2}'.format(sstr(self.lhs), self.op._symbol,
                sstr(self.rhs))

    @property
    def lhs(self):
        return self._args[0]

    @property
    def op(self):
        return self._args[1]

    @property
    def rhs(self):
        return self._args[2]

    @property
    def status(self):
        return self._args[3]

    @property
    def like(self):
        return self._args[4]

    @property
    def strict(self):
        return self._strict

class While(Basic):
    """Represents a 'while' statement in the code.

    Expressions are of the form:
        "while test:
            body..."

    test : expression
        test condition given as a sympy expression
    body : sympy expr
        list of statements representing the body of the While statement.

    Examples

    >>> from sympy import Symbol
    >>> from pyccel.ast.core import Assign, While
    >>> n = Symbol('n')
    >>> While((n>1), [Assign(n,n-1)])
    While(n > 1, (n := n - 1,))
    """
    def __new__(cls, test, body):
        test = sympify(test)

        if not iterable(body):
            raise TypeError("body must be an iterable")
        body = Tuple(*(sympify(i) for i in body))
        return Basic.__new__(cls, test, body)

    @property
    def test(self):
        return self._args[0]


    @property
    def body(self):
        return self._args[1]

class With(Basic):
    """Represents a 'with' statement in the code.

    Expressions are of the form:
        "while test:
            body..."

    test : expression
        test condition given as a sympy expression
    body : sympy expr
        list of statements representing the body of the With statement.

    Examples

    """
    # TODO check prelude and epilog
    def __new__(cls, test, body, settings):
        test = sympify(test)

        if not iterable(body):
            raise TypeError("body must be an iterable")
        body = Tuple(*(sympify(i) for i in body))
        return Basic.__new__(cls, test, body, settings)

    @property
    def test(self):
        return self._args[0]

    @property
    def body(self):
        return self._args[1]

    @property
    def settings(self):
        return self._args[2]

class Range(Basic):
    """
    Represents a range.

    Examples

    >>> from pyccel.ast.core import Variable
    >>> from pyccel.ast.core import Range
    >>> from sympy import Symbol
    >>> s = Variable('int', 's')
    >>> e = Symbol('e')
    >>> Range(s, e, 1)
    Range(0, n, 1)
    """

    def __new__(cls, *args):
        start = 0
        stop  = None
        step  = 1

        _valid_args = (Integer, Symbol, Indexed, Variable, IndexedElement)

        if isinstance(args, (tuple, list, Tuple)):
            if len(args) == 1:
                stop = args[0]
            elif len(args) == 2:
                start = args[0]
                stop = args[1]
            elif len(args) == 3:
                start = args[0]
                stop = args[1]
                step = args[2]
            else:
                raise ValueError('Range has at most 3 arguments')
        elif isinstance(args, _valid_args):
            stop = args
        else:
            raise TypeError('expecting a list or valid stop')

        return Basic.__new__(cls, start, stop, step)

    @property
    def start(self):
        return self._args[0]

    @property
    def stop(self):
        return self._args[1]

    @property
    def step(self):
        return self._args[2]

    @property
    def size(self):
        return (self.stop - self.start)/self.step

class Tile(Range):
    """
    Representes a tile.

    Examples

    >>> from pyccel.ast.core import Variable
    >>> from pyccel.ast.core import Tile
    >>> from sympy import Symbol
    >>> s = Variable('int', 's')
    >>> e = Symbol('e')
    >>> Tile(s, e, 1)
    Tile(0, n, 1)
    """

    def __new__(cls, start, stop):
        step = 1
        return Range.__new__(cls, start, stop, step)

    @property
    def start(self):
        return self._args[0]

    @property
    def stop(self):
        return self._args[1]

    @property
    def size(self):
        return self.stop - self.start

class ParallelRange(Range):
    """
    Representes a parallel range using OpenMP/OpenACC.

    Examples

    >>> from pyccel.ast.core import Variable
    """
    pass


# TODO: implement it as an extension of sympy Tensor?
class Tensor(Basic):
    """
    Base class for tensor.

    Examples

    >>> from pyccel.ast.core import Variable
    >>> from pyccel.ast.core import Range, Tensor
    >>> from sympy import Symbol
    >>> s1 = Variable('int', 's1')
    >>> s2 = Variable('int', 's2')
    >>> e1 = Variable('int', 'e1')
    >>> e2 = Variable('int', 'e2')
    >>> r1 = Range(s1, e1, 1)
    >>> r2 = Range(s2, e2, 1)
    >>> Tensor(r1, r2)
    Tensor(Range(s1, e1, 1), Range(s2, e2, 1), name=tensor)
    """

    def __new__(cls, *args, **kwargs):
        for r in args:
            cond = (isinstance(r, Variable) and
                    isinstance(r.dtype, (NativeRange, NativeTensor)))
            cond = cond or isinstance(r, (Range, Tensor))

            if not cond:
                raise TypeError("non valid argument, given {0}".format(type(r)))

        try:
            name = kwargs['name']
        except:
            name = 'tensor'

        args = list(args) + [name]

        return Basic.__new__(cls, *args)

    @property
    def name(self):
        return self._args[-1]

    @property
    def ranges(self):
        return self._args[:-1]

    @property
    def dim(self):
        return len(self.ranges)

    def _sympystr(self, printer):
        sstr = printer.doprint
        txt  = ', '.join(sstr(n) for n in self.ranges)
        txt  = 'Tensor({0}, name={1})'.format(txt, sstr(self.name))
        return txt

# TODO add a name to a block?
class Block(Basic):
    """Represents a block in the code. A block consists of the following inputs

    variables: list
        list of the variables that appear in the block.

    declarations: list
        list of declarations of the variables that appear in the block.

    body: list
        a list of statements

    Examples

    >>> from pyccel.ast.core import Variable, Assign, Block
    >>> n = Variable('int', 'n')
    >>> x = Variable('int', 'x')
    >>> Block([n, x], [Assign(x,2.*n + 1.), Assign(n, n + 1)])
    Block([n, x], [x := 1.0 + 2.0*n, n := 1 + n])
    """

    def __new__(cls, variables, body):
        if not iterable(variables):
            raise TypeError("variables must be an iterable")
        for var in variables:
            if not isinstance(var, Variable):
                raise TypeError("Only a Variable instance is allowed.")
        if not iterable(body):
            raise TypeError("body must be an iterable")
        return Basic.__new__(cls, variables, body)

    @property
    def variables(self):
        return self._args[0]

    @property
    def body(self):
        return self._args[1]

    @property
    def declarations(self):
        return [Declare(i.dtype, i) for i in self.variables]

class ParallelBlock(Block):
    """
    Represents a parallel block in the code.
    In addition to block inputs, there is

    clauses: list
        a list of clauses

    Examples

    >>> from pyccel.ast.core import ParallelBlock
    >>> from pyccel.ast.core import Variable, Assign, Block
    >>> n = Variable('int', 'n')
    >>> x = Variable('int', 'x')
    >>> body = [Assign(x,2.*n + 1.), Assign(n, n + 1)]
    >>> variables = [x,n]
    >>> clauses = []
    >>> ParallelBlock(clauses, variables, body)
    # parallel
    x := 1.0 + 2.0*n
    n := 1 + n
    """
    _prefix = '#'
    def __new__(cls, clauses, variables, body):
        if not iterable(clauses):
            raise TypeError('Expecting an iterable for clauses')

        cls._clauses = clauses

        return Block.__new__(cls, variables, body)

    @property
    def clauses(self):
        return self._clauses

    @property
    def prefix(self):
        return self._prefix

    def _sympystr(self, printer):
        sstr = printer.doprint

        prefix  = sstr(self.prefix)
        clauses = ' '.join('{0}'.format(sstr(i)) for i in self.clauses)
        body    = '\n'.join('{0}'.format(sstr(i)) for i in self.body)

        code = '{0} parallel {1}\n{2}'.format(prefix, clauses, body)
        return code

class Module(Basic):
    """Represents a module in the code. A block consists of the following inputs

    variables: list
        list of the variables that appear in the block.

    declarations: list
        list of declarations of the variables that appear in the block.

    funcs: list
        a list of FunctionDef instances

    classes: list
        a list of ClassDef instances

    imports: list, tuple
        list of needed imports

    Examples

    >>> from pyccel.ast.core import Variable, Assign
    >>> from pyccel.ast.core import ClassDef, FunctionDef, Module
    >>> x = Variable('double', 'x')
    >>> y = Variable('double', 'y')
    >>> z = Variable('double', 'z')
    >>> t = Variable('double', 't')
    >>> a = Variable('double', 'a')
    >>> b = Variable('double', 'b')
    >>> body = [Assign(y,x+a)]
    >>> translate = FunctionDef('translate', [x,y,a,b], [z,t], body)
    >>> attributs   = [x,y]
    >>> methods     = [translate]
    >>> Point = ClassDef('Point', attributs, methods)
    >>> incr = FunctionDef('incr', [x], [y], [Assign(y,x+1)])
    >>> decr = FunctionDef('decr', [x], [y], [Assign(y,x-1)])
    >>> Module('my_module', [], [incr, decr], [Point])
    Module(my_module, [], [FunctionDef(incr, (x,), (y,), [y := 1 + x], [], [], None, False, function), FunctionDef(decr, (x,), (y,), [y := -1 + x], [], [], None, False, function)], [ClassDef(Point, (x, y), (FunctionDef(translate, (x, y, a, b), (z, t), [y := a + x], [], [], None, False, function),), [public])])
    """

    def __new__(cls, name, variables, funcs, classes, imports=[]):
        if not isinstance(name, str):
            raise TypeError('name must be a string')

        if not iterable(variables):
            raise TypeError("variables must be an iterable")
        for i in variables:
            if not isinstance(i, Variable):
                raise TypeError("Only a Variable instance is allowed.")

        if not iterable(funcs):
            raise TypeError("funcs must be an iterable")
        for i in funcs:
            if not isinstance(i, FunctionDef):
                raise TypeError("Only a FunctionDef instance is allowed.")

        if not iterable(classes):
            raise TypeError("classes must be an iterable")
        for i in classes:
            if not isinstance(i, ClassDef):
                raise TypeError("Only a ClassDef instance is allowed.")

        if not iterable(imports):
            raise TypeError("imports must be an iterable")

        for i in funcs:
            imports += i.imports
        for i in classes:
            imports += i.imports
        imports = set(imports) # for unicity
        imports = Tuple(*imports)

        return Basic.__new__(cls, name, variables, funcs, classes, imports)

    @property
    def name(self):
        return self._args[0]

    @property
    def variables(self):
        return self._args[1]

    @property
    def funcs(self):
        return self._args[2]

    @property
    def classes(self):
        return self._args[3]

    @property
    def imports(self):
        return self._args[4]

    @property
    def declarations(self):
        return [Declare(i.dtype, i) for i in self.variables]

    @property
    def body(self):
        return self.funcs + self.classes

class Program(Basic):
    """Represents a Program in the code. A block consists of the following inputs

    variables: list
        list of the variables that appear in the block.

    declarations: list
        list of declarations of the variables that appear in the block.

    funcs: list
        a list of FunctionDef instances

    classes: list
        a list of ClassDef instances

    body: list
        a list of statements

    imports: list, tuple
        list of needed imports

    modules: list, tuple
        list of needed modules

    Examples

    >>> from pyccel.ast.core import Variable, Assign
    >>> from pyccel.ast.core import ClassDef, FunctionDef, Module
    >>> x = Variable('double', 'x')
    >>> y = Variable('double', 'y')
    >>> z = Variable('double', 'z')
    >>> t = Variable('double', 't')
    >>> a = Variable('double', 'a')
    >>> b = Variable('double', 'b')
    >>> body = [Assign(y,x+a)]
    >>> translate = FunctionDef('translate', [x,y,a,b], [z,t], body)
    >>> attributs   = [x,y]
    >>> methods     = [translate]
    >>> Point = ClassDef('Point', attributs, methods)
    >>> incr = FunctionDef('incr', [x], [y], [Assign(y,x+1)])
    >>> decr = FunctionDef('decr', [x], [y], [Assign(y,x-1)])
    >>> Module('my_module', [], [incr, decr], [Point])
    Module(my_module, [], [FunctionDef(incr, (x,), (y,), [y := 1 + x], [], [], None, False, function), FunctionDef(decr, (x,), (y,), [y := -1 + x], [], [], None, False, function)], [ClassDef(Point, (x, y), (FunctionDef(translate, (x, y, a, b), (z, t), [y := a + x], [], [], None, False, function),), [public])])
    """

    def __new__(cls, name, variables, funcs, classes, body, imports=[], modules=[]):
        if not isinstance(name, str):
            raise TypeError('name must be a string')
            
        if not iterable(variables):
            raise TypeError("variables must be an iterable")
        for i in variables:
            if not isinstance(i, Variable):
                raise TypeError("Only a Variable instance is allowed.")

        if not iterable(funcs):
            raise TypeError("funcs must be an iterable")
        for i in funcs:
            if not isinstance(i, FunctionDef):
                raise TypeError("Only a FunctionDef instance is allowed.")

        if not iterable(body):
            raise TypeError("body must be an iterable")

        if not iterable(classes):
            raise TypeError("classes must be an iterable")
        for i in classes:
            if not isinstance(i, ClassDef):
                raise TypeError("Only a ClassDef instance is allowed.")

        if not iterable(imports):
            raise TypeError("imports must be an iterable")

        for i in funcs:
            imports += i.imports
        for i in classes:
            imports += i.imports
        imports = set(imports) # for unicity
        imports = Tuple(*imports)

        if not iterable(modules):
            raise TypeError("modules must be an iterable")


        #TODO
#        elif isinstance(stmt, list):
#            for s in stmt:
#                body += printer(s) + "\n"


        return Basic.__new__(cls, name, variables, funcs, classes, body, imports, modules)

    @property
    def name(self):
        return self._args[0]

    @property
    def variables(self):
        return self._args[1]

    @property
    def funcs(self):
        return self._args[2]

    @property
    def classes(self):
        return self._args[3]

    @property
    def body(self):
        return self._args[4]

    @property
    def imports(self):
        return self._args[5]

    @property
    def modules(self):
        return self._args[6]

    @property
    def declarations(self):
        return [Declare(i.dtype, i) for i in self.variables]



class For(Basic):
    """Represents a 'for-loop' in the code.

    Expressions are of the form:
        "for target in iter:
            body..."

    target : symbol
        symbol representing the iterator
    iter : iterable
        iterable object. for the moment only Range is used
    body : sympy expr
        list of statements representing the body of the For statement.

    Examples

    >>> from sympy import symbols, MatrixSymbol
    >>> from pyccel.ast.core import Assign, For
    >>> i,b,e,s,x = symbols('i,b,e,s,x')
    >>> A = MatrixSymbol('A', 1, 3)
    >>> For(i, (b,e,s), [Assign(x,x-1), Assign(A[0, 1], x)])
    For(i, Range(b, e, s), (x := x - 1, A[0, 1] := x))
    """

    def __new__(cls, target, iter, body, strict=True):
        if strict:
            target = sympify(target)

            cond_iter = iterable(iter)
            cond_iter = cond_iter or (isinstance(iter, (Range, Tensor)))
            cond_iter = cond_iter or (isinstance(iter, Variable)
                                      and is_iterable_datatype(iter.dtype))
            cond_iter = cond_iter or (isinstance(iter, ConstructorCall)
                                      and is_iterable_datatype(iter.this.dtype))
            if not cond_iter:
                raise TypeError("iter must be an iterable")

            if not iterable(body):
                raise TypeError("body must be an iterable")

            body = Tuple(*(sympify(i) for i in body))
        return Basic.__new__(cls, target, iter, body)

    @property
    def target(self):
        return self._args[0]

    @property
    def iterable(self):
        return self._args[1]

    @property
    def body(self):
        return self._args[2]

class ForIterator(For):
    """Class that describes iterable classes defined by the user."""

    @property
    def target(self):
        ts = super(ForIterator, self).target

        if not(len(ts) == self.depth):
            raise ValueError('wrong number of targets')

        return ts

    @property
    def depth(self):
        it = self.iterable
        if isinstance(it, Variable):
            if isinstance(it.dtype, NativeRange):
                return 1
            if isinstance(it.dtype, NativeTensor):
                # TODO must be computed
                return 2

            cls_base = it.cls_base
            if not cls_base:
                raise TypeError('cls_base undefined')

            methods = cls_base.methods_as_dict

            it_method = methods['__iter__']

            it_vars = []
            for stmt in it_method.body:
                if isinstance(stmt, Assign):
                    it_vars.append(stmt.lhs)

            n = len(set([str(var.name) for var in it_vars]))
            return n
        else: # isinstance(it, ConstructorCall)
            return 1

    @property
    def ranges(self):
        return get_iterable_ranges(self.iterable)


# The following are defined to be sympy approved nodes. If there is something
# smaller that could be used, that would be preferable. We only use them as
# tokens.


class DataType(with_metaclass(Singleton, Basic)):
    """Base class representing native datatypes"""
    _name = '__UNDEFINED__'

    @property
    def name(self):
        return self._name

class NativeBool(DataType):
    _name = 'Bool'
    pass

class NativeInteger(DataType):
    _name = 'Int'
    pass

class NativeFloat(DataType):
    _name = 'Float'
    pass

class NativeDouble(DataType):
    _name = 'Double'
    pass

class NativeComplex(DataType):
    _name = 'Complex'
    pass

class NativeString(DataType):
    _name = 'String'
    pass

class NativeVoid(DataType):
    _name = 'Void'
    pass

class NativeNil(DataType):
    _name = 'Nil'
    pass

class NativeList(DataType):
    _name = 'List'
    pass

class NativeIntegerList(NativeInteger, NativeList):
    _name = 'IntegerList'
    pass

class NativeFloatList(NativeFloat, NativeList):
    _name = 'FloatList'
    pass

class NativeDoubleList(NativeDouble, NativeList):
    _name = 'DoubleList'
    pass

class NativeComplexList(NativeComplex, NativeList):
    _name = 'ComplexList'
    pass

class NativeRange(DataType):
    _name = 'Range'
    pass

class NativeTensor(DataType):
    _name = 'Tensor'
    pass

class NativeParallelRange(NativeRange):
    _name = 'ParallelRange'
    pass

# TODO remove later
class NativeVector(DataType):
    _name = 'Vector'
    pass

# TODO remove later
class NativeStencil(DataType):
    _name = 'Stencil'
    pass

class NativeSymbol(DataType):
    _name = 'Symbol'
    pass

class CustomDataType(DataType):
    _name = '__UNDEFINED__'
    pass


Bool    = NativeBool()
Int     = NativeInteger()
Float   = NativeFloat()
Double  = NativeDouble()
Complex = NativeComplex()
Void    = NativeVoid()
Nil     = NativeNil()
String  = NativeString()
_Vector = NativeVector()
_Stencil = NativeStencil()
_Symbol = NativeSymbol()
IntegerList = NativeIntegerList()
FloatList = NativeFloatList()
DoubleList = NativeDoubleList()
ComplexList = NativeComplexList()


dtype_registry = {'bool': Bool,
                  'int': Int,
                  'float': Float,
                  'double': Double,
                  'complex': Complex,
                  'void': Void,
                  'nil': Nil,
                  'vector': _Vector,
                  'stencil': _Stencil,
                  'symbol': _Symbol,
                  '*int': IntegerList,
                  '*float': FloatList,
                  '*double': DoubleList,
                  '*complex': ComplexList,
                  'str': String}


def DataTypeFactory(name, argnames=["_name"], \
                    BaseClass=CustomDataType, \
                    prefix=None, \
                    alias=None, \
                    is_iterable=False, \
                    is_with_construct=False, \
                    is_polymorphic=True):
    def __init__(self, **kwargs):
        for key, value in list(kwargs.items()):
            # here, the argnames variable is the one passed to the
            # DataTypeFactory call
            if key not in argnames:
                raise TypeError("Argument %s not valid for %s"
                    % (key, self.__class__.__name__))
            setattr(self, key, value)
        BaseClass.__init__(self, name[:-len("Class")])

    if prefix is None:
        prefix = 'Pyccel'
    else:
        prefix = 'Pyccel{0}'.format(prefix)

    newclass = type(prefix + name, (BaseClass,),
                    {"__init__":          __init__,
                     "_name":             name,
                     "prefix":            prefix,
                     "alias":             alias,
                     "is_iterable":       is_iterable,
                     "is_with_construct": is_with_construct,
                     "is_polymorphic":    is_polymorphic})
    return newclass

def is_pyccel_datatype(expr):
    return isinstance(expr, CustomDataType)
#    if not isinstance(expr, DataType):
#        raise TypeError('Expecting a DataType instance')
#    name = expr.__class__.__name__
#    return name.startswith('Pyccel')

# TODO improve and remove try/except
def is_iterable_datatype(dtype):
    """Returns True if dtype is an iterable class."""
    try:
        if is_pyccel_datatype(dtype):
            return dtype.is_iterable
        elif isinstance(dtype, (NativeRange, NativeTensor)):
            return True
        else:
            return False
    except:
        return False

# TODO improve and remove try/except
def is_with_construct_datatype(dtype):
    """Returns True if dtype is an with_construct class."""
    try:
        if is_pyccel_datatype(dtype):
            return dtype.is_with_construct
        else:
            return False
    except:
        return False

# TODO check the use of floats
def datatype(arg):
    """Returns the datatype singleton for the given dtype.

    arg : str or sympy expression
        If a str ('bool', 'int', 'float', 'double', or 'void'), return the
        singleton for the corresponding dtype. If a sympy expression, return
        the datatype that best fits the expression. This is determined from the
        assumption system. For more control, use the `DataType` class directly.

    Returns:
        DataType

    """
    def infer_dtype(arg):
        if arg.is_integer:
            return Int
        elif arg.is_Boolean:
            return Bool
        else:
            return Double

    if isinstance(arg, str):
        if arg.lower() not in dtype_registry:
            raise ValueError("Unrecognized datatype " + arg)
        return dtype_registry[arg]
    elif isinstance(arg, (Variable, IndexedVariable, IndexedElement)):
        if isinstance(arg.dtype, DataType):
            return dtype_registry[arg.dtype.name.lower()]
        else:
            raise TypeError('Expecting a DataType')
    else:
        arg = sympify(arg)
        if isinstance(arg, ImmutableDenseMatrix):
            dts = [infer_dtype(i) for i in arg]
            if all([i is Bool for i in dts]):
                return Bool
            elif all([i is Int for i in dts]):
                return Int
            else:
                return Double
        else:
            return infer_dtype(arg)

class EqualityStmt(Relational):
    """Represents a relational equality expression in the code."""
    def __new__(cls,lhs,rhs):
        lhs = sympify(lhs)
        rhs = sympify(rhs)
        return Relational.__new__(cls,lhs,rhs)
    @property
    def canonical(self):
        return self

class NotequalStmt(Relational):
    """Represents a relational not equality expression in the code."""
    def __new__(cls,lhs,rhs):
        lhs = sympify(lhs)
        rhs = sympify(rhs)
        return Relational.__new__(cls,lhs,rhs)


class Is(Basic):
    """Represents a is expression in the code.

    Examples

    >>> from pyccel.ast import Is
    >>> from pyccel.ast import Nil
    >>> from sympy.abc import x
    >>> Is(x, Nil())
    Is(x, None)
    """
    def __new__(cls, lhs, rhs):
        return Basic.__new__(cls, lhs, rhs)

    @property
    def lhs(self):
        return self._args[0]

    @property
    def rhs(self):
        return self._args[1]


# TODO remove kind from here and put it in FunctionDef
class FunctionCall(AtomicExpr):
    """
    Base class for applied mathematical functions.

    It also serves as a constructor for undefined function classes.

    func: FunctionDef, str
        an instance of FunctionDef or function name

    arguments: list, tuple, None
        a list of arguments.

    kind: str
        'function' or 'procedure'. default value: 'function'

    Examples

    Examples

    >>> from pyccel.ast.core import Assign, Variable
    >>> from pyccel.ast.core import FunctionDef
    >>> x = Variable('int', 'x')
    >>> y = Variable('int', 'y')
    >>> args        = [x]
    >>> results     = [y]
    >>> body        = [Assign(y,x+1)]
    >>> incr = FunctionDef('incr', args, results, body)
    >>> n = Variable('int', 'n')
    >>> incr(n)
    incr(n)
    >>> type(incr(n))
    pyccel.ast.core.FunctionCall
    >>> incr(n)*2+1
    1 + 2*incr(n)
    >>> incr(n)+1
    incr(n) + 1
    >>> incr(n)*2
    2*incr(n)
    """
    is_commutative = True

    # TODO improve
    def __new__(cls, func, arguments, cls_variable=None, kind='function'):
        if not isinstance(func, (FunctionDef, str)):
            raise TypeError("Expecting func to be a FunctionDef or str")

        if isinstance(func, FunctionDef):
            kind = func.kind
            f_name = func.name
        else:
            f_name = func

#        if not isinstance(kind, str):
#            raise TypeError("Expecting a string for kind.")
#
#        if not (kind in ['function', 'procedure']):
#            raise ValueError("kind must be one among {'function', 'procedure'}")
#        if isinstance(func,FunctionDef) and func.cls_name and not cls_variable:
#            raise TypeError("Expecting a cls_variable.")

        obj = Basic.__new__(cls, f_name)

        obj._kind         = kind
        obj._func         = func
        obj._arguments    = arguments

        return obj

    def _sympystr(self, printer):
        sstr = printer.doprint
        name = sstr(self.name)
        args = ''
        if not(self.arguments) is None:
            args = ', '.join(sstr(i) for i in self.arguments)
        return '{0}({1})'.format(name, args)

    @property
    def func(self):
        return self._func

    @property
    def kind(self):
        return self._kind

    @property
    def arguments(self):
        return self._arguments

    @property
    def name(self):
        if isinstance(self.func, FunctionDef):
            return self.func.name
        else:
            return self.func


class MethodCall(AtomicExpr):
    """
    Base class for applied mathematical functions.

    It also serves as a constructor for undefined function classes.

    func: FunctionDef, str
        an instance of FunctionDef or function name

    arguments: list, tuple, None
        a list of arguments.

    kind: str
        'function' or 'procedure'. default value: 'function'

    Examples

    Examples

    >>> from pyccel.ast.core import Assign, Variable
    >>> from pyccel.ast.core import FunctionDef
    >>> x = Variable('int', 'x')
    >>> y = Variable('int', 'y')
    >>> args        = [x]
    >>> results     = [y]
    >>> body        = [Assign(y,x+1)]
    >>> incr = FunctionDef('incr', args, results, body)
    >>> n = Variable('int', 'n')
    >>> incr(n)
    incr(n)
    >>> type(incr(n))
    pyccel.ast.core.FunctionCall
    >>> incr(n)*2+1
    1 + 2*incr(n)
    >>> incr(n)+1
    incr(n) + 1
    >>> incr(n)*2
    2*incr(n)
    """

    is_commutative = True

    # TODO improve
    def __new__(cls, func, arguments,cls_variable=None, kind='function'):
        if not isinstance(func, (FunctionDef, str)):
            raise TypeError("Expecting func to be a FunctionDef or str")

        if isinstance(func, FunctionDef):
            kind = func.kind

#        if not isinstance(kind, str):
#            raise TypeError("Expecting a string for kind.")
#
#        if not (kind in ['function', 'procedure']):
#            raise ValueError("kind must be one among {'function', 'procedure'}")
#
#        if isinstance(func,FunctionDef) and func.cls_name and not cls_variable:
#            raise TypeError("Expecting a cls_variable.")

        f_name = func.name

        obj = Basic.__new__(cls, f_name)
        obj._cls_variable=cls_variable

        obj._kind      = kind
        obj._func      = func
        obj._arguments = arguments

        return obj

    def _sympystr(self, printer):
        sstr = printer.doprint
        name = sstr(self.name)
        args = ''
        if not(self.arguments) is None:
            args = ', '.join(sstr(i) for i in self.arguments)
        return '{0}({1})'.format(name, args)

    @property
    def func(self):
        return self._func

    @property
    def kind(self):
        return self._kind

    @property
    def arguments(self):
        return self._arguments
    @property
    def cls_variable(self):
        return self._cls_variable

    @property
    def name(self):
        if isinstance(self.func, FunctionDef):
            return self.func.name
        else:
            return self.func


class ConstructorCall(MethodCall):
    """
    class for a call to class constructor in the code.
    """
    @property
    def this(self):
        return self.arguments[0]

    @property
    def attributs(self):
        """Returns all attributs of the __init__ function."""
        attr = []
        for i in self.func.body:
            if isinstance(i, Assign) and (str(i.lhs).startswith('self.')):
                attr += [i.lhs]
        return attr


class Nil(Basic):
    """
    class for None object in the code.
    """

    def _sympystr(self, printer):
        sstr = printer.doprint
        return sstr('None')


class Variable(Symbol):
    """Represents a typed variable.

    dtype : str, DataType
        The type of the variable. Can be either a DataType,
        or a str (bool, int, float, double).

    name : str, list, DottedName
        The sympy object the variable represents. This can be either a string
        or a dotted name, when using a Class attribut.

    rank : int
        used for arrays. [Default value: 0]

    allocatable: False
        used for arrays, if we need to allocate memory [Default value: False]

    shape: int or list
        shape of the array. [Default value: None]

    cls_base: class
        class base if variable is an object or an object member

    Examples

    >>> from sympy import symbols
    >>> from pyccel.ast.core import Variable
    >>> Variable('int', 'n')
    n
    >>> Variable('float', x, rank=2, shape=(n,2), allocatable=True)
    x
    >>> Variable('int', ('matrix', 'n_rows'))
    matrix.n_rows
    """
    def __new__(cls, dtype, name,
                rank=0,
                allocatable=False,
                is_pointer=False,
                is_target=False,
                is_polymorphic=None,
                is_optional=None,
                shape=None, cls_base=None, cls_parameters=None):

        if isinstance(dtype, str):
            dtype = datatype(dtype)
        elif not isinstance(dtype, DataType):
            raise TypeError("datatype must be an instance of DataType.")

        if is_pointer is None:
            is_pointer = False
        elif not isinstance(is_pointer, bool):
            raise TypeError("is_pointer must be a boolean.")

        if is_target is None:
            is_target = False
        elif not isinstance(is_target, bool):
            raise TypeError("is_target must be a boolean.")

        if is_polymorphic is None:
            if isinstance(dtype, CustomDataType):
                is_polymorphic = dtype.is_polymorphic
            else:
                is_polymorphic = False
        elif not isinstance(is_polymorphic, bool):
            raise TypeError("is_polymorphic must be a boolean.")

        if is_optional is None:
            is_optional = False
        elif not isinstance(is_optional, bool):
            raise TypeError("is_optional must be a boolean.")

        # if class attribut
        if isinstance(name, str):
            name = name.split('.')
            if len(name) == 1:
                name = name[0]
            else:
                name = DottedName(*name)

        if not isinstance(name, (str, DottedName)):
            raise TypeError('Expecting a string or DottedName, '
                            'given {0}'.format(type(name)))

        if not isinstance(rank, int):
            raise TypeError("rank must be an instance of int.")
#        if not shape==None:
#            if  (not isinstance(shape,int) and not isinstance(shape,tuple) and not all(isinstance(n, int) for n in shape)):
#                raise TypeError("shape must be an instance of int or tuple of int")

        # TODO improve order of arguments
        return Basic.__new__(cls, dtype, name, rank, allocatable, shape,
                             cls_base, cls_parameters,
                             is_pointer, is_target, is_polymorphic, is_optional)

    @property
    def dtype(self):
        return self._args[0]

    @property
    def name(self):
        return self._args[1]

    @property
    def rank(self):
        return self._args[2]

    @property
    def allocatable(self):
        return self._args[3]

    @property
    def shape(self):
        return self._args[4]

    @property
    def cls_base(self):
        return self._args[5]

    @property
    def cls_parameters(self):
        return self._args[6]

    @property
    def is_pointer(self):
        return self._args[7]

    @property
    def is_target(self):
        return self._args[8]

    @property
    def is_polymorphic(self):
        return self._args[9]

    @property
    def is_optional(self):
        return self._args[10]

    def __str__(self):
        if isinstance(self.name, (str, DottedName)):
            return str(self.name)
        elif self.name is iterable:
            return '.'.join(str(n) for n in self.name)

    def _sympystr(self, printer):
        sstr = printer.doprint
        if isinstance(self.name, (str, DottedName)):
            return '{}'.format(sstr(self.name))
        elif self.name is iterable:
            return '.'.join(sstr(n) for n in self.name)

    def inspect(self):
        """inspects the variable."""
        print('>>> Variable')
        print('  name           = {}'.format(self.name))
        print('  dtype          = {}'.format(self.dtype))
        print('  rank           = {}'.format(self.rank))
        print('  allocatable    = {}'.format(self.allocatable))
        print('  shape          = {}'.format(self.shape))
        print('  cls_base       = {}'.format(self.cls_base))
        print('  cls_parameters = {}'.format(self.cls_parameters))
        print('  is_pointer     = {}'.format(self.is_pointer))
        print('  is_target      = {}'.format(self.is_target))
        print('  is_polymorphic = {}'.format(self.is_polymorphic))
        print('  is_optional    = {}'.format(self.is_optional))
        print('<<<')

    def clone(self, name):
        # TODO check it is up to date
        cls = eval(self.__class__.__name__)

        return cls(self.dtype,
                   name,
                   rank=self.rank,
                   allocatable=self.allocatable,
                   shape=self.shape,
                   is_pointer=self.is_pointer,
                   is_target=self.is_target,
                   is_polymorphic=self.is_polymorphic,
                   is_optional=self.is_optional,
                   cls_base=self.cls_base,
                   cls_parameters=self.cls_parameters)



class DottedVariable(Atom):
    """
    Represents a dotted variable.
    """
    def __new__(cls, *args):

        if  not isinstance(args[0],(Variable, Symbol, IndexedVariable,
                                    IndexedBase, Indexed, Function,
                                    DottedVariable)):
            raise TypeError('Expecting a Variable or a function call, '
                            'got instead {0} of type {1}'.format(str(args[0]),
                                                                  type(args[0])))

        if  not isinstance(args[1],(Variable, Symbol, IndexedVariable,
                                    IndexedBase, Indexed, Function)):
            raise TypeError('Expecting a Variable or a function call,'
                            ' got instead {0} of type {1}'.format(str(args[1]),
                                                                  type(args[1])))

        return Basic.__new__(cls,args[0],args[1])

    @property
    def args(self):
        return [self._args[0],self._args[1]]

    @ property
    def name(self):
        return self.args[0].name+'.'+self.args[1].name


class ValuedVariable(Variable):
    """Represents a valued variable in the code.

    variable: Variable
        A single variable
    value: Variable, or instance of Native types
        value associated to the variable

    Examples

    >>> from pyccel.ast.core import ValuedVariable
    >>> n  = ValuedVariable('int', 'n', value=4)
    >>> n
    n := 4
    """

    def __new__(cls, *args, **kwargs):

        # if value is not given, we set it to Nil
        # we also remove value from kwargs,
        # since it is not a valid argument for Variable
        value = kwargs.pop('value', Nil())

        obj = Variable.__new__(cls, *args, **kwargs)

        obj._value = value

        return obj

    @property
    def value(self):
        return self._value

    def _sympystr(self, printer):
        sstr = printer.doprint

        name = sstr(self.name)
        value = sstr(self.value)
        return '{0}={1}'.format(name, value)


class Argument(Symbol):
    """An abstract Argument data structure.

    Examples

    >>> from pyccel.ast.core import Argument
    >>> n = Argument('n')
    >>> n
    n
    """
    pass


class ValuedArgument(Basic):
    """Represents a valued argument in the code.

    Examples

    >>> from pyccel.ast.core import ValuedArgument
    >>> n = ValuedArgument('n', 4)
    >>> n
    n=4
    """

    def __new__(cls, expr, value):
        if isinstance(expr, str):
            expr = Argument(expr)

        if not isinstance(expr, Argument):
            raise TypeError('Expecting an argument')

        return Basic.__new__(cls, expr, value)

    @property
    def argument(self):
        return self._args[0]

    @property
    def value(self):
        return self._args[1]

    @property
    def name(self):
        return self.argument.name

    def _sympystr(self, printer):
        sstr = printer.doprint

        argument = sstr(self.argument)
        value    = sstr(self.value)
        return '{0}={1}'.format(argument, value)


# TODO keep sympify?
class Return(Basic):
    """Represents a function return in the code.

    expr : sympy expr
        The expression to return.
    """

    def __new__(cls, expr):
#        expr = _sympify(expr)
        return Basic.__new__(cls, expr)

    @property
    def expr(self):
        return self._args[0]

class FunctionDef(Basic):
    """Represents a function definition.

    name : str
        The name of the function.

    arguments : iterable
        The arguments to the function.

    results : iterable
        The direct outputs of the function.

    body : iterable
        The body of the function.

    local_vars : list of Symbols
        These are used internally by the routine.

    global_vars : list of Symbols
        Variables which will not be passed into the function.

    cls_name: str
        Class name if the function is a method of cls_name

    hide: bool
        if True, the function definition will not be generated.

    kind: str
        'function' or 'procedure'. default value: 'function'

    imports: list, tuple
        a list of needed imports

    Examples

    >>> from pyccel.ast.core import Assign, Variable, FunctionDef
    >>> x = Variable('float', 'x')
    >>> y = Variable('float', 'y')
    >>> args        = [x]
    >>> results     = [y]
    >>> body        = [Assign(y,x+1)]
    >>> FunctionDef('incr', args, results, body)
    FunctionDef(incr, (x,), (y,), [y := 1 + x], [], [], None, False, function)

    One can also use parametrized argument, using ValuedArgument

    >>> from pyccel.ast.core import Variable
    >>> from pyccel.ast.core import Assign
    >>> from pyccel.ast.core import FunctionDef
    >>> from pyccel.ast.core import ValuedArgument
    >>> from pyccel.ast.core import GetDefaultFunctionArg
    >>> n = ValuedArgument('n', 4)
    >>> x = Variable('float', 'x')
    >>> y = Variable('float', 'y')
    >>> args        = [x, n]
    >>> results     = [y]
    >>> body        = [Assign(y,x+n)]
    >>> FunctionDef('incr', args, results, body)
    FunctionDef(incr, (x, n=4), (y,), [y := 1 + x], [], [], None, False, function, [])
    """

    def __new__(cls, name, arguments, results, \
                body, local_vars=[], global_vars=[], \
                cls_name=None, hide=False, kind='function', imports=[]):
        # name
        if isinstance(name, str):
            name = Symbol(name)
        elif isinstance(name,(tuple,list)):
            name_ = []
            for i in name:
                if isinstance(i,str):
                    name = name +Symbol(i)
                elif not isinstance(i, Symbol):
                    raise TypeError("Function name must be Symbol or string")
            name=tuple(name_)

        elif not isinstance(name, Symbol):
            raise TypeError("Function name must be Symbol or string")
        # arguments
        if not iterable(arguments):
            raise TypeError("arguments must be an iterable")
        # TODO improve and uncomment
#        if not all(isinstance(a, Argument) for a in arguments):
#            raise TypeError("All arguments must be of type Argument")
        arguments = Tuple(*arguments)
        # body
        if not iterable(body):
            raise TypeError("body must be an iterable")
#        body = Tuple(*(i for i in body))
        # results
        if not iterable(results):
            raise TypeError("results must be an iterable")
        results = Tuple(*results)
        # if method
        if cls_name:

            if not(isinstance(cls_name, str)):
                raise TypeError("cls_name must be a string")
            #if not cls_variable:
             #   raise TypeError('Expecting a instance of {0}'.format(cls_name))

        if kind is None:
            kind = 'function'

        if not isinstance(kind, str):
            raise TypeError("Expecting a string for kind.")

        if not (kind in ['function', 'procedure']):
            raise ValueError("kind must be one among {'function', 'procedure'}")

        if not iterable(imports):
            raise TypeError("imports must be an iterable")

        return Basic.__new__(cls, name, \
                             arguments, results, \
                             body, \
                             local_vars, global_vars, \
                             cls_name,hide, kind, imports)

    @property
    def name(self):
        return self._args[0]

    @property
    def arguments(self):
        return self._args[1]

    @property
    def results(self):
        return self._args[2]

    @property
    def body(self):
        return self._args[3]

    @property
    def local_vars(self):
        return self._args[4]

    @property
    def global_vars(self):
        return self._args[5]

    @property
    def cls_name(self):
        return self._args[6]


    @property
    def hide(self):
        return self._args[7]

    @property
    def kind(self):
        return self._args[8]

    @property
    def imports(self):
        return self._args[9]

    def print_body(self):
        for s in self.body:
            print (s)

  #  def set_name(self,new_name):
   #         return FunctionDef(new_name, self.arguments, self.results, self.body, self.local_vars,
    #                  self.global_vars, self.cls_name, self.hide, self.kind, self.imports)

#    @property
#    def declarations(self):
#        ls = self.arguments + self.results + self.local_vars
#        return [Declare(i.dtype, i) for i in ls]

    def rename(self, newname):
        """
        Rename the FunctionDef name by creating a new FunctionDef with
        newname.

        newname: str
            new name for the FunctionDef
        """
        return FunctionDef(newname, self.arguments, self.results, self.body, \
                           local_vars=self.local_vars, \
                           global_vars=self.global_vars, \
                           cls_name=self.cls_name, \
                           hide=self.hide, \
                           kind=self.kind)

    def __call__(self, *args, **kwargs):
        """Represents a call to the function."""
        # TODO treat parametrized arguments.
        #      this will be done later, once it is validated for FunctionCall

        # we remove 'self' from arguments
        f_args = self.arguments[1:]
        args = list(args)
        print args
        print f_args
        assert(len(args) == len(f_args))

        return FunctionCall(self, args)

    @property
    def is_procedure(self):
        """Returns True if a procedure."""
        #flag = ((len(self.results) == 1) and (self.results[0].allocatable))
        flag = ((len(self.results) == 1) and (self.results[0].rank > 0))
        flag = flag or (len(self.results) > 1)
        flag = flag or (len(self.results) == 0)
        flag = flag or (self.kind == 'procedure')

        return flag

    def is_compatible_header(self, header):
        """
        Returns True if the header is compatible with the given FunctionDef.

        header: Header
            a pyccel header suppose to describe the FunctionDef
        """
        cond_args    = (len(self.arguments) == len(header.dtypes))
        cond_results = (len(self.results)   == len(header.results))

        header_with_results = (len(header.results) > 0)

        if not cond_args:
            return False

        if header_with_results and not cond_results:
            return False

        return True


class GetDefaultFunctionArg(Basic):
    """Creates a FunctionDef for handling optional arguments in the code.

    arg: ValuedArgument, ValuedVariable
        argument for which we want to create the function returning the default
        value

    func: FunctionDef
        the function/subroutine in which the optional arg is used

    Examples

    >>> from pyccel.ast.core import Variable
    >>> from pyccel.ast.core import Assign
    >>> from pyccel.ast.core import FunctionDef
    >>> from pyccel.ast.core import ValuedArgument
    >>> from pyccel.ast.core import GetDefaultFunctionArg
    >>> n = ValuedArgument('n', 4)
    >>> x = Variable('float', 'x')
    >>> y = Variable('float', 'y')
    >>> args        = [x, n]
    >>> results     = [y]
    >>> body        = [Assign(y,x+n)]
    >>> incr = FunctionDef('incr', args, results, body)
    >>> get_n = GetDefaultFunctionArg(n, incr)
    >>> get_n.name
    get_default_incr_n
    >>> get_n
    get_default_incr_n(n=4)

    You can also use **ValuedVariable** as in the following example

    >>> from pyccel.ast.core import ValuedVariable
    >>> n = ValuedVariable('int', 'n', value=4)
    >>> x = Variable('float', 'x')
    >>> y = Variable('float', 'y')
    >>> args        = [x, n]
    >>> results     = [y]
    >>> body        = [Assign(y,x+n)]
    >>> incr = FunctionDef('incr', args, results, body)
    >>> get_n = GetDefaultFunctionArg(n, incr)
    >>> get_n
    get_default_incr_n(n=4)
    """

    def __new__(cls, arg, func):

        if not isinstance(arg, (ValuedArgument, ValuedVariable)):
            raise TypeError('Expecting a ValuedArgument or ValuedVariable')

        if not isinstance(func, FunctionDef):
            raise TypeError('Expecting a FunctionDef')

        return Basic.__new__(cls, arg, func)

    @property
    def argument(self):
        return self._args[0]

    @property
    def func(self):
        return self._args[1]

    @property
    def name(self):
        text = 'get_default_{func}_{arg}'.format(arg=self.argument.name,
                                                 func=self.func.name)
        return text

    def _sympystr(self, printer):
        sstr = printer.doprint

        name = sstr(self.name)
        argument = sstr(self.argument)
        return '{0}({1})'.format(name, argument)


class ClassDef(Basic):
    """Represents a class definition.

    name : str
        The name of the class.

    attributs: iterable
        The attributs to the class.

    methods: iterable
        Class methods

    options: list, tuple
        list of options ('public', 'private', 'abstract')

    imports: list, tuple
        list of needed imports

    Examples

    >>> from pyccel.ast.core import Variable, Assign
    >>> from pyccel.ast.core import ClassDef, FunctionDef
    >>> x = Variable('double', 'x')
    >>> y = Variable('double', 'y')
    >>> z = Variable('double', 'z')
    >>> t = Variable('double', 't')
    >>> a = Variable('double', 'a')
    >>> b = Variable('double', 'b')
    >>> body = [Assign(y,x+a)]
    >>> translate = FunctionDef('translate', [x,y,a,b], [z,t], body)
    >>> attributs   = [x,y]
    >>> methods     = [translate]
    >>> ClassDef('Point', attributs, methods)
    ClassDef(Point, (x, y), (FunctionDef(translate, (x, y, a, b), (z, t), [y := a + x], [], [], None, False, function),), [public])
    """

    def __new__(cls, name, attributs, methods, \
                options=['public'], imports=[]):
        # name
        if isinstance(name, str):
            name = Symbol(name)
        elif not isinstance(name, Symbol):
            raise TypeError("Function name must be Symbol or string")
        # attributs
        if not iterable(attributs):
            raise TypeError("attributs must be an iterable")
        attributs = Tuple(*attributs)
        # methods
        if not iterable(methods):
            raise TypeError("methods must be an iterable")
        # options
        if not iterable(options):
            raise TypeError("options must be an iterable")
        # imports
        if not iterable(imports):
            raise TypeError("imports must be an iterable")

        for i in methods:
            imports += i.imports
        imports = set(imports) # for unicity
        imports = Tuple(*imports)

        # ...
        # look if the class has the method __del__
        d_methods = {}
        for i in methods:
            d_methods[str(i.name).replace('\'','')] = i
        if not ('__del__' in d_methods):
            dtype = DataTypeFactory(str(name), ("_name"), prefix='Custom')
            this  = Variable(dtype(), 'self')

            # constructs the __del__ method if not provided
            args = []
            for a in attributs:
                if isinstance(a, Variable):
                    if a.allocatable:
                        args.append(a)

            args = [Variable(a.dtype, DottedName(str(this), str(a.name))) for a in args]
            body = [Del(a) for a in args]

            free = FunctionDef('__del__', [this], [], \
                               body, local_vars=[], global_vars=[], \
                               cls_name='__UNDEFINED__', kind='procedure', imports=[])

            methods = list(methods) + [free]
        methods = Tuple(*methods)
        # ...

        return Basic.__new__(cls, name, attributs, methods, options, imports)

    @property
    def name(self):
        return self._args[0]

    @property
    def attributs(self):
        return self._args[1]

    @property
    def methods(self):
        return self._args[2]

    @property
    def options(self):
        return self._args[3]

    @property
    def imports(self):
        return self._args[4]

    @property
    def methods_as_dict(self):
        """Returns a dictionary that contains all methods, where the key is the
        method's name."""
        d_methods = {}
        for i in self.methods:
            d_methods[str(i.name)] = i
        return d_methods

    @property
    def attributs_as_dict(self):
        """Returns a dictionary that contains all attributs, where the key is the
        attribut's name."""
        d_attributs = {}
        for i in self.attributs:
            d_attributs[str(i.name)] = i
        return d_attributs

    # TODO add other attributs?
    @property
    def this(self):
        alias  = None
        name   = str(self.name)
        dtype = DataTypeFactory(name, ("_name"), \
                                prefix='Custom', \
                                alias=alias)

        return Variable(dtype(), 'self')

    def get_attribute(self, O, attr):
        """Returns the attribute attr of the class O of instance self."""
        if not isinstance(attr, str):
            raise TypeError('Expecting attribute to be a string')

        if isinstance(O, Variable):
            cls_name = str(O.name)
        else:
            cls_name = str(O)

        attributs = {}
        for i in self.attributs:
            attributs[str(i.name)] = i

        if not attr in attributs:
            raise ValueError('{0} is not an attribut of {1}'.format(attr, str(self)))

        var = attributs[attr]
        name = DottedName(cls_name, str(var.name))
        return Variable(var.dtype, name, \
                        rank=var.rank, \
                        allocatable=var.allocatable, \
                        shape=var.shape, \
                        cls_base=var.cls_base)

    @property
    def is_iterable(self):
        """Returns True if the class has an iterator."""
        names = [str(m.name) for m in self.methods]
        if ('__next__' in names) and ('__iter__' in names):
            return True
        elif ('__next__' in names):
            raise ValueError('ClassDef does not contain __iter__ method')
        elif ('__iter__' in names):
            raise ValueError('ClassDef does not contain __next__ method')
        else:
            return False

    @property
    def is_with_construct(self):
        """Returns True if the class is a with construct."""
        names = [str(m.name) for m in self.methods]
        if ('__enter__' in names) and ('__exit__' in names):
            return True
        elif ('__enter__' in names):
            raise ValueError('ClassDef does not contain __exit__ method')
        elif ('__exit__' in names):
            raise ValueError('ClassDef does not contain __enter__ method')
        else:
            return False

    @property
    def hide(self):
        if 'hide' in self.options:
            return True
        else:
            return self.is_iterable or self.is_with_construct

class Ceil(Function):
    """
    Represents ceil expression in the code.

    rhs: symbol or number
        input for the ceil function

    >>> from sympy import symbols
    >>> from pyccel.ast.core import Ceil, Variable
    >>> n,x,y = symbols('n,x,y')
    >>> var = Variable('float', x)
    >>> Ceil(x)
    Ceil(x)
    >>> Ceil(var)
    Ceil(x)
    """
    def __new__(cls,rhs):
        return Basic.__new__(cls,rhs)

    @property
    def rhs(self):
        return self._args[0]

class Import(Basic):
    """Represents inclusion of dependencies in the code.

    fil : str
        The filepath of the module (i.e. header in C).
    funcs
        The name of the function (or an iterable of names) to be imported.

    Examples

    >>> from pyccel.ast.core import Import
    >>> Import('numpy', 'linspace')
    Import(numpy, (linspace,))

    >>> from pyccel.ast.core import DottedName
    >>> from pyccel.ast.core import Import
    >>> mpi = DottedName('pyccel', 'stdlib', 'parallel', 'mpi')
    >>> Import(mpi, 'mpi_init')
    Import(pyccel.stdlib.parallel.mpi, (mpi_init,))
    >>> Import(mpi, '*')
    Import(pyccel.stdlib.parallel.mpi, (*,))
    """

    def __new__(cls, fil, funcs=None):
        if not isinstance(fil, (str, DottedName)):
            raise TypeError('Expecting a string or DottedName')

        if funcs:
            if iterable(funcs):
                funcs = Tuple(*[Symbol(f) for f in funcs])
            elif not isinstance(funcs, (str, DottedName)):
                raise TypeError("Unrecognized funcs type: ", funcs)

        return Basic.__new__(cls, fil, funcs)

    @property
    def fil(self):
        return self._args[0]

    @property
    def funcs(self):
        return self._args[1]

class Load(Basic):
    """Similar to 'importlib' in python. In addition, we can also provide the
    functions we want to import.

    module: str, DottedName
        name of the module to load.

    funcs: str, list, tuple, Tuple
        a string representing the function to load, or a list of strings.

    as_lambda: bool
        load as a Lambda expression, if True

    nargs: int
        number of arguments of the function to load. (default = 1)

    Examples

    >>> from pyccel.ast.core import Load
    """

    def __new__(cls, module, funcs=None, as_lambda=False, nargs=1):
        if not isinstance(module, (str, DottedName, list, tuple, Tuple)):
            raise TypeError('Expecting a string or DottedName, given'
                            ' {0}'.format(type(module)))

        # see syntax
        if isinstance(module, str):
            module = module.replace('__', '.')

        if isinstance(module, (list, tuple, Tuple)):
            module = DottedName(*module)

        if funcs:
            if not isinstance(funcs, (str, DottedName, list, tuple, Tuple)):
                raise TypeError('Expecting a string or DottedName')

            if isinstance(funcs, str):
                funcs = [funcs]
            elif not isinstance(funcs, (list, tuple, Tuple)):
                raise TypeError('Expecting a string, list, tuple, Tuple')

        if not isinstance(as_lambda, (BooleanTrue, BooleanFalse, bool)):
            raise TypeError('Expecting a boolean, given {0}'.format(as_lambda))

        return Basic.__new__(cls, module, funcs, as_lambda, nargs)

    @property
    def module(self):
        return self._args[0]

    @property
    def funcs(self):
        return self._args[1]

    @property
    def as_lambda(self):
        return self._args[2]

    @property
    def nargs(self):
        return self._args[3]

    def execute(self):
        module = str(self.module)
        try:
            package = importlib.import_module(module)
        except:
            raise ImportError('could not import {0}'.format(module))

        ls = []
        for f in self.funcs:
            try:
                m = getattr(package, '{0}'.format(str(f)))
            except:
                raise ImportError('could not import {0}'.format(f))

            # TODO improve
            if self.as_lambda:
                args = []
                for i in range(0, self.nargs):
                    fi = Symbol('f{0}'.format(i))
                    args.append(fi)
                if len(args) == 1:
                    arg = args[0]
                    m = Lambda(arg, m(arg, evaluate=False))
                else:
                    m = Lambda(args, m(*args, evaluate=False))

            ls.append(m)

        return ls


# TODO: Should Declare have an optional init value for each var?


class Declare(Basic):
    """Represents a variable declaration in the code.

    dtype : DataType
        The type for the declaration.
    variable(s)
        A single variable or an iterable of Variables. If iterable, all
        Variables must be of the same type.
    intent: None, str
        one among {'in', 'out', 'inout'}
    value: Expr
        variable value

    Examples

    >>> from pyccel.ast.core import Declare, Variable
    >>> Declare('int', Variable('int', 'n'))
    Declare(NativeInteger(), (n,), None)
    >>> Declare('double', Variable('double', 'x'), intent='out')
    Declare(NativeDouble(), (x,), out)
    """

    def __new__(cls, dtype, variables, intent=None, value=None):
        if isinstance(dtype, str):
            dtype = datatype(dtype)
        elif not isinstance(dtype, DataType):
            raise TypeError("datatype must be an instance of DataType.")

        if not isinstance(variables, (list, tuple, Tuple)):
            variables = [variables]
        for var in variables:
            if not isinstance(var, Variable):
                raise TypeError("var must be of type Variable, given {0}".format(var))
            if var.dtype != dtype:
                raise ValueError("All variables must have the same dtype")
        variables = Tuple(*variables)

        if intent:
            if not(intent in ['in', 'out', 'inout']):
                raise ValueError("intent must be one among {'in', 'out', 'inout'}")
        return Basic.__new__(cls, dtype, variables, intent, value)

    @property
    def dtype(self):
        return self._args[0]

    @property
    def variables(self):
        return self._args[1]

    @property
    def intent(self):
        return self._args[2]

    @property
    def value(self):
        return self._args[3]

class Break(Basic):
    """Represents a break in the code."""
    pass

class Continue(Basic):
    """Represents a continue in the code."""
    pass

class Raise(Basic):
    """Represents a raise in the code."""
    pass

# TODO: improve with __new__ from Function and add example
class Random(Function):
    """
    Represents a 'random' number in the code.
    """
    # TODO : remove later
    def __str__(self):
        return "random"

    def __new__(cls, seed):
        return Basic.__new__(cls, seed)

    @property
    def seed(self):
        return self._args[0]


# TODO: improve with __new__ from Function and add example
class Len(Function):
    """
    Represents a 'len' expression in the code.
    """
    # TODO : remove later
    def __str__(self):
        return "len"

    def __new__(cls, rhs):
        return Basic.__new__(cls, rhs)

    @property
    def rhs(self):
        return self._args[0]

# TODO add example
class Shape(Function):
    """
    Represents a 'shape' expression in the code.
    """
    # TODO : remove later
    def __str__(self):
        return "shape"

    def __new__(cls, rhs):
        return Basic.__new__(cls, rhs)

    @property
    def rhs(self):
        return self._args[0]

# TODO: add example
class Min(Function):
    """Represents a 'min' expression in the code."""
    def __new__(cls, *args):
        return Basic.__new__(cls, *args)

# TODO: add example
class Max(Function):
    """Represents a 'max' expression in the code."""
    def __new__(cls, *args):
        return Basic.__new__(cls, *args)

# TODO: add example
class Mod(Function):
    """Represents a 'mod' expression in the code."""
    def __new__(cls, *args):
        return Basic.__new__(cls, *args)

# TODO: improve with __new__ from Function and add example
class Dot(Function):
    """
    Represents a 'dot' expression in the code.

    expr_l: variable
        first variable
    expr_r: variable
        second variable
    """
    def __new__(cls, expr_l, expr_r):
        return Basic.__new__(cls, expr_l, expr_r)

    @property
    def expr_l(self):
        return self.args[0]

    @property
    def expr_r(self):
        return self.args[1]

# TODO: treat as a Function
# TODO: add example
class Sign(Basic):

    def __new__(cls,expr):
        return Basic.__new__(cls, expr)

    @property
    def rhs(self):
        return self.args[0]

class Zeros(Basic):
    """Represents variable assignment using numpy.zeros for code generation.

    lhs : Expr
        Sympy object representing the lhs of the expression. These should be
        singular objects, such as one would use in writing code. Notable types
        include Symbol, MatrixSymbol, MatrixElement, and Indexed. Types that
        subclass these types are also supported.

    shape : int, list, tuple
        int or list of integers

    grid : Range, Tensor
        ensures a one-to-one representation of the array.

    Examples

    >>> from pyccel.ast.core import Variable, Zeros
    >>> n = Variable('int', 'n')
    >>> m = Variable('int', 'm')
    >>> x = Variable('int', 'x')
    >>> Zeros(x, (n,m))
    x := 0
    >>> y = Variable('bool', 'y')
    >>> Zeros(y, (n,m))
    y := False
    """
    # TODO improve in the spirit of assign
    def __new__(cls, lhs, shape=None, grid=None):
        lhs   = sympify(lhs)

        if shape:
            if isinstance(shape, list):
                # this is a correction. otherwise it is not working on LRZ
                if isinstance(shape[0], list):
                    shape = Tuple(*(sympify(i) for i in shape[0]))
                else:
                    shape = Tuple(*(sympify(i) for i in shape))
            elif isinstance(shape, int):
                shape = Tuple(sympify(shape))
            elif isinstance(shape,Len):
                shape = shape.str
            else:
                shape = shape

        if grid:
            if not isinstance(grid, (Range, Tensor, Variable)):
                raise TypeError('Expecting a Range, Tensor or a Variable object.')

        # Tuple of things that can be on the lhs of an assignment
        assignable = (Symbol, MatrixSymbol, MatrixElement, Indexed, Idx)
        if not isinstance(lhs, assignable):
            raise TypeError("Cannot assign to lhs of type %s." % type(lhs))

        return Basic.__new__(cls, lhs, shape, grid)

    def _sympystr(self, printer):
        sstr = printer.doprint
        return '{0} := {1}'.format(sstr(self.lhs), sstr(self.init_value))

    @property
    def lhs(self):
        return self._args[0]

    @property
    def shape(self):
        if self._args[1]:
            return self._args[1]
        else:
            ranges = self.grid.ranges
            sh = [r.size for r in ranges]
            return Tuple(*(i for i in sh))

    @property
    def grid(self):
        return self._args[2]

    @property
    def init_value(self):
        dtype = self.lhs.dtype
        if isinstance(dtype, NativeInteger):
            value = 0
        elif isinstance(dtype, NativeFloat):
            value = 0.0
        elif isinstance(dtype, NativeDouble):
            value = 0.0
        elif isinstance(dtype, NativeComplex):
            value = 0.0
        elif isinstance(dtype, NativeBool):
            value = BooleanFalse()
        else:
            raise TypeError('Unknown type')
        return value

class Ones(Zeros):
    """
    Represents variable assignment using numpy.ones for code generation.

    lhs : Expr
        Sympy object representing the lhs of the expression. These should be
        singular objects, such as one would use in writing code. Notable types
        include Symbol, MatrixSymbol, MatrixElement, and Indexed. Types that
        subclass these types are also supported.

    shape : int or list of integers

    Examples

    >>> from pyccel.ast.core import Variable, Ones
    >>> n = Variable('int', 'n')
    >>> m = Variable('int', 'm')
    >>> x = Variable('int', 'x')
    >>> Ones(x, (n,m))
    x := 1
    >>> y = Variable('bool', 'y')
    >>> Ones(y, (n,m))
    y := True
    """
    @property
    def init_value(self):
        dtype = self.lhs.dtype
        if isinstance(dtype, NativeInteger):
            value = 1
        elif isinstance(dtype, NativeFloat):
            value = 1.0
        elif isinstance(dtype, NativeDouble):
            value = 1.0
        elif isinstance(dtype, NativeComplex):
            value = 1.0
        elif isinstance(dtype, NativeBool):
            value = BooleanTrue()
        else:
            raise TypeError('Unknown type')
        return value

# TODO: add example
class Array(Basic):
    """Represents variable assignment using numpy.array for code generation.

    lhs : Expr
        Sympy object representing the lhs of the expression. These should be
        singular objects, such as one would use in writing code. Notable types
        include Symbol, MatrixSymbol, MatrixElement, and Indexed. Types that
        subclass these types are also supported.

    rhs : Expr
        Sympy object representing the rhs of the expression. These should be
        singular objects, such as one would use in writing code. Notable types
        include Symbol, MatrixSymbol, MatrixElement, and Indexed. Types that
        subclass these types are also supported.

    shape : int or list of integers
    """
    def __new__(cls, lhs,rhs,shape):
        lhs   = sympify(lhs)


        # Tuple of things that can be on the lhs of an assignment
        assignable = (Symbol, MatrixSymbol, MatrixElement, Indexed, Idx)
        if not isinstance(lhs, assignable):
            raise TypeError("Cannot assign to lhs of type %s." % type(lhs))
        if not isinstance(rhs, (list, ndarray)):
            raise TypeError("cannot assign rhs of type %s." % type(rhs))
        if not isinstance(shape, tuple):
            raise TypeError("shape must be of type tuple")


        return Basic.__new__(cls, lhs, rhs,shape)

    def _sympystr(self, printer):
        sstr = printer.doprint
        return '{0} := 0'.format(sstr(self.lhs))

    @property
    def lhs(self):
        return self._args[0]

    @property
    def rhs(self):
        return self._args[1]

    @property
    def shape(self):
        return self._args[2]

# TODO - add examples
class ZerosLike(Basic):
    """Represents variable assignment using numpy.zeros_like for code generation.

    lhs : Expr
        Sympy object representing the lhs of the expression. These should be
        singular objects, such as one would use in writing code. Notable types
        include Symbol, MatrixSymbol, MatrixElement, and Indexed. Types that
        subclass these types are also supported.

    rhs : Variable
        the input variable

    Examples

    >>> from sympy import symbols
    >>> from pyccel.ast.core import Zeros, ZerosLike
    >>> n,m,x = symbols('n,m,x')
    >>> y = Zeros(x, (n,m))
    >>> z = ZerosLike(y)
    """
    # TODO improve in the spirit of assign
    def __new__(cls, lhs, rhs):
        if isinstance(lhs, str):
            lhs = Symbol(lhs)
        # Tuple of things that can be on the lhs of an assignment
        assignable = (Symbol, MatrixSymbol, MatrixElement, \
                      Indexed, Idx, Variable)
        if not isinstance(lhs, assignable):
            raise TypeError("Cannot assign to lhs of type %s." % type(lhs))

        return Basic.__new__(cls, lhs, rhs)

    def _sympystr(self, printer):
        sstr = printer.doprint
        return '{0} := 0'.format(sstr(self.lhs))

    @property
    def lhs(self):
        return self._args[0]

    @property
    def rhs(self):
        return self._args[1]

    @property
    def init_value(self):
        def _native_init_value(dtype):
            if isinstance(dtype, NativeInteger):
                return 0
            elif isinstance(dtype, NativeFloat):
                return 0.0
            elif isinstance(dtype, NativeDouble):
                return 0.0
            elif isinstance(dtype, NativeComplex):
                return 0.0
            elif isinstance(dtype, NativeBool):
                return BooleanFalse()
            raise TypeError('Expecting a Native type, given {}'.format(dtype))

        _native_types = (NativeInteger, NativeFloat, NativeDouble,
                         NativeComplex, NativeBool)

        rhs = self.rhs
        if isinstance(rhs.dtype, _native_types):
            return _native_init_value(rhs.dtype)
        elif isinstance(rhs, (Variable, IndexedVariable)):
            return _native_init_value(rhs.dtype)
        elif isinstance(rhs, IndexedElement):
            return _native_init_value(rhs.base.dtype)
        else:
            raise TypeError('Unknown type for {name}, given '
                            '{dtype}'.format(dtype=type(rhs), name=rhs))

# TODO: treat as a function
class Print(Basic):
    """Represents a print function in the code.

    expr : sympy expr
        The expression to return.

    Examples

    >>> from sympy import symbols
    >>> from pyccel.ast.core import Print
    >>> n,m = symbols('n,m')
    >>> Print(('results', n,m))
    Print((results, n, m))
    """

    def __new__(cls, expr):
        if not isinstance(expr, list):
            expr = sympify(expr)
        return Basic.__new__(cls, expr)

    @property
    def expr(self):
        return self._args[0]

class Del(Basic):
    """Represents a memory deallocation in the code.

    variables : list, tuple
        a list of pyccel variables

    Examples

    >>> from pyccel.ast.core import Del, Variable
    >>> x = Variable('float', 'x', rank=2, shape=(10,2), allocatable=True)
    >>> Del([x])
    Del([x])
    """

    def __new__(cls, expr):
        # TODO: check that the variable is allocatable
        if not iterable(expr):
            expr = Tuple(expr)
        return Basic.__new__(cls, expr)

    @property
    def variables(self):
        return self._args[0]

class EmptyLine(Basic):
    """Represents a EmptyLine in the code.

    text : str
       the comment line

    Examples

    >>> from pyccel.ast.core import EmptyLine
    >>> EmptyLine()

    """

    def __new__(cls):
        return Basic.__new__(cls)

    def _sympystr(self, printer):
        return '\n'

class Comment(Basic):
    """Represents a Comment in the code.

    text : str
       the comment line

    Examples

    >>> from pyccel.ast.core import Comment
    >>> Comment('this is a comment')
    # this is a comment
    """

    def __new__(cls, text):
        return Basic.__new__(cls, text)

    @property
    def text(self):
        return self._args[0]

    def _sympystr(self, printer):
        sstr = printer.doprint
        return '# {0}'.format(sstr(self.text))

class SeparatorComment(Comment):
    """Represents a Separator Comment in the code.

    mark : str
        marker

    Examples

    >>> from pyccel.ast.core import SeparatorComment
    >>> SeparatorComment(n=40)
    # ........................................
    """

    def __new__(cls, n):
        text = "."*n
        return Comment.__new__(cls, text)


class AnnotatedComment(Basic):
    """Represents a Annotated Comment in the code.

    accel : str
       accelerator id. One among {'omp', 'acc'}

    txt: str
        statement to print

    Examples

    >>> from pyccel.ast.core import AnnotatedComment
    >>> AnnotatedComment('omp', 'parallel')
    AnnotatedComment(omp, parallel)
    """
    def __new__(cls, accel, txt):
        return Basic.__new__(cls, accel, txt)

    @property
    def accel(self):
        return self._args[0]

    @property
    def txt(self):
        return self._args[1]

class IndexedVariable(IndexedBase):
    """
    Represents an indexed variable, like x in x[i], in the code.

    Examples

    >>> from sympy import symbols, Idx
    >>> from pyccel.ast.core import IndexedVariable
    >>> A = IndexedVariable('A'); A
    A
    >>> type(A)
    <class 'pyccel.ast.core.IndexedVariable'>

    When an IndexedVariable object receives indices, it returns an array with named
    axes, represented by an IndexedElement object:

    >>> i, j = symbols('i j', integer=True)
    >>> A[i, j, 2]
    A[i, j, 2]
    >>> type(A[i, j, 2])
    <class 'pyccel.ast.core.IndexedElement'>

    The IndexedVariable constructor takes an optional shape argument.  If given,
    it overrides any shape information in the indices. (But not the index
    ranges!)

    >>> m, n, o, p = symbols('m n o p', integer=True)
    >>> i = Idx('i', m)
    >>> j = Idx('j', n)
    >>> A[i, j].shape
    (m, n)
    >>> B = IndexedVariable('B', shape=(o, p))
    >>> B[i, j].shape
    (m, n)

    **todo:** fix bug. the last result must be : (o,p)
    """

    def __new__(cls, label, shape=None, dtype=None, **kw_args):
        if dtype:
            if isinstance(dtype, str):
                dtype = datatype(dtype)
            elif not isinstance(dtype, DataType):
                raise TypeError("datatype must be an instance of DataType.")

        obj = IndexedBase.__new__(cls, label, shape=shape, **kw_args)
        obj._dtype = dtype
        return obj

    def __getitem__(self,*args):

        if self.shape and len(self.shape) != len(args):
            raise IndexException("Rank mismatch.")
        return IndexedElement(self,*args)

    @property
    def dtype(self):
        return self._dtype

    @property
    def name(self):
        return self._args[0]

    # TODO what about kw_args in __new__?
    def clone(self, name):
        cls = eval(self.__class__.__name__)

        return cls(name, shape=self.shape, dtype=self.dtype)


class IndexedElement(Indexed):
    """
    Represents a mathematical object with indices.

    Examples

    >>> from sympy import symbols, Idx
    >>> from pyccel.ast.core import IndexedVariable
    >>> i, j = symbols('i j', cls=Idx)
    >>> IndexedElement('A', i, j)
    A[i, j]

    It is recommended that ``IndexedElement`` objects be created via ``IndexedVariable``:

    >>> from pyccel.ast.core import IndexedElement
    >>> A = IndexedVariable('A')
    >>> IndexedElement('A', i, j) == A[i, j]
    False

    **todo:** fix bug. the last result must be : True
    """
    def __new__(cls, base, *args, **kw_args):
        from sympy.utilities.misc import filldedent
        from sympy.tensor.array.ndim_array import NDimArray
        from sympy.matrices.matrices import MatrixBase

        if not args:
            raise IndexException("Indexed needs at least one index.")
        if isinstance(base, (string_types, Symbol)):
            base = IndexedBase(base)
        elif not hasattr(base, '__getitem__') and not isinstance(base, IndexedBase):
            raise TypeError(filldedent("""
                Indexed expects string, Symbol, or IndexedBase as base."""))
        args = list(map(sympify, args))
        if isinstance(base, (NDimArray, collections.Iterable, Tuple, MatrixBase)) and all([i.is_number for i in args]):
            if len(args) == 1:
                return base[args[0]]
            else:
                return base[args]

        return Expr.__new__(cls, base, *args, **kw_args)

    @property
    def rank(self):
        """
        Returns the rank of the ``IndexedElement`` object.

        Examples

        >>> from sympy import Indexed, Idx, symbols
        >>> i, j, k, l, m = symbols('i:m', cls=Idx)
        >>> Indexed('A', i, j).rank
        2
        >>> q = Indexed('A', i, j, k, l, m)
        >>> q.rank
        5
        >>> q.rank == len(q.indices)
        True

        """
        n = 0
        for a in self.args[1:]:
            if not(isinstance(a, Slice)):
                n += 1
        return n

    @property
    def dtype(self):
        return self.base.dtype


class Concatinate(Basic):
    """Represents the String concatination operation.

    left : Symbol or string

    right : Symbol or string


    Examples

    >>> from sympy import symbols
    >>> from pyccel.ast.core import Concatinate
    >>> x = symbols('x')
    >>> Concatinate('some_string',x)
    some_string+x
    >>> Concatinate(None,x)
    x
    >>> Concatinate(x,None)
    x
    >>> Concatinate('some_string','another_string')
    'some_string' + 'another_string'
    """
    # TODO add step

    def __new__(cls, left, right):
        if isinstance(left,str):
           left = repr(left)
        if isinstance(right,str):
           right = repr(right)
        return Basic.__new__(cls, left, right)

    @property
    def left(self):
        return self._args[0]

    @property
    def right(self):
        return self._args[1]

    def _sympystr(self, printer):
        sstr = printer.doprint
        left = self.left
        right = self.right
        if left is None:
            return right

        if right is None:
            return left

        return '{0}+{1}'.format(left, right)

# TODO check that args are integers
class Slice(Basic):
    """Represents a slice in the code.

    start : Symbol or int
        starting index

    end : Symbol or int
        ending index

    Examples

    >>> from sympy import symbols
    >>> from pyccel.ast.core import Slice
    >>> m, n = symbols('m, n', integer=True)
    >>> Slice(m,n)
    m : n
    >>> Slice(None,n)
     : n
    >>> Slice(m,None)
    m :
    """
    # TODO add step

    def __new__(cls, start, end):
        return Basic.__new__(cls, start, end)

    @property
    def start(self):
        return self._args[0]

    @property
    def end(self):
        return self._args[1]

    def _sympystr(self, printer):
        sstr = printer.doprint
        if self.start is None:
            start = ''
        else:
            start = sstr(self.start)
        if self.end is None:
            end = ''
        else:
            end = sstr(self.end)
        return '{0} : {1}'.format(start, end)

class Assert(Basic):
    """Represents a assert statement in the code.

    test: Expr
        boolean expression to check

    Examples

    """
    def __new__(cls, test):
        if not isinstance(test, (bool, Relational, Boolean)):
            raise TypeError(
                "test %s is of type %s, but must be a Relational,"
                " Boolean, or a built-in bool." % (test, type(test)))

        return Basic.__new__(cls, test)

    @property
    def test(self):
        return self._args[0]

class Eval(Basic):
    """Basic class for eval instruction."""
    pass

class Pass(Basic):
    """Basic class for pass instruction."""
    pass

class Exit(Basic):
    """Basic class for exists."""
    pass

class ErrorExit(Exit):
    """Exist with error."""
    pass

class If(Basic):
    """Represents a if statement in the code.

    args :
        every argument is a tuple and
        is defined as (cond, expr) where expr is a valid ast element
        and cond is a boolean test.

    Examples

    >>> from sympy import Symbol
    >>> from pyccel.ast.core import Assign, If
    >>> n = Symbol('n')
    >>> If(((n>1), [Assign(n,n-1)]), (True, [Assign(n,n+1)]))
    If(((n>1), [Assign(n,n-1)]), (True, [Assign(n,n+1)]))
    """
    # TODO add step
    def __new__(cls, *args):
        # (Try to) sympify args first
        newargs = []
        for ce in args:
            cond = ce[0]
            if not isinstance(cond, (bool, Relational, Boolean, Is)):
                raise TypeError(
                    "Cond %s is of type %s, but must be a Relational,"
                    " Boolean, Is, or a built-in bool." % (cond, type(cond)))
            newargs.append(ce)

        return Basic.__new__(cls, *newargs)

# TODO: to improve
class Vector(Basic):
    """Represents variable assignment using a vector for code generation.

    lhs : Expr
        Sympy object representing the lhs of the expression. These should be
        singular objects, such as one would use in writing code. Notable types
        include Symbol, MatrixSymbol, MatrixElement, and Indexed. Types that
        subclass these types are also supported.

    starts : int or list of integers

    stops : int or list of integers

    Examples

    >>> from pyccel.ast.core import Vector
    """

    def __new__(cls, lhs, starts, stops):
        # ...
        lhs = sympify(lhs)
        # ...

        # Tuple of things that can be on the lhs of an assignment
        assignable = (Symbol, MatrixSymbol, MatrixElement, Indexed, Idx)
        if not isinstance(lhs, assignable):
            raise TypeError("Cannot assign to lhs of type %s." % type(lhs))

        return Basic.__new__(cls, lhs, starts, stops)

    @property
    def lhs(self):
        return self._args[0]

    @property
    def starts(self):
        return self._args[1]

    @property
    def stops(self):
        return self._args[2]

    @property
    def name(self):
        return str(self.lhs)

    @property
    def dtype(self):
        return NativeDouble()

# TODO: to improve
class Stencil(Basic):
    """Represents variable assignment using a stencil for code generation.

    lhs : Expr
        Sympy object representing the lhs of the expression. These should be
        singular objects, such as one would use in writing code. Notable types
        include Symbol, MatrixSymbol, MatrixElement, and Indexed. Types that
        subclass these types are also supported.

    starts : int or list of integers

    stops : int or list of integers

    pads : int or list of integers

    Examples

    >>> from pyccel.ast.core import Vector
    """

    def __new__(cls, lhs, starts, stops, pads):
        # ...
        lhs = sympify(lhs)
        # ...

        # Tuple of things that can be on the lhs of an assignment
        assignable = (Symbol, MatrixSymbol, MatrixElement, Indexed, Idx)
        if not isinstance(lhs, assignable):
            raise TypeError("Cannot assign to lhs of type %s." % type(lhs))

        return Basic.__new__(cls, lhs, starts, stops, pads)

    @property
    def lhs(self):
        return self._args[0]

    @property
    def starts(self):
        return self._args[1]

    @property
    def stops(self):
        return self._args[2]

    @property
    def pads(self):
        return self._args[3]

    @property
    def name(self):
        return str(self.lhs)

    @property
    def dtype(self):
        return NativeDouble()

class Header(Basic):
    pass

# TODO rename dtypes to arguments
class VariableHeader(Header):
    """Represents a variable header in the code.

    name: str
        variable name

    dtypes: tuple/list
        a list of datatypes. an element of this list can be str/DataType of a
        tuple (str/DataType, attr, allocatable)

    Examples

    """

    # TODO dtypes should be a dictionary (useful in syntax)
    def __new__(cls, name, dtypes):
        if not(iterable(dtypes)):
            raise TypeError("Expecting dtypes to be iterable.")

#        if isinstance(dtypes, str):
#            types.append((datatype(dtypes), []))
#        elif isinstance(dtypes, DataType):
#            types.append((dtypes, []))
#        elif isinstance(dtypes, (tuple, list)):
#            if not(len(dtypes) in [2, 3]):
#                raise ValueError("Expecting exactly 2 or 3 entries.")
#        else:
#            raise TypeError("Wrong element in dtypes.")

        return Basic.__new__(cls, name, dtypes)

    @property
    def name(self):
        return self._args[0]

    @property
    def dtypes(self):
        return self._args[1]

    def create_definition(self):
        """Returns a Variable."""
        raise NotImplementedError('TODO')

# TODO rename dtypes to arguments
class FunctionHeader(Header):
    """Represents function/subroutine header in the code.

    func: str
        function/subroutine name

    dtypes: tuple/list
        a list of datatypes. an element of this list can be str/DataType of a
        tuple (str/DataType, attr, allocatable)

    results: tuple/list
        a list of datatypes. an element of this list can be str/DataType of a
        tuple (str/DataType, attr, allocatable)

    kind: str
        'function' or 'procedure'. default value: 'function'

    Examples

    >>> from pyccel.ast.core import FunctionHeader
    >>> FunctionHeader('f', ['double'])
    FunctionHeader(f, [(NativeDouble(), [])])
    """

    # TODO dtypes should be a dictionary (useful in syntax)
    def __new__(cls, func, dtypes, results=None, kind='function'):
        func = str(func)

        if not(iterable(dtypes)):
            raise TypeError("Expecting dtypes to be iterable.")

        types = []
        for d in dtypes:
            if isinstance(d, str):
                types.append((datatype(d), []))
            elif isinstance(d, DataType):
                types.append((d, []))
            elif isinstance(d, (tuple, list)):
                if not(len(d) in [2, 3]):
                    raise ValueError("Expecting exactly 2 or 3 entries.")
                types.append(d)
            else:
                raise TypeError("Wrong element in dtypes.")

        r_types = []
        if results:
            if not(iterable(results)):
                raise TypeError("Expecting results to be iterable.")

            r_types = []
            for d in results:
                if isinstance(d, str):
                    r_types.append((datatype(d), []))
                elif isinstance(d, DataType):
                    r_types.append((d, []))
                elif isinstance(d, (tuple, list)):
                    if not(len(d) in [2, 3]):
                        raise ValueError("Expecting exactly 2 or 3 entries.")
                    r_types.append(d)
                else:
                    raise TypeError("Wrong element in r_types.")

        if not isinstance(kind, str):
            raise TypeError("Expecting a string for kind.")

        if not (kind in ['function', 'procedure']):
            raise ValueError("kind must be one among {'function', 'procedure'}")

        return Basic.__new__(cls, func, types, r_types, kind)

    @property
    def func(self):
        return self._args[0]

    @property
    def dtypes(self):
        return self._args[1]

    @property
    def results(self):
        return self._args[2]

    @property
    def kind(self):
        return self._args[3]

    def create_definition(self):
        """Returns a FunctionDef with empy body."""
        # TODO factorize what can be factorized

        name = str(self.func)

        body      = []
        cls_name  = None
        hide      = False
        kind      = self.kind
#        kind      = 'procedure'
        imports   = []

        # ... factorize the following 2 blocks
        args = []
        for i,d in enumerate(self.dtypes):
            datatype    = d[0]
            allocatable = d[2]

            rank = 0
            for a in d[1]:
                if isinstance(a, Slice) or a == ':':
                    rank += 1

            shape  = None

            arg_name = 'arg_{0}'.format(str(i))
            arg = Variable(datatype, arg_name,
                           allocatable=allocatable,
                           rank=rank,
                           shape=shape)
            args.append(arg)

        results = []
        for i,d in enumerate(self.results):
            datatype    = d[0]
            allocatable = d[2]

            rank = 0
            for a in d[1]:
                if isinstance(a, Slice) or a == ':':
                    rank += 1

            shape  = None

            result_name = 'result_{0}'.format(str(i))
            result = Variable(datatype, result_name,
                           allocatable=allocatable,
                           rank=rank,
                           shape=shape)
            results.append(result)
        # ...

        return FunctionDef(name, args, results, body,
                           local_vars=[],
                           global_vars=[],
                           cls_name=cls_name,
                           hide=hide,
                           kind=kind,
                           imports=imports)

class MethodHeader(FunctionHeader):
    """Represents method header in the code.

    name: iterable
        method name as a list/tuple

    dtypes: tuple/list
        a list of datatypes. an element of this list can be str/DataType of a
        tuple (str/DataType, attr)

    results: tuple/list
        a list of datatypes. an element of this list can be str/DataType of a
        tuple (str/DataType, attr)

    kind: str
        'function' or 'procedure'. default value: 'function'

    Examples

    >>> from pyccel.ast.core import MethodHeader
    >>> m = MethodHeader(('point', 'rotate'), ['double'])
    >>> m
    MethodHeader((point, rotate), [(NativeDouble(), [])], [])
    >>> m.name
    'point.rotate'
    """

    def __new__(cls, name, dtypes, results=None, kind='function'):
        if not isinstance(name, (list, tuple)):
            raise TypeError("Expecting a list/tuple of strings.")

        if not(iterable(dtypes)):
            raise TypeError("Expecting dtypes to be iterable.")

        types = []
        for d in dtypes:
            if isinstance(d, str):
                types.append((datatype(d), []))
            elif isinstance(d, DataType):
                types.append((d, []))
            elif isinstance(d, (tuple, list)):
                # commented because of 'star' attribut
                # TODO clean this later
#                if not(len(d) == 2):
#                    print '>> d = ', d
#                    raise ValueError("Expecting exactly two entries.")
                types.append(d)
            else:
                raise TypeError("Wrong element in dtypes.")

        r_types = []
        if results:
            if not(iterable(results)):
                raise TypeError("Expecting results to be iterable.")

            r_types = []
            for d in results:
                if isinstance(d, str):
                    r_types.append((datatype(d), []))
                elif isinstance(d, DataType):
                    r_types.append((d, []))
                elif isinstance(d, (tuple, list)):
                    if not(len(d) == 2):
                        raise ValueError("Expecting exactly two entries.")
                    r_types.append(d)
                else:
                    raise TypeError("Wrong element in r_types.")


        if not isinstance(kind, str):
            raise TypeError("Expecting a string for kind.")

        if not (kind in ['function', 'procedure']):
            raise ValueError("kind must be one among {'function', 'procedure'}")

        return Basic.__new__(cls, name, types, r_types, kind)

    @property
    def name(self):
        _name = self._args[0]
        if isinstance(_name, str):
            return _name
        else:
            return '.'.join(str(n) for n in _name)

    @property
    def dtypes(self):
        return self._args[1]

    @property
    def results(self):
        return self._args[2]

    @property
    def kind(self):
        return self._args[3]

class ClassHeader(Header):
    """Represents class header in the code.

    name: str
        class name

    options: str, list, tuple
        a list of options

    Examples

    >>> from pyccel.ast.core import ClassHeader
    >>> ClassHeader('Matrix', ('abstract', 'public'))
    ClassHeader(Matrix, (abstract, public))
    """

    def __new__(cls, name, options):
        if not(iterable(options)):
            raise TypeError("Expecting options to be iterable.")

        return Basic.__new__(cls, name, options)

    @property
    def name(self):
        return self._args[0]

    @property
    def options(self):
        return self._args[1]

numbers = []

def is_simple_assign(expr):
    if not isinstance(expr, Assign):
        return False

    assignable  = [Variable, IndexedVariable, IndexedElement]
    assignable += [sp_Integer, sp_Float]
    assignable = tuple(assignable)
    if isinstance(expr.rhs, assignable):
        return True
    else:
        return False

def is_valid_module(expr):
    _module_stmt = (Comment, FunctionDef, ClassDef, \
                    FunctionHeader, ClassHeader, MethodHeader, Import)

    if isinstance(expr, (tuple, list, Tuple)):
        is_module = True
        for stmt in expr:
            if not is_valid_module(stmt):
                is_module = False
                break
        return is_module
    elif isinstance(expr, _module_stmt):
        return True
    elif isinstance(expr, Assign):
        return is_simple_assign(expr)
    else:
        return False
# ...

# ...
def get_initial_value(expr, var):
    """Returns the first assigned value to var in the Expression expr.

    expr: Expression
        any AST valid expression

    var: str, Variable, DottedName, list, tuple
        variable name
    """
    # ...
    def is_None(expr):
        """Returns True if expr is None or Nil()."""
        return isinstance(expr, Nil) or (expr is None)
    # ...

    # ...
    if isinstance(var, str):
        return get_initial_value(expr, [var])

    elif isinstance(var, DottedName):
        return get_initial_value(expr, [str(var)])

    elif isinstance(var, Variable):
        return get_initial_value(expr, [var.name])

    elif not isinstance(var, (list, tuple)):
        raise TypeError('Expecting var to be str, list, tuple or Variable, '
                        'given {0}'.format(type(var)))
    # ...

    # ...
    if isinstance(expr, ValuedVariable):
        if expr.variable.name in var:
            return expr.value

    elif isinstance(expr, Variable):
        # expr.cls_base if of type ClassDef
        if expr.cls_base:
            return get_initial_value(expr.cls_base, var)

    elif isinstance(expr, Assign):
        if str(expr.lhs) in var:
            return expr.rhs

    elif isinstance(expr, FunctionDef):
        value = get_initial_value(expr.body, var)
        if not is_None(value):
            r = get_initial_value(expr.arguments, value)
            if 'self._linear' in var:
                print('>>>> ', var, value, r)
            if not (r is None):
                return r
        return value

    elif isinstance(expr, FunctionCall):
        return get_initial_value(expr.func, var)

    elif isinstance(expr, ConstructorCall):
        return get_initial_value(expr.func, var)

    elif isinstance(expr, (list, tuple, Tuple)):
        for i in expr:
            value = get_initial_value(i, var)
            # here we make a difference between None and Nil,
            # since the output of our function can be None
            if not (value is None):
                return value

    elif isinstance(expr, ClassDef):
        methods     = expr.methods_as_dict
        init_method = methods['__init__']
        return get_initial_value(init_method, var)
    # ...

    return Nil()
# ...

# ... TODO: improve and make it recursive
def get_iterable_ranges(it, var_name=None):
    """Returns ranges of an iterable object."""
    if isinstance(it, Variable):
        if it.cls_base is None:
            raise TypeError('iterable must be an iterable Variable object')

        # ...
        def _construct_arg_Range(name):
            if not isinstance(name, DottedName):
                raise TypeError('Expecting a DottedName, given '
                                ' {0}'.format(type(name)))

            if not var_name:
                return DottedName(it.name.name[0], name.name[1])
            else:
                return DottedName(var_name, name.name[1])
        # ...

        cls_base = it.cls_base

        if isinstance(cls_base, Range):
            if not isinstance(it.name, DottedName):
                raise TypeError('Expecting a DottedName, given '
                                ' {0}'.format(type(it.name)))

            args = []
            for i in [cls_base.start, cls_base.stop, cls_base.step]:
                if isinstance(i, (Variable, IndexedVariable)):
                    arg_name = _construct_arg_Range(i.name)
                    arg = i.clone(arg_name)
                elif isinstance(i, IndexedElement):
                    arg_name = _construct_arg_Range(i.base.name)
                    base    = i.base.clone(arg_name)
                    indices = i.indices
                    arg = base[indices]
                else:
                    raise TypeError('Wrong type, given {0}'.format(type(i)))
                args += [arg]

            return [Range(*args)]

        elif isinstance(cls_base, Tensor):
            if not isinstance(it.name, DottedName):
                raise TypeError('Expecting a DottedName, given '
                                ' {0}'.format(type(it.name)))
            # ...
            ranges = []
            for r in cls_base.ranges:
                ranges += get_iterable_ranges(r, var_name=str(it.name.name[0]))
            # ...

            return ranges

        params   = [str(i) for i in it.cls_parameters]
    elif isinstance(it, ConstructorCall):
        cls_base = it.this.cls_base

        # arguments[0] is 'self'
        # TODO must be improved in syntax, so that a['value'] is a sympy object
        args   = []
        kwargs = {}
        for a in it.arguments[1:]:
            if isinstance(a, dict):
                # we add '_' tp be conform with the private variables convention
                kwargs['{0}'.format(a['key'])] = a['value']
            else:
                args.append(a)

        # TODO improve
        params = args

#        for k,v in kwargs:
#            params.append(k)

    methods     = cls_base.methods_as_dict
    init_method = methods['__init__']

    args   = init_method.arguments[1:]
    args   = [str(i) for i in args]

    # ...
    it_method = methods['__iter__']
    targets = []
    starts = []
    for stmt in it_method.body:
        if isinstance(stmt, Assign):
            targets.append(stmt.lhs)
            starts.append(stmt.lhs)

    names = []
    for i in starts:
        if isinstance(i, IndexedElement):
            names.append(str(i.base))
        else:
            names.append(str(i))
    names = list(set(names))

    inits = {}
    for stmt in init_method.body:
        if isinstance(stmt, Assign):
            if str(stmt.lhs) in names:
                expr = stmt.rhs
                for a_old, a_new in zip(args, params):
                    dtype = datatype(stmt.rhs)
                    v_old = Variable(dtype, a_old)
                    if isinstance(a_new, (IndexedVariable, IndexedElement,
                                          str, Variable)):
                        v_new = Variable(dtype, a_new)
                    else:
                        v_new = a_new
                    expr = subs(expr, v_old, v_new)
                    inits[str(stmt.lhs)] = expr

    _starts = []
    for i in starts:
        if isinstance(i, IndexedElement):
            _starts.append(i.base)
        else:
            _starts.append(i)
    starts = [inits[str(i)] for i in _starts]

    # ...
    def _find_stopping_criterium(stmts):
        for stmt in stmts:
            if isinstance(stmt, If):
                if not(len(stmt.args) == 2):
                    raise ValueError('Wrong __next__ pattern')

                ct, et = stmt.args[0]
                cf, ef = stmt.args[1]

                for i in et:
                    if isinstance(i, Raise):
                        return cf

                for i in ef:
                    if isinstance(i, Raise):
                        return ct

                raise TypeError('Wrong type for __next__ pattern')

        return None
    # ...

    # ...
    def doit(expr, targets):
        if isinstance(expr, Relational):
            if (str(expr.lhs) in targets) and (expr.rel_op in ['<', '<=']):
                return expr.rhs
            elif (str(expr.rhs) in targets) and (expr.rel_op in ['>', '>=']):
                return expr.lhs
            else:
                return None
        elif isinstance(expr, And):
            return [doit(a, targets) for a in expr.args]
        else:
            raise TypeError('Expecting And logical expression.')
    # ...

    # ...
    next_method = methods['__next__']
    ends = []
    cond = _find_stopping_criterium(next_method.body)
    # TODO treate case of cond with 'and' operation
    # TODO we should avoid using str
    #      must change target from DottedName to Variable
    targets = [str(i) for i in targets]
    ends    = doit(cond, targets)

    # TODO not use str
    if not isinstance(ends, (list, tuple)):
        ends = [ends]

    names = []
    for i in ends:
        if isinstance(i, IndexedElement):
            names.append(str(i.base))
        else:
            names.append(str(i))
    names = list(set(names))

    inits = {}
    for stmt in init_method.body:
        if isinstance(stmt, Assign):
            if str(stmt.lhs) in names:
                expr = stmt.rhs
                for a_old, a_new in zip(args, params):
                    dtype = datatype(stmt.rhs)
                    v_old = Variable(dtype, a_old)
                    if isinstance(a_new, (IndexedVariable, IndexedElement,
                                          str, Variable)):
                        v_new = Variable(dtype, a_new)
                    else:
                        v_new = a_new
                    expr = subs(expr, v_old, v_new)
                    inits[str(stmt.lhs)] = expr

    _ends = []
    for i in ends:
        if isinstance(i, IndexedElement):
            _ends.append(i.base)
        else:
            _ends.append(i)
    ends = [inits[str(i)] for i in _ends]
    # ...

    # ...
    if not(len(ends) == len(starts)):
        raise ValueError('wrong number of starts/ends')
    # ...

    return [Range(s, e, 1) for s,e in zip(starts, ends)]
# ...

def builtin_function(expr, args=None):
    """Returns a builtin-function call applied to given arguments."""
    if not(isinstance(expr, Function) or isinstance(expr, str)):
        raise TypeError('Expecting a string or a Function class')

    if isinstance(expr, Function):
        name = str(type(expr).__name__)

    if isinstance(expr, str):
        name = expr

    if name == 'range':
        return Range(*args)

    return None
