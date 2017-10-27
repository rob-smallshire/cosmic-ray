"""Functionality related to Python's import mechanisms."""

import astunparse
import contextlib
import importlib
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec
import importlib.util
import inspect
import sys

from .mutating import MutatingCore
from .parsing import get_ast


class Context:
    def __init__(self, module_name, operator_class, occurrence):
        spec = importlib.util.find_spec(module_name)

        self.module_name = module_name
        self.operator_class = operator_class
        self.occurrence = occurrence
        self.core = MutatingCore(self.occurrence)
        self.module_source_file = spec.origin # TODO: This is totally sketchy!!! Need to understand it better. Is it always set? I would imagine not.
        self.module_source = None
        self.modified_source = None
        self.modified_ast = None

    def generate_ast(self):
        self.module_source, module_ast = get_ast(self.module_source_file)

        self.core = MutatingCore(self.occurrence)
        operator = self.operator_class(self.core)
        # note: after this step module_ast and modified_ast
        # appear to be the same
        self.modified_ast = operator.visit(module_ast)
        self.modified_source = astunparse.unparse(self.modified_ast)

    @property
    def activation_record(self):
        return self.core.activation_record


class ASTLoader:  # pylint:disable=old-style-class,too-few-public-methods

    """
    An `importlib.abc.Loader` which loads an AST for a particular name.

    You construct this with an AST and a module name. The
    `exec_module` method simply compiles the AST with the name and
    execs the resulting code against the provided module dict.

    In practice, this is how cosmic-ray loads mutated ASTs for modules.
    """

    def __init__(self, context):
        self.context = context

    def create_module(self, spec):
        return None

    def exec_module(self, mod):
        with preserve_modules():
            self.context.generate_ast()
            exec(compile(self.context.modified_ast, self.context.module_name, 'exec'),  # pylint:disable=exec-used
                 mod.__dict__)


class ASTFinder(MetaPathFinder):  # pylint:disable=too-few-public-methods

    """
    An `importlib.ast.MetaPathFinder` that associates a module name
    with an AST.

    Construct this by passing a module name and associated AST. When
    the finder is asked for that name, it will return a loader that
    produces the code equivalent of the AST.

    We use this to inject mutated ASTs into tests.
    """

    def __init__(self, loader):
        self._loader = loader

    def find_spec(self, fullname, path, target=None):  # pylint:disable=unused-argument
        if fullname == self._loader.context.module_name:
            return ModuleSpec(fullname, self._loader)
        else:
            return None


@contextlib.contextmanager
def preserve_modules():
    """Remember the state of sys.modules on enter and reset it on exit.
    """
    original_mods = dict(sys.modules)
    try:
        yield
    finally:
        del_mods = {m for m in sys.modules if m not in original_mods}
        for m in del_mods:
            del sys.modules[m]


@contextlib.contextmanager
def using_mutant(module_name, operator_class, occurrence):
    """Create a new Finder as a context-manager.

    This creates a new Finder which loads the AST `module_ast` when
    `module_name` is requested. It installs this finder at the head of
    `sys.meta_path` for the duration of the with-block, yielding the Finder in
    the with-statement. After the with-block, the Finder is uninstalled.

    Note that this does *not* attempt to adjust `sys.modules` in any way. You
    should make sure to clear out any existing references to `module_name`
    before running this (e.g. with `preserve_modules()` or something similar).

    """
    context = Context(module_name, operator_class, occurrence)
    loader = ASTLoader(context)
    finder = ASTFinder(loader)
    sys.meta_path = [finder] + sys.meta_path
    try:
        yield context
    finally:
        sys.meta_path.remove(finder)
