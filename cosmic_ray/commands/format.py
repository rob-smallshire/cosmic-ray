"Implementation of various formatting commands."

import json
import sys
import xml.etree.ElementTree

import docopt
from yattag import Doc

from cosmic_ray.reporting import create_report, is_killed, survival_rate
from cosmic_ray.testing.test_runner import TestOutcome
from cosmic_ray.work_item import WorkItem, WorkItemJsonDecoder
from cosmic_ray.worker import WorkerOutcome


def format_survival_rate():
    """cr-rate

Usage: cr-rate

Read JSON work-records from stdin and print the survival rate.
"""
    records = (WorkItem(json.loads(line, cls=WorkItemJsonDecoder)) for line in sys.stdin)
    print('{:.2f}'.format(survival_rate(records)))


def report():
    """cr-report

Usage: cr-report [--full-report] [--show-pending]

Print a nicely formatted report of test results and some basic statistics.

options:
    --full-report   Show test output and mutation diff for killed mutants
    --show-pending  Display results for incomplete tasks
"""

    arguments = docopt.docopt(report.__doc__, version='cr-format 0.1')
    full_report = arguments['--full-report']
    show_pending = arguments['--show-pending']
    records = (WorkItem(json.loads(line, cls=WorkItemJsonDecoder)) for line in sys.stdin)
    for line in create_report(records, show_pending, full_report):
        print(line)


def _create_element_from_item(work_item):
    data = work_item.data
    sub_elem = xml.etree.ElementTree.Element('testcase')

    sub_elem.set('classname', work_item.job_id)
    sub_elem.set('line', str(work_item.line_number))
    sub_elem.set('file', work_item.module)
    if work_item.command_line:
        sub_elem.set('name', str(work_item.command_line))

    outcome = work_item.worker_outcome

    if outcome == WorkerOutcome.TIMEOUT:
        error_elem = xml.etree.ElementTree.SubElement(sub_elem, 'error')
        error_elem.set('message', "Timeout: {:.3f} sec".format(data))
    elif outcome == WorkerOutcome.EXCEPTION:
        error_elem = xml.etree.ElementTree.SubElement(sub_elem, 'error')
        error_elem.set('message', "Worker has encountered exception")
        error_elem.text = str(data) + "\n".join(work_item.diff)
    elif _evaluation_success(outcome, work_item):
        failure_elem = xml.etree.ElementTree.SubElement(sub_elem, 'failure')
        failure_elem.set('message', "Mutant has survived your unit tests")
        failure_elem.text = str(data) + "\n".join(work_item.diff)

    return sub_elem


def _evaluation_success(outcome, work_item):
    return outcome == WorkerOutcome.NORMAL and \
           work_item.test_outcome in [TestOutcome.SURVIVED,
                                      TestOutcome.INCOMPETENT]


def _create_xml_report(records):
    total_jobs = 0
    errors = 0
    failed = 0
    root_elem = xml.etree.ElementTree.Element('testsuite')
    for item in records:
        total_jobs += 1
        if item.worker_outcome is None:
            errors += 1
        if is_killed(item):
            failed += 1
        if item.worker_outcome is not None:
            subelement = _create_element_from_item(item)
            root_elem.append(subelement)

    root_elem.set('errors', str(errors))
    root_elem.set('failures', str(failed))
    root_elem.set('skips', str(0))
    root_elem.set('tests', str(total_jobs))
    return xml.etree.ElementTree.ElementTree(root_elem)


def report_xml():
    """cr-xml

Usage: cr-xml

Print an XML formatted report of test results for continuos integration systems
"""
    records = (WorkItem(json.loads(line, cls=WorkItemJsonDecoder)) for line in sys.stdin)
    xml_elem = _create_xml_report(records)
    xml_elem.write(sys.stdout.buffer, encoding='utf-8', xml_declaration=True)


def report_html():
    doc, tag, text = Doc().tagtext()

    with tag('html'):
        with tag('body', id = 'hello'):
            with tag('h1'):
                text('Cosmic Ray Report')

            work_items = (WorkItem(json.loads(line, cls=WorkItemJsonDecoder)) for line in sys.stdin)
            with tag('table'):
                for work_item in work_items:
                    with tag('tr'):
                        with tag('td'):
                            text(str(work_item.job_id))
                        with tag('td'):
                            text(str(work_item.worker_outcome))

    print(doc.getvalue())
