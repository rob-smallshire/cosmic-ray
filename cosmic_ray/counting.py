"""
Facilities for counting how many mutants will be created in a
cross-product of operators and modules.
"""

from .parsing import get_ast
from .plugins import get_operator
from .util import get_col_offset, get_line_number


class _CountingCore:

    """
    An operator core which simply counts how many times an operator finds a
    mutation site in a module.
    """

    def __init__(self):
        self.count = 0
        self.line_number = None
        self.col_offset = None

    def visit_mutation_site(self, node, _, count):
        self.count += count
        self.line_number = get_line_number(node)
        self.col_offset = get_col_offset(node)
        return node

    def repr_args(self):
        return []


def _count(module_ast, op_name):
    """Count mutants for a single module-operator pair."""
    core = _CountingCore()
    op = get_operator(op_name)(core)
    op.visit(module_ast)
    return (core.count, core.line_number, core.col_offset)


def count_mutants(modules, operators):
    """Count how many mutations each operator will peform on each module.

    Args:
        modules: A sequence of module objects
        operators: A sequence of operator plugin names (not operator instances)

    Returns: A sequence of `(module-object, operator-name, count, line-number,
        col-offset)` tuples, giving a per-operator count for each module.
    """
    return filter(
        lambda t: t[2] > 0,
        ((mod, op) + _count(mod_ast, op)
         for (mod, mod_ast)
         in ((m, get_ast(m))
             for m in modules)
         for op in operators))
