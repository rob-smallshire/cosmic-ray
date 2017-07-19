import logging

from spor.cli import find_metadata

from cosmic_ray.worker import WorkerOutcome

LOG = logging.getLogger()


def intercept(work_db):
    for rec in work_db.work_records:
        for md in find_metadata(rec.filename):
            args = md.metadata
            if rec.line_number == md.line_number and not args.get('mutate', True):
                rec.worker_outcome = WorkerOutcome.SKIPPED
                LOG.info('skipping {}'.format(rec))
                work_db.update_work_record(rec)
