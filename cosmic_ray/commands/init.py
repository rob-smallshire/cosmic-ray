import logging
import uuid

from spor.cli import find_metadata

import cosmic_ray.modules
from cosmic_ray.parsing import get_ast
from cosmic_ray.plugins import get_operator
from cosmic_ray.worker import WorkerOutcome
from cosmic_ray.work_record import WorkRecord
from cosmic_ray.util import get_col_offset, get_line_number

LOG = logging.getLogger()


class WorkDBInitCore:
    def __init__(self, module, opname, work_db):
        self.module = module
        self.opname = opname
        self.work_db = work_db
        self.occurrence = 0

    def visit_mutation_site(self, node, _, count):
        self.work_db.add_work_records(
            WorkRecord(
                job_id=uuid.uuid4().hex,
                module=self.module.__name__,
                operator=self.opname,
                occurrence=self.occurrence + c,
                filename=self.module.__file__,
                line_number=get_line_number(node),
                col_offset=get_col_offset(node))
            for c in range(count))

        self.occurrence += count

        return node


def init(modules,
         work_db,
         test_runner,
         test_args,
         timeout):
    """Clear and initialize a work-db with work items.

    Any existing data in the work-db will be cleared and replaced with entirely
    new work orders. In particular, this means that any results in the db are
    removed.

    """
    operators = cosmic_ray.plugins.operator_names()
    work_db.set_work_parameters(
        test_runner=test_runner,
        test_args=test_args,
        timeout=timeout)

    work_db.clear_work_records()

    for mod in modules:
        mod_ast = get_ast(mod)
        for op_name in operators:
            core = WorkDBInitCore(mod, op_name, work_db)
            op = get_operator(op_name)(core)
            op.visit(mod_ast)

    intercept(work_db)


def intercept(work_db):
    for rec in work_db.work_records:
        for md in find_metadata(rec.filename):
            if rec.line_number == md.line_number:
                rec.worker_outcome = WorkerOutcome.SKIPPED
                LOG.info('skipping {}'.format(rec))
                work_db.update_work_record(rec)
