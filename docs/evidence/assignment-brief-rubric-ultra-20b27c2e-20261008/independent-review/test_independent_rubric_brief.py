"""Independent receiving checks through native API, CLI and registered MCP.

No production projection or tool function is replaced. Only real CanvasClient's
existing fixture transport is injected at each public receiving boundary.
"""
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import argparse, asyncio, hashlib, importlib.metadata, io, json, math, sys, unittest

HERE = Path(__file__).resolve().parent
FIXTURE = json.loads((HERE / 'assignment-fixture.json').read_text())
ROUTE = '/api/v1/courses/74/assignments/701'
SURFACES = ('api', 'cli', 'registered-mcp')
OUTPUTS = []

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))

def digest(data):
    return hashlib.sha256(data).hexdigest()

def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()

def fixture_api(payload):
    client = client_module.CanvasClient(base_url='https://canvas.example.test', token='',
        profile=HERE / 'unused-profile', fixture={'routes': {'GET ' + ROUTE: payload}})
    return api_module.CanvasAPI(client)

def mcp_payload(result):
    if getattr(result, 'is_error', getattr(result, 'isError', False)):
        raise AssertionError('registered MCP returned an error: ' + str(result))
    if len(result.content) != 1 or result.content[0].type != 'text':
        raise AssertionError('registered MCP text envelope changed')
    return json.loads(result.content[0].text)

