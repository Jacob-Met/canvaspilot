"""Independent fictional data and expectations, before candidate exposure."""
import copy, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
base = json.loads((ROOT / 'historical-normalized.json').read_text())
def record(aid, name, group, flags=None, state='returned', visibility='reported_fields', extra=None):
    fields = {'id': aid, 'course_id': 42, 'assignment_group_id': group,
              'name': name, 'points_possible': 0, 'due_at': None,
              'html_url': 'https://school.invalid/never-follow'}
    sf = {'assignment_id': aid, 'user_id': 7}
    if flags is not None: sf.update(flags)
    if extra: sf.update(extra)
    return {'fields': fields, 'submission_state': state,
            'submission': None if state != 'returned' else {'grade_visibility': visibility, 'fields': sf}}

g0 = [
 record('9007199254740992', 'Alpha <b>literal</b> Ω', 3, {'missing': True, 'late': False, 'excused': None}, extra={'score': 0, 'grade': '', 'grade_matches_current_submission': True}),
 record('9007199254740993', 'Alpha <b>literal</b> Ω', 3, {'missing': False, 'late': True, 'excused': False}, visibility='not_posted', extra={'posted_at': None}),
 record('0007', 'Regex [a.*] Café', 3, {'missing': None, 'late': False, 'excused': True}, extra={'score': 85, 'grade': 'B', 'attempt': 2, 'grade_matches_current_submission': False}),
 record('702', 'missing late excused words', 3, state='not_returned'),
 record('703', '', 3, state='null'),
]
g1 = [
 record('9007199254740994', 'Alpha <b>literal</b> Ω', 4, {'missing': False, 'late': False, 'excused': False}),
 record('0042', 'Café 東京', 4, {'missing': True, 'late': True, 'excused': True}, visibility='assignment_not_visible', extra={'assignment_visible': False}),
 record(704, 'ordinary', 4),
 record('705', 'Empty "" field', 4, {'missing': None, 'late': None, 'excused': None}),
 record(706, 'Title CR\rLF\nTAB\tend\u0080', 4, {'missing': False}),
]
groups = [
 {'id': 3, 'name': 'Repeated lab Ω', 'position': 1, 'group_weight': 40, 'rules': {'drop_lowest': 1, 'drop_highest': 0, 'never_drop': ['0007']}, 'assignments_state': 'returned', 'assignments': g0},
 {'id': 4, 'name': 'Repeated lab Ω', 'position': 2, 'group_weight': 60, 'rules': None, 'assignments_state': 'returned', 'assignments': g1},
 {'id': 5, 'name': 'Empty returned group', 'assignments_state': 'returned', 'assignments': []},
 {'id': 6, 'name': 'Unknown null group', 'assignments_state': 'null', 'assignments': None},
 {'id': 7, 'name': 'Unknown absent group', 'assignments_state': 'not_returned', 'assignments': None},
]
base['course']['name'] = 'Fictional returned-grade view — Ω / 東京'
base['assignment_groups'] = groups
base['counts'] = {'groups_returned': 5, 'assignments_returned': 10, 'groups_without_assignment_list': 2,
 'submissions_not_returned': 1, 'submissions_null': 1, 'explicitly_not_posted': 1,
 'explicitly_not_visible': 1, 'excused_true': 2, 'missing_true': 2, 'late_true': 2,
 'grade_matches_current_submission_false': 1}
