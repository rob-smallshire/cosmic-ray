import logging

from spor.cli import find_anchor

from cosmic_ray.worker import WorkerOutcome

LOG = logging.getLogger()


def intercept(work_db):
    for rec in work_db.work_records:
        for anchor in find_anchor(rec.filename):
            metadata = anchor.metadata
            if rec.line_number == anchor.line_number and not metadata.get('mutate', True):
                rec.worker_outcome = WorkerOutcome.SKIPPED
                LOG.info('skipping {}'.format(rec))
                work_db.update_work_record(rec)
