import ast
import sys
from .operator import Operator


class ReplaceTrueFalse(Operator):
    """An operator that modifies True/False constants."""
    def visit_NameConstant(self, node):  # noqa
        """
            New in version 3.4: Previously, these constants were instances of ``Name``.
            http://greentreesnakes.readthedocs.io/en/latest/nodes.html#NameConstant
        """
        if node.value in [True, False]:
            return self.visit_mutation_site(node)
        else:
            return node

    def visit_Name(self, node):  # noqa
        """For backward compatibility with Python 3.3."""
        if node.id in ['True', 'False']:
            return self.visit_mutation_site(node)
        else:
            return node

    def mutate(self, node, _):
        """Modify the boolean value on `node`."""
        if sys.version_info >= (3, 4):
            return ast.NameConstant(value=not node.value)
        else:
            return ast.Name(id=not ast.literal_eval(node.id), ctx=node.ctx)


class ReplaceAndWithOr(Operator):
    """An operator that swaps 'and' with 'or'."""
    def visit_BoolOp(self, node):  # noqa
        """
            http://greentreesnakes.readthedocs.io/en/latest/nodes.html#BoolOp
        """
        if isinstance(node.op, ast.And):
            return self.visit_mutation_site(node, len(node.values))
        else:
            return node

    def mutate(self, node, idx):
        """Replace AND with OR."""
        # replace all occurences of And()
        # A and B and C -> A or B or C
        node.op = ast.Or()

        # or replace an operator somewhere in the middle
        # of the expression
        if idx and len(node.values) > 2:
            left = node.values[:idx]
            if len(left) > 1:
                left = [ast.BoolOp(op=ast.And(), values=left)]

            right = node.values[idx:]
            if len(right) > 1:
                right = [ast.BoolOp(op=ast.And(), values=right)]

            node.values = []
            node.values.extend(left)
            node.values.extend(right)

        # add lineno and col_offset
        ast.fix_missing_locations(node)
        return node


class ReplaceOrWithAnd(Operator):
    """An operator that swaps 'or' with 'and'."""
    def visit_Or(self, node):  # noqa
        """
            http://greentreesnakes.readthedocs.io/en/latest/nodes.html#Or
        """
        return self.visit_mutation_site(node)

    def mutate(self, node, _):
        """Replace OR with AND."""
        return ast.And()


class RemoveNot(Operator):

    """An operator that removes the 'not' keyword from expressions."""

    def visit_UnaryOp(self, node):  # noqa
        """
        http://greentreesnakes.readthedocs.io/en/latest/nodes.html#UnaryOp
        """
        if isinstance(node.op, ast.Not):
            return self.visit_mutation_site(node)
        else:
            return node

    def mutate(self, node, _):
        """Remove the 'not' keyword."""
        # UnaryOp.operand is any expression node so just
        # return the expression without the 'not' keyword
        return node.operand


class AddNot(Operator):

    """An operator that adds the 'not' keyword to expressions."""

    def visit_If(self, node):  # noqa
        return self.visit_mutation_site(node)

    def visit_IfExp(self, node):  # noqa
        return self.visit_mutation_site(node)

    def visit_Assert(self, node):  # noqa
        return self.visit_mutation_site(node)

    def visit_While(self, node):  # noqa
        return self.visit_mutation_site(node)

    def mutate(self, node, _):
        """
        Add the 'not' keyword.

        Note: this will negate the entire if condition.
        """
        if hasattr(node, 'test'):
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
            # add lineno & col_offset to the nodes we created
            ast.fix_missing_locations(node)
            return node
