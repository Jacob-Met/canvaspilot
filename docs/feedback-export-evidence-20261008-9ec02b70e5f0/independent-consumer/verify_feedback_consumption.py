"""Independent real-CLI / loopback / offline semantic receiving controls."""
from __future__ import annotations

import argparse
from copy import deepcopy
from itertools import product
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from receiving_support import (ASSIGNMENT_PATH, SUBMISSION_PATH, LocalCanvas,
                               OfflineDocument, authored_feedback, fingerprint,
                               pretty, terminal_json)

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'candidate'
BASELINE = HERE / 'before'
OUTPUT = None


class FeedbackConsumerReceiving(unittest.TestCase):
    def setUp(self):
        self.receipts = OUTPUT / self._testMethodName
        self.receipts.mkdir()
        temporary = tempfile.TemporaryDirectory(prefix='private-', dir=OUTPUT)
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)

    def assert_native_gets(self, record, count=2):
        requests = record['requests']
        self.assertEqual(len(requests), count)
        self.assertEqual([r['method'] for r in requests], ['GET'] * count)
        self.assertEqual([r['path'] for r in requests], [ASSIGNMENT_PATH, SUBMISSION_PATH][:count])
        for request in requests:
            self.assertTrue(request['synthetic_authorization_matches'])
            self.assertEqual(request['query'].get('per_page'), ['50'])
            self.assertNotIn('read_status', request['query'])
        if count == 2:
            self.assertEqual(requests[1]['query'].get('include[]'),
                             ['submission_comments', 'rubric_assessment'])

    def export(self, local, name='feedback.html'):
        target = self.work / name
        record = local.cli(SOURCE, 'export-feedback', out=target)
        self.assertEqual(record['returncode'], 0, record)
        self.assert_native_gets(record)
        result = json.loads(record['stdout'])
        self.assertIs(result['ok'], True)
        self.assertEqual(Path(result['output']), target)
        raw = target.read_bytes()
        self.assertEqual(result['sha256'], fingerprint(raw)['sha256'])
        self.assertEqual((result['course_id'], result['assignment_id']), (77, 314))
        self.assertTrue(result['captured_at'].endswith('Z'))
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        document = OfflineDocument(raw)
        self.assertEqual(len(document.elements('html')), 1)
        self.assertEqual(len(document.elements('body')), 1)
        return document, result, record

    def assert_reader_unchanged(self, local):
        original = local.cli(BASELINE, 'feedback')
        current = local.cli(SOURCE, 'feedback')
        self.assertEqual(original['returncode'], 0, original)
        self.assertEqual(current['returncode'], 0, current)
        self.assert_native_gets(original)
        self.assert_native_gets(current)
        old = json.loads(original['stdout'])
        new = json.loads(current['stdout'])
        self.assertEqual(new, old)
        return new

    def test_zero_prior_attempt_and_existing_reader_remain_truthful(self):
        assignment, submission = authored_feedback()
        with LocalCanvas(assignment, submission, self.receipts / 'case') as local:
            received = self.assert_reader_unchanged(local)
            document, _, _ = self.export(local)
        self.assertEqual(received['submission']['score'], 0)
        self.assertIs(received['submission']['grade_matches_current_submission'], False)
        self.assertEqual(received['submission']['attempt'], 7)
        self.assertEqual(received['submission_comments'], submission['submission_comments'])
        values = document.fields()
        self.assertEqual(values['submission.score'], '0')
        self.assertEqual(values['submission.grade'], '0')
        self.assertEqual(values['assignment.points_possible'], '0')
        self.assertEqual(values['submission.attempt'], '7')
        self.assertEqual(values['submission.excused'], 'false')
        self.assertEqual(values['submission.missing'], 'Not returned')
        self.assertEqual(values['submission.graded_at'], submission['graded_at'])
        self.assertEqual(values['submission.submitted_at'], submission['submitted_at'])
        grading = document.by_id('submission-heading').parent.text()
        self.assertIn('must not be treated as a grade for the current attempt', grading)
        self.assertNotIn('attempt 6', grading.lower())
        self.assertEqual(values['criterion.1.assessment.points'], '0')
        self.assertNotIn('criterion.2.assessment.points', values)
        self.assertIn('No assessment was returned', document.by_id('criterion-2').text())
        self.assertEqual(values['unmatched.1.points'], '2.125')
        self.assertNotIn('47.25', values['submission.grade'])

    def test_missing_empty_and_present_zero_have_separate_consumer_meanings(self):
        documents = {}
        for mode in ['missing', 'empty']:
            with self.subTest(mode=mode):
                assignment, submission = authored_feedback()
                assignment['points_possible'] = None
                submission.update(score=None, grade=None, grade_matches_current_submission=None)
                if mode == 'missing':
                    for key in ['rubric', 'rubric_settings', 'use_rubric_for_grading']:
                        assignment.pop(key, None)
                    submission.pop('rubric_assessment')
                    submission.pop('submission_comments')
                else:
                    assignment.update(rubric=[], rubric_settings={})
                    submission.update(rubric_assessment={}, submission_comments=[])
                with LocalCanvas(assignment, submission, self.receipts / mode) as local:
                    received = self.assert_reader_unchanged(local)
                    document, _, _ = self.export(local, mode + '.html')
                values = document.fields()
                self.assertEqual(values['submission.score'], 'Not returned')
                self.assertEqual(values['submission.grade'], 'Not returned')
                self.assertEqual(values['assignment.points_possible'], 'Not returned')
                self.assertIn('did not establish whether the grade matches', document.text())
                self.assertEqual(received['submission_comments'], None if mode == 'missing' else [])
                self.assertEqual(received['rubric']['settings'], None if mode == 'missing' else {})
                self.assertEqual(values['rubric.assessment_returned'], 'false' if mode == 'missing' else 'true')
                documents[mode] = document.text()
        self.assertIn('Rubric settings were not returned', documents['missing'])
        self.assertIn('Submission comments were not returned; their presence is unknown', documents['missing'])
        self.assertIn('Rubric criteria were not returned; their presence is unknown', documents['missing'])
        self.assertIn('empty rubric settings object', documents['empty'])
        self.assertIn('empty comment list', documents['empty'])
        self.assertIn('empty criterion list', documents['empty'])
        self.assertNotEqual(documents['missing'], documents['empty'])

    def test_all_rubric_flag_combinations_preserve_independent_meanings(self):
        measured = []
        for hide_points, hide_total, hide_outcomes in product([False, True], repeat=3):
            label = ''.join(str(int(x)) for x in [hide_points, hide_total, hide_outcomes])
            with self.subTest(flags=label):
                assignment, submission = authored_feedback()
                assignment['rubric_settings'].update(hide_points=hide_points,
                    hide_score_total=hide_total, hide_outcome_results=hide_outcomes)
                with LocalCanvas(assignment, submission, self.receipts / label) as local:
                    document, _, _ = self.export(local, label + '.html')
                values = document.fields()
                self.assertEqual(values['submission.score'], '0')
                self.assertEqual(values['submission.grade'], '0')
                self.assertEqual(values['assignment.points_possible'], '0')
                self.assertEqual(values['rubric.hide_outcome_results'], str(hide_outcomes).lower())
                self.assertEqual(values['criterion.1.learning_outcome_id'], '610')
                self.assertEqual(values['criterion.1.assessment.comments'],
                                 'Keep the claimed outcome visible.')
                self.assertIn('Outcome evidence Ω', document.text())
                self.assertIn('Spoken response 日本語', document.text())
                point_fields = ['criterion.1.points', 'criterion.1.rating.1.points',
                                'criterion.1.assessment.points', 'unmatched.1.points']
                for key in point_fields:
                    self.assertEqual(key in values, not hide_points, key)
                if not hide_points:
                    self.assertEqual(values['criterion.1.points'], '8.75')
                    self.assertEqual(values['criterion.1.rating.1.points'], '0')
                    self.assertEqual(values['criterion.1.assessment.points'], '0')
                    self.assertEqual(values['unmatched.1.points'], '2.125')
                else:
                    self.assertNotIn('8.75', document.text())
                    self.assertNotIn('2.125', document.text())
                self.assertEqual('rubric.points_possible' in values, not (hide_points or hide_total))
                if 'rubric.points_possible' in values:
                    self.assertEqual(values['rubric.points_possible'], '47.25')
                else:
                    self.assertNotIn('47.25', document.text())
                measured.append({'hide_points': hide_points, 'hide_score_total': hide_total,
                                 'hide_outcome_results': hide_outcomes,
                                 'visible_field_names': sorted(values)})
        (self.receipts / 'flag-consumer-matrix.json').write_bytes(pretty(measured))

    def test_authorship_and_literal_text_survive_without_active_html_or_fetches(self):
        assignment, submission = authored_feedback()
        assignment['name'] += ' </h1><img src="https://should-not-load.invalid/x">'
        assignment['html_url'] = 'javascript:alert(1)'
        assignment['rubric'][0]['description'] += ' <iframe src="https://should-not-load.invalid/f"></iframe>'
        with LocalCanvas(assignment, submission, self.receipts / 'case') as local:
            document, _, _ = self.export(local)
            self.assertEqual(len(local.requests), 2)
        self.assertEqual(document.elements('h1')[0].text(), assignment['name'])
        values = document.fields()
        self.assertEqual(values['comment.1.author_name'], 'Kai <learner> & Ω')
        self.assertEqual(values['comment.1.author_id'], '202')
        self.assertEqual(values['comment.1.author.display_name'], 'Nested supplied name 研')
        self.assertEqual(values['comment.1.author.id'], '203')
        self.assertEqual(values['comment.1.comment'], submission['submission_comments'][0]['comment'])
        self.assertEqual(values['comment.2.author_name'], 'Not returned')
        self.assertEqual(values['comment.2.author.display_name'], 'Only nested author β')
        self.assertEqual(values['comment.2.author.id'], '204')
        self.assertEqual(values['comment.2.comment'], 'Returned empty text')
        self.assertEqual(values['comment.2.media.name'], 'Spoken response 日本語')
        self.assertEqual(values['comment.2.attachment.1.name'], 'voice <literal>.ogg')
        self.assertEqual(values['comment.3.author_name'], 'Not returned')
        self.assertEqual(values['comment.3.author_id'], 'Not returned')
        for index in [1, 2, 3]:
            self.assertNotIn('instructor', document.by_id(f'comment-{index}').text().lower())
        comments = document.by_id('comments-heading').parent
        self.assertEqual([x.attrs.get('id') for x in comments.descendants('article')],
                         ['comment-1', 'comment-2', 'comment-3'])
        for tag in ['script', 'iframe', 'img', 'object', 'embed', 'audio', 'video', 'source', 'link', 'form']:
            self.assertEqual(document.elements(tag), [], tag)
        for element in document.elements():
            self.assertFalse(any(key.lower().startswith('on') for key in element.attrs), element)
            self.assertFalse((element.attrs.get('href') or '').lower().startswith('javascript:'))
            self.assertNotEqual(element.attrs.get('http-equiv', '').lower(), 'refresh')
        self.assertIn('javascript:alert(1)', document.text())
        self.assertIn(submission['submission_comments'][0]['comment'], document.text())

    def test_ambiguous_rubric_ids_remain_separate_in_the_actual_sheet(self):
        assignment, submission = authored_feedback()
        assignment['rubric'] = [{'id': 'ambiguous', 'description': 'FIRST DESCRIPTOR', 'points': 4},
                                {'id': 'ambiguous', 'description': 'SECOND DESCRIPTOR', 'points': 5}]
        submission['rubric_assessment'] = {'ambiguous': {'points': 3.625,
                                                       'comments': 'UNJOINED-ONLY FEEDBACK'}}
        with LocalCanvas(assignment, submission, self.receipts / 'case') as local:
            received = self.assert_reader_unchanged(local)
            document, _, _ = self.export(local)
        self.assertEqual([x['assessment'] for x in received['rubric']['criteria']], [None, None])
        self.assertEqual(received['rubric']['unmatched_assessments'], submission['rubric_assessment'])
        values = document.fields()
        for index in [1, 2]:
            criterion = document.by_id(f'criterion-{index}').text()
            self.assertIn('No assessment was returned', criterion)
            self.assertNotIn('UNJOINED-ONLY', criterion)
            self.assertNotIn(f'criterion.{index}.assessment.points', values)
        self.assertEqual(values['unmatched.1.points'], '3.625')
        self.assertEqual(values['unmatched.1.comments'], 'UNJOINED-ONLY FEEDBACK')
        self.assertEqual(document.text().count('UNJOINED-ONLY FEEDBACK'), 1)

    def test_existing_locators_and_late_creation_win_without_overwrite(self):
        assignment, submission = authored_feedback()
        for kind in ['file', 'directory', 'dangling-symlink', 'fifo']:
            with self.subTest(kind=kind):
                target = self.work / (kind + '.html')
                original = b'INDP-EXISTING\x00\xff\n'
                if kind == 'file':
                    target.write_bytes(original)
                elif kind == 'directory':
                    target.mkdir()
                elif kind == 'dangling-symlink':
                    target.symlink_to(self.work / 'never-created-target')
                else:
                    os.mkfifo(target)
                initial_entries = sorted(p.name for p in self.work.iterdir())
                before = target.lstat()
                with LocalCanvas(assignment, submission, self.receipts / kind) as local:
                    record = local.cli(SOURCE, 'export-feedback', out=target)
                    self.assertEqual(record['returncode'], 1, record)
                    self.assertEqual(record['stdout'], '')
                    self.assertIs(terminal_json(record['stderr'])['ok'], False)
                    self.assertEqual(local.requests, [])
                after = target.lstat()
                self.assertEqual((after.st_dev, after.st_ino, after.st_mode),
                                 (before.st_dev, before.st_ino, before.st_mode))
                if kind == 'file':
                    self.assertEqual(target.read_bytes(), original)
                if kind == 'dangling-symlink':
                    self.assertEqual(target.readlink(), self.work / 'never-created-target')
                    self.assertFalse((self.work / 'never-created-target').exists())
                self.assertEqual(sorted(p.name for p in self.work.iterdir()), initial_entries)
        target = self.work / 'late-file.html'
        winner = b'ANOTHER LOCAL WRITER WINS\n'
        def create_during_response(path):
            if path == SUBMISSION_PATH:
                target.write_bytes(winner)
        initial_entries = {p.name for p in self.work.iterdir()}
        with LocalCanvas(assignment, submission, self.receipts / 'late-file',
                         before_response=create_during_response) as local:
            record = local.cli(SOURCE, 'export-feedback', out=target)
            self.assertEqual(record['returncode'], 1, record)
            self.assertEqual(record['stdout'], '')
            self.assertIs(terminal_json(record['stderr'])['ok'], False)
            self.assert_native_gets(record)
        self.assertEqual(target.read_bytes(), winner)
        self.assertEqual({p.name for p in self.work.iterdir()}, initial_entries | {'late-file.html'})

    def test_reader_validation_and_publication_failures_leave_no_partial_sheet(self):
        assignment, submission = authored_feedback()
        cases = []
        cases.append(('self-forbidden', deepcopy(assignment), deepcopy(submission),
                      {SUBMISSION_PATH: (403, b'{"error":"authored forbidden"}', 'application/json')}, 2))
        cases.append(('assignment-failed', deepcopy(assignment), deepcopy(submission),
                      {ASSIGNMENT_PATH: (503, b'{"error":"authored outage"}', 'application/json')}, 1))
        bad = deepcopy(assignment); bad['rubric'] = [None]
        cases.append(('malformed-criteria', bad, deepcopy(submission), {}, 2))
        bad = deepcopy(assignment); bad['course_id'] = 78
        cases.append(('wrong-course', bad, deepcopy(submission), {}, 2))
        bad = deepcopy(assignment); bad['rubric_settings']['hide_points'] = 'false'
        cases.append(('non-boolean-flag', bad, deepcopy(submission), {}, 2))
        cases.append(('invalid-json', deepcopy(assignment), deepcopy(submission),
                      {SUBMISSION_PATH: (200, b'{not JSON}', 'application/json')}, 2))
        cases.append(('missing-output-parent', deepcopy(assignment), deepcopy(submission), {}, 2))
        for name, a, s, responses, requests in cases:
            with self.subTest(case=name):
                directory = self.work / name
                directory.mkdir()
                target = directory / 'sheet.html'
                if name == 'missing-output-parent':
                    target = directory / 'absent' / 'sheet.html'
                with LocalCanvas(a, s, self.receipts / name, responses=responses) as local:
                    record = local.cli(SOURCE, 'export-feedback', out=target)
                    self.assertEqual(record['returncode'], 1, record)
                    self.assertEqual(record['stdout'], '')
                    failure = terminal_json(record['stderr'])
                    self.assertIs(failure['ok'], False)
                    self.assertTrue(failure['error'])
                    self.assert_native_gets(record, count=requests)
                self.assertFalse(target.exists())
                self.assertEqual(list(directory.iterdir()), [])


