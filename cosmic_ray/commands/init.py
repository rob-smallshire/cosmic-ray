import logging
import uuid

from spor.cli import find_metadata

import cosmic_ray.modules
from cosmic_ray.work_record import WorkRecord

LOG = logging.getLogger()


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
    counts = cosmic_ray.counting.count_mutants(modules, operators)
    work_db.set_work_parameters(
        test_runner=test_runner,
        test_args=test_args,
        timeout=timeout)

    work_db.clear_work_records()

    work_db.add_work_records(
        WorkRecord(
            job_id=uuid.uuid4().hex,
            module=module.__name__,
            operator=opname,
            occurrence=occurrence,
            filename=module.__file__,
            line_number=line_number,
            col_offset=col_offset)
        for module, opname, count, line_number, col_offset in counts
        for occurrence in range(count))

    # for rec in work_db.work_records:
    #     for md in find_metadata(rec.filename):
    #         if rec.line_number == md.line_number:
    #             print(md, md.metadata)