class TestIndependentBrief(unittest.TestCase):
    def core(self, result, payload, course='74', assignment='701'):
        expected = {'title': payload['name'], 'due_at': payload['due_at'],
            'points_possible': payload['points_possible'],
            'submission_types': payload['submission_types'],
            'prompt': 'Read <lab> & compare α β. Source link',
            'html_url': payload['html_url'], 'course_id': course, 'assignment_id': assignment}
        self.assertEqual(canonical({k: result[k] for k in expected}), canonical(expected))

    def invoke(self, payload, surface):
        supplied = deepcopy(payload)
        before = canonical(supplied)
        api = fixture_api(supplied)
        native_request = api.client.request
        calls = []
        def record(method, path, **kwargs):
            calls.append([method, path, kwargs])
            return native_request(method, path, **kwargs)
        api.client.request = record
        try:
            with ExitStack() as stack:
                stack.enter_context(patch.object(client_module, 'broker_health', side_effect=AssertionError('unexpected broker')))
                stack.enter_context(patch.object(client_module.httpx, 'Client', side_effect=AssertionError('unexpected HTTP client')))
                if surface == 'api':
                    result = api.assignment_brief('74', '701')
                elif surface == 'cli':
                    stack.enter_context(patch.object(client_module, 'CanvasClient', return_value=api.client))
                    out = io.StringIO()
                    with redirect_stdout(out):
                        cli_module.main(['brief', '74', '701', '--base-url', 'https://canvas.example.test', '--token', ''])
                    result = json.loads(out.getvalue())
                else:
                    stack.enter_context(patch.object(mcp_module, '_api', api))
                    result = mcp_payload(asyncio.run(mcp_module.mcp.call_tool('canvas_assignment_brief',
                        {'course_id': '74', 'assignment_id': '701'})))
            self.assertEqual(calls, [['GET', ROUTE, {'params': {'include[]': ['submission']}}]])
            self.assertEqual(canonical(supplied), before, 'public receiving mutated supplied Canvas data')
            self.core(result, supplied)
            OUTPUTS.append({'test': self.id(), 'surface': surface,
                'input_sha256': digest(before.encode()), 'request': calls, 'output': result})
            return result
        finally:
            api.close()

    def check(self, payload, rubric, *, settings='supplied', grading='supplied', warnings=()):
        for surface in SURFACES:
            with self.subTest(surface=surface):
                result = self.invoke(payload, surface)
                for name in ('rubric', 'rubric_settings', 'use_rubric_for_grading', 'rubric_warnings'):
                    self.assertIn(name, result)
                self.assertEqual(canonical(result['rubric']), canonical(rubric))
                self.assertEqual(canonical(result['rubric_settings']), canonical(payload.get('rubric_settings') if settings == 'supplied' else settings))
                self.assertEqual(canonical(result['use_rubric_for_grading']), canonical(payload.get('use_rubric_for_grading') if grading == 'supplied' else grading))
                self.assertIsInstance(result['rubric_warnings'], list)
                self.assertTrue(all(isinstance(w, str) for w in result['rubric_warnings']))
                if not warnings:
                    self.assertEqual(result['rubric_warnings'], [])
                for path in warnings:
                    self.assertTrue(any(w.startswith(path + ':') for w in result['rubric_warnings']),
                                    'missing path-specific warning: ' + path)
                json.dumps(result, allow_nan=False)

    def test_original_brief_fields_links_body_and_request(self):
        for surface in SURFACES:
            with self.subTest(surface=surface):
                self.invoke(FIXTURE, surface)

    def test_original_get_assignment_fields(self):
        api = fixture_api(deepcopy(FIXTURE))
        try:
            result = api.get_assignment('74', '701')
            expected = {'id': 701, 'course_id': '74', 'name': FIXTURE['name'],
                'due_at': FIXTURE['due_at'], 'points_possible': 100,
                'submission_types': FIXTURE['submission_types'], 'html_url': FIXTURE['html_url'],
                'description_html': FIXTURE['description'],
                'description_text': 'Read <lab> & compare α β. Source link',
                'rubric': FIXTURE['rubric'], 'submission': FIXTURE['submission']}
            self.assertEqual(canonical({k: result[k] for k in expected}), canonical(expected))
        finally:
            api.close()

    def test_native_api_preserves_integer_requested_ids(self):
        api = fixture_api(deepcopy(FIXTURE))
        try:
            self.core(api.assignment_brief(74, 701), FIXTURE, course=74, assignment=701)
        finally:
            api.close()

    def test_ordered_ratings_fractional_zero_points_and_literal_text(self):
        self.check(FIXTURE, FIXTURE['rubric'])

    def test_outcome_range_and_nonscoring_fields(self):
        payload = deepcopy(FIXTURE)
        criterion = {'id': 0, 'description': 'Advisory outcome', 'points': 0,
            'criterion_use_range': True, 'ignore_for_scoring': True,
            'outcome_id': 781, 'learning_outcome_id': 0, 'vendor_guid': 'outcome:β',
            'ratings': [{'id': 0, 'points': 0, 'description': 'Observed'}]}
        payload['rubric'] = [criterion]
        self.check(payload, [criterion])

    def test_advisory_grading_and_display_flags_are_independent(self):
        for grading, hide_total, hide_points in [(False, True, False), (True, False, True)]:
            with self.subTest(grading=grading):
                payload = deepcopy(FIXTURE)
                payload['use_rubric_for_grading'] = grading
                payload['rubric_settings'].update(points_possible='12.5',
                    hide_score_total=hide_total, hide_points=hide_points,
                    free_form_criterion_comments=True)
                self.check(payload, payload['rubric'])

    def test_absent_null_and_empty_rubrics_remain_distinct(self):
        for kind in ('absent', 'null', 'empty'):
            with self.subTest(kind=kind):
                payload = deepcopy(FIXTURE)
                for key in ('rubric', 'rubric_settings', 'use_rubric_for_grading'):
                    payload.pop(key)
                if kind != 'absent':
                    payload.update(rubric=[] if kind == 'empty' else None,
                                   rubric_settings=None, use_rubric_for_grading=None)
                self.check(payload, [] if kind == 'empty' else None)

    def test_nullable_and_sparse_criteria_do_not_invent_fields(self):
        payload = deepcopy(FIXTURE)
        payload['rubric'] = [{'id': 'nullable', 'description': None,
            'long_description': None, 'ratings': None}, {'description': 'Only guidance'},
            {'ratings': [{'description': 'Named only'}, {'points': 0}]}]
        self.check(payload, payload['rubric'])

    def test_malformed_rubric_containers_preserve_the_brief(self):
        for value in ('bad', {'description': 'not a criterion list'}, False, 7):
            with self.subTest(value=value):
                payload = deepcopy(FIXTURE)
                payload['rubric'] = value
                self.check(payload, None, warnings=('rubric',))

    def test_bad_criterion_rows_and_fields_preserve_healthy_neighbors(self):
        payload = deepcopy(FIXTURE)
        first, last = deepcopy(payload['rubric'])
        payload['rubric'] = [first, None, {'id': 'keep', 'description': 17,
            'long_description': [], 'points': False, 'criterion_use_range': 'false',
            'ignore_for_scoring': 1}, last]
        self.check(payload, [first, {'id': 'keep'}, last], warnings=('rubric[1]',
            'rubric[2].description', 'rubric[2].long_description', 'rubric[2].points',
            'rubric[2].criterion_use_range', 'rubric[2].ignore_for_scoring'))

    def test_bad_rating_rows_and_fields_preserve_healthy_levels(self):
        payload = deepcopy(FIXTURE)
        first, last = deepcopy(payload['rubric'][0]['ratings'][::2])
        payload['rubric'][0]['ratings'] = [first, None, {'id': True, 'description': 8,
            'long_description': [], 'points': True}, {'description': 'Keep zero', 'points': 0}, last]
        expected = deepcopy(payload['rubric'])
        expected[0]['ratings'] = [first, {'description': 'Keep zero', 'points': 0}, last]
        self.check(payload, expected, warnings=('rubric[0].ratings[1]',
            'rubric[0].ratings[2].id', 'rubric[0].ratings[2].description',
            'rubric[0].ratings[2].long_description', 'rubric[0].ratings[2].points'))

    def test_bad_rating_containers_remain_unavailable(self):
        for value in ('bad', {}, False, 7):
            with self.subTest(value=value):
                payload = deepcopy(FIXTURE)
                payload['rubric'][0]['ratings'] = value
                expected = deepcopy(payload['rubric'])
                expected[0]['ratings'] = None
                self.check(payload, expected, warnings=('rubric[0].ratings',))

    def test_settings_container_validation_and_whole_object_custody(self):
        for value in ('bad', [], False, 0):
            with self.subTest(value=value):
                payload = deepcopy(FIXTURE)
                payload['rubric_settings'] = value
                self.check(payload, payload['rubric'], settings=None, warnings=('rubric_settings',))
        payload = deepcopy(FIXTURE)
        payload['rubric_settings']['vendor_metadata'] = {'optional': None, 'levels': [0, 'β']}
        self.check(payload, payload['rubric'])

    def test_grading_flag_rejects_coercion(self):
        for value in ('false', 'true', 0, 1, {}, []):
            with self.subTest(value=value):
                payload = deepcopy(FIXTURE)
                payload['use_rubric_for_grading'] = value
                self.check(payload, payload['rubric'], grading=None, warnings=('use_rubric_for_grading',))

    def test_invalid_points_are_local_and_output_is_strict_json(self):
        for value in (False, '2.5', float('nan'), float('inf'), float('-inf')):
            with self.subTest(value=repr(value)):
                payload = deepcopy(FIXTURE)
                payload['rubric'][0]['points'] = value
                payload['rubric'][0]['ratings'][0]['points'] = value
                expected = deepcopy(payload['rubric'])
                del expected[0]['points']
                del expected[0]['ratings'][0]['points']
                self.check(payload, expected, warnings=('rubric[0].points', 'rubric[0].ratings[0].points'))

    def test_projection_and_settings_do_not_alias_supplied_data(self):
        payload = deepcopy(FIXTURE)
        payload['rubric_settings']['vendor_metadata'] = {'levels': ['original']}
        before = canonical(payload)
        api = fixture_api(payload)
        try:
            first = api.assignment_brief('74', '701')
            self.assertIn('rubric', first)
            first['rubric'][0]['ratings'][0]['points'] = 9000
            first['rubric_settings']['vendor_metadata']['levels'][0] = 'mutated'
            second = api.assignment_brief('74', '701')
            self.assertEqual(canonical(payload), before)
            self.assertEqual(canonical(second['rubric']), canonical(FIXTURE['rubric']))
            self.assertEqual(second['rubric_settings']['vendor_metadata']['levels'], ['original'])
        finally:
            api.close()

    def test_registered_mcp_rereads_current_assignment(self):
        payload = deepcopy(FIXTURE)
        api = fixture_api(payload)
        try:
            with patch.object(mcp_module, '_api', api):
                first = mcp_payload(asyncio.run(mcp_module.mcp.call_tool('canvas_assignment_brief', {'course_id': '74', 'assignment_id': '701'})))
                payload['rubric'] = [{'description': 'New advisory guidance', 'points': 0}]
                payload['use_rubric_for_grading'] = False
                second = mcp_payload(asyncio.run(mcp_module.mcp.call_tool('canvas_assignment_brief', {'course_id': '74', 'assignment_id': '701'})))
            self.assertIn('rubric', first)
            self.assertEqual(canonical(first['rubric']), canonical(FIXTURE['rubric']))
            self.assertEqual(canonical(second['rubric']), canonical(payload['rubric']))
            self.assertIs(second['use_rubric_for_grading'], False)
            self.core(second, payload)
        finally:
            api.close()

    def test_public_help_and_registered_tool_description_expose_rubric(self):
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as stopped:
            cli_module.main(['--help'])
        self.assertEqual(stopped.exception.code, 0)
        self.assertIn('rubric', out.getvalue().lower())
        tool = next(t for t in asyncio.run(mcp_module.mcp.list_tools()) if t.name == 'canvas_assignment_brief')
        self.assertIn('rubric', tool.description.lower())

    def test_unknown_criterion_fields_are_not_invented_as_contract(self):
        payload = deepcopy(FIXTURE)
        payload['rubric'][0]['vendor_untyped_future_field'] = {'unknown': True}
        payload['rubric'][0]['ratings'][0]['criterion_use_range'] = True
        self.check(payload, FIXTURE['rubric'])

    def test_no_usable_criteria_is_diagnosed_empty_not_missing(self):
        payload = deepcopy(FIXTURE)
        payload['rubric'] = [None, {}, {'unknown_only': 'opaque'}]
        self.check(payload, [], warnings=('rubric[0]', 'rubric[1]', 'rubric[2]'))

