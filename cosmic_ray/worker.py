"""This is the body of the low-level worker tool.

A worker is intended to run as a process that imports a module, mutates it in
one location with one operator, runs the tests, reports the results, and dies.
"""

import difflib
import logging
import sys
import traceback

from .importing import using_mutant
from .testing.test_runner import TestOutcome
from .work_record import WorkRecord

LOG = logging.getLogger()


class WorkerOutcome:
    """Possible outcomes for a worker.
    """
    NORMAL = 'normal'
    EXCEPTION = 'exception'
    NO_TEST = 'no-test'
    TIMEOUT = 'timeout'


def worker(module_name,
           operator_class,
           occurrence,
           test_runner):
    """Mutate the OCCURRENCE-th site for OPERATOR_CLASS in MODULE_NAME, run the
    tests, and report the results.

    This is fundamentally the single-mutation-and-test-run process
    implementation.

    There are three high-level ways that a worker can finish. First, it could
    fail exceptionally, meaning that some uncaught exception made its way from
    some part of the operation to terminate the function. This function will
    intercept all exceptions and return it in a non-exceptional structure.

    Second, the mutation testing machinery may determine that there is no
    OCCURENCE-th instance for OPERATOR_NAME in the module under test. In this
    case there is no way to report a test result (i.e. killed, survived, or
    incompetent) so a special value is returned indicating that no mutation is
    possible.

    Finally, and hopefully normally, the worker will find that it can run a
    test. It will do so and report back the result - killed, survived, or
    incompetent - in a structured way.

    Returns: a WorkRecord

    Raises: This will generally not raise any exceptions. Rather, exceptions
        will be reported using the 'exception' result-type in the return value.

    """
    try:
        #  TODO: Is it necessary to use preserve_modules() here? Or should it
        #  be done at a higher level?
        with using_mutant(module_name, operator_class, occurrence) as context:
            work_record = test_runner()
            if not context.activation_record:
                return WorkRecord(
                    worker_outcome=WorkerOutcome.NO_TEST)

            work_record.update({
                'diff': generate_diff(context),
                'worker_outcome': WorkerOutcome.NORMAL
            })

            work_record.update(context.activation_record)
            return work_record

    except Exception:  # noqa
        return WorkRecord(
            data=traceback.format_exception(*sys.exc_info()),
            test_outcome=TestOutcome.INCOMPETENT,
            worker_outcome=WorkerOutcome.EXCEPTION)


def generate_diff(context):
    module_diff = ["--- mutation diff ---"]
    for line in difflib.unified_diff(
            context.module_source.split('\n'),
            context.modified_source.split('\n'),
            fromfile="a" + context.module_source_file,
            tofile="b" + context.module_source_file,
            lineterm=""):
        module_diff.append(line)
    return module_diff