def verify_sources():
    all_pins = {}
    for label, root, filename in [('candidate', SOURCE, 'candidate-pins.json'),
                                   ('baseline', BASELINE, 'before-pins.json')]:
        expected = json.loads((HERE / filename).read_text())
        observed = {}
        for record in expected['files']:
            value = fingerprint((root / record['path']).read_bytes())
            if any(value[key] != record[key] for key in value):
                raise ValueError(label + ' source drift: ' + record['path'])
            observed[record['path']] = value
        all_pins[label] = observed
    return all_pins


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    OUTPUT = args.output.resolve()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    before = verify_sources()
    (OUTPUT / 'source-before.json').write_bytes(pretty(before))
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FeedbackConsumerReceiving))
    after = verify_sources()
    (OUTPUT / 'source-after.json').write_bytes(pretty(after))
    summary = {'schema': 'independent-feedback-consumer.v1',
               'parent': '55fe1e0a3c4ad85e1065f295e49d44722c3be32b',
               'mode': 'optimized' if sys.flags.optimize else 'normal',
               'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
               'skips': len(result.skipped), 'source_before_after_identical': before == after,
               'runtime_source_files': sum(len(x) for x in before.values()),
               'browser_allocations': 0, 'live_accounts': 0, 'github_writes': 0,
               'probe': fingerprint(Path(__file__).read_bytes()),
               'support': fingerprint((HERE / 'receiving_support.py').read_bytes())}
    (OUTPUT / 'review.json').write_bytes(pretty(summary))
    sys.exit(0 if result.wasSuccessful() and before == after else 1)