def source_map(root):
    return {str(p.relative_to(root)): {'sha256': digest(p.read_bytes()), 'git_blob': blob(p.read_bytes())}
            for p in sorted((root / 'src').rglob('*.py')) if '__pycache__' not in p.parts}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    output.mkdir(exist_ok=False)
    before = source_map(source)
    sys.path.insert(0, str(source / 'src'))
    global api_module, client_module, cli_module, mcp_module
    from canvaspilot import api as api_module, client as client_module, cli as cli_module, mcp_server as mcp_module
    if Path(api_module.__file__).resolve() != source / 'src/canvaspilot/api.py':
        raise RuntimeError('wrong imported source')
    log = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestIndependentBrief)
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    after = source_map(source)
    failed_methods = {getattr(t, 'test_case', t).id() for t, _ in result.failures + result.errors}
    receipt = {'schema': 'independent-canvas-public-brief-v1', 'source_root': str(source),
        'python': sys.version, 'optimize': sys.flags.optimize,
        'runtime_packages': {p: importlib.metadata.version(p) for p in ('httpx', 'mcp', 'pydantic')},
        'source_before': before, 'source_after': after, 'source_unchanged': before == after,
        'test_sha256': digest(Path(__file__).read_bytes()), 'fixture_sha256': digest((HERE / 'assignment-fixture.json').read_bytes()),
        'methods': result.testsRun, 'passed_methods': result.testsRun - len(failed_methods) - len(result.skipped),
        'failed_methods': sorted(failed_methods), 'failure_entries': len(result.failures),
        'error_entries': len(result.errors), 'skips': len(result.skipped),
        'public_invocations_captured': len(OUTPUTS), 'successful': result.wasSuccessful() and before == after}
    (output / 'results.log').write_text(log.getvalue())
    (output / 'public-outputs.json').write_text(json.dumps(OUTPUTS, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: receipt[k] for k in ('methods', 'passed_methods', 'failed_methods', 'failure_entries', 'error_entries', 'skips', 'public_invocations_captured', 'source_unchanged', 'successful')}))
    return 0 if receipt['successful'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