base['warnings'] = ['Fictional optional-value warning; omitted values remain unknown.']
hidden = copy.deepcopy(base)
hidden['course']['hide_final_grades'] = True
hidden['totals_visibility'] = 'hidden_by_course'
for row in hidden['enrollments']: row['reported_totals'] = {}
hidden['grading_periods_state'] = 'null'
hidden['grading_periods'] = None
all_ids = ['assignment-%d-%d' % (g, a) for g in range(2) for a in range(5)]
criteria = {
 'schema': 'canvaspilot.returned-grade-view-independent/1',
 'repository': 'Jacob-Met/canvaspilot',
 'original_commit': 'd567702f8a328320dad7d2eac74006cbe15cf0f8',
 'original_exporter_blob': '8a6281f62f99e18109f90a273a4c29da4929f3a3',
 'historical_fixture_blob': '09c05a32482dfdc09163e16870cfc6da0700852b',
 'generated_at': '2026-10-14T00:00:00+00:00',
 'scope': 'Fictional normalized derivatives; public render method only, no reader/API/CLI/account/provider operation.',
 'all_cards': all_ids, 'group_ids': ['group-'+str(i) for i in range(5)],
 'cases': [
  {'name': 'initial', 'search': '', 'group': '', 'flag': '', 'expected': all_ids},
  {'name': 'literal markup and case', 'search': ' ALPHA <b>literal</b> ', 'group': '', 'flag': '', 'expected': ['assignment-0-0', 'assignment-0-1', 'assignment-1-0']},
  {'name': 'literal regex punctuation', 'search': '[a.*]', 'group': '', 'flag': '', 'expected': ['assignment-0-2']},
  {'name': 'adjacent large ID A', 'search': '9007199254740992', 'group': '', 'flag': '', 'expected': ['assignment-0-0']},
  {'name': 'adjacent large ID B', 'search': '9007199254740993', 'group': '', 'flag': '', 'expected': ['assignment-0-1']},
  {'name': 'leading zeros', 'search': '0007', 'group': '', 'flag': '', 'expected': ['assignment-0-2']},
  {'name': 'displayed fallback title', 'search': 'assignment 703', 'group': '', 'flag': '', 'expected': ['assignment-0-4']},
  {'name': 'first repeated group occurrence', 'search': '', 'group': '0', 'flag': '', 'expected': all_ids[:5]},
  {'name': 'second repeated group occurrence', 'search': '', 'group': '1', 'flag': '', 'expected': all_ids[5:]},
  {'name': 'explicit missing only', 'search': '', 'group': '', 'flag': 'missing', 'expected': ['assignment-0-0', 'assignment-1-1']},
  {'name': 'explicit late only', 'search': '', 'group': '', 'flag': 'late', 'expected': ['assignment-0-1', 'assignment-1-1']},
  {'name': 'explicit excused only', 'search': '', 'group': '', 'flag': 'excused', 'expected': ['assignment-0-2', 'assignment-1-1']},
  {'name': 'combined literal group flag', 'search': 'café', 'group': '1', 'flag': 'missing', 'expected': ['assignment-1-1']},
  {'name': 'no inferred flag from words', 'search': 'missing late', 'group': '', 'flag': 'missing', 'expected': []},
  {'name': 'empty group', 'search': '', 'group': '2', 'flag': '', 'expected': []},
  {'name': 'unknown group', 'search': '', 'group': '3', 'flag': '', 'expected': []},
 ],
 'original': 'All cards/full report/exact JSON; filter controls absent. Freeze native original before candidate exposure.',
 'candidate': 'Default full; combined cases above; manual details.open preserved through filter/reset; no-match explanatory; reset full; hidden grade and full JSON stable.',
 'browser': 'Existing Chrome, isolated nonpersistent profile/context; actual JSON download, real Tab/Enter reset, 390px no horizontal document overflow, no external requests/storage/errors; managed cleanup before success.',
 'no_js_print': 'JavaScript-disabled complete report with no unusable controls; print media restores all cards and closed-detail content; no physical print or PDF glyph claim.',
 'conservation': 'Exact source/fixture/page path sets and bytes/SHA/mode/mtime/inode before and after; earlier epochs retained; no source/course replay on observer correction.'
}
out = ROOT / 'fixtures'; out.mkdir(exist_ok=True)
written=[]
for path, obj in [(out/'mixed.json',base),(out/'hidden.json',hidden),(ROOT/'criteria.json',criteria)]:
 raw=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
 with path.open('xb') as f:f.write(raw)
 written.append({'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()})
(ROOT/'freeze-manifest.json').write_text(json.dumps(written,indent=2)+'\n')
print(json.dumps(written))
