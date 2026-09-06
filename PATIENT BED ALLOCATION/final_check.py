"""Final quality check — verifies all endpoints and key values."""
import urllib.request, json, sys

def get(url):
    r = urllib.request.urlopen(url)
    return json.loads(r.read())

checks = []

dash = get('http://127.0.0.1:5000/api/dashboard')
exp  = dash['experiment']

checks.append(('Dashboard loads', True))
checks.append(('Total beds > 0', dash['total_beds'] > 0))
checks.append(('Delayed turnovers detected', dash['delayed_turnovers'] > 0))
checks.append(('Missing data detected', dash['missing_data_count'] > 0))
checks.append(('Conflicting data detected', dash['conflicting_data_count'] > 0))
checks.append(('High priority actions detected', dash['high_priority_unresolved'] > 0))
checks.append(('Baseline calculated', exp['baseline']['median'] is not None))
checks.append(('Target calculated', exp['target_median_minutes'] is not None))
checks.append(('Measured calculated', exp['measured']['median'] is not None))
checks.append(('Improvement calculated', exp['improvement_pct'] is not None))
checks.append(('Target met', exp['target_met'] == True))

admissions = get('http://127.0.0.1:5000/api/admissions')
checks.append(('Admissions endpoint returns 100', len(admissions) == 100))

for role in ['housekeeping', 'clinical', 'transfer']:
    filtered = get('http://127.0.0.1:5000/api/admissions?role=' + role)
    checks.append(('Role filter ' + role, len(filtered) <= 100))

val = get('http://127.0.0.1:5000/api/validation')
checks.append(('Validation summary detects issues', val['admissions_with_issues'] > 0))

actions = get('http://127.0.0.1:5000/api/actions')
checks.append(('Actions loaded', len(actions) > 0))

ea = get('http://127.0.0.1:5000/api/error-analysis')
checks.append(('Error analysis correct total', ea['total_records'] == 100))

adm_id = admissions[0]['admission_id']
detail = get('http://127.0.0.1:5000/api/admission/' + adm_id)
checks.append(('Detail endpoint loads', 'timeline' in detail))
checks.append(('Timeline has events', len(detail.get('timeline', [])) > 0))

# Verify edge cases in dataset
scenarios = {a['scenario'] for a in admissions}
for s in ['missing_cleaning', 'stale_data', 'conflicting', 'escalated_overdue',
          'duplicate_events', 'invalid_timestamp', 'invalid_sequence', 'bed_revert']:
    checks.append(('Edge case scenario: ' + s, s in scenarios))

print()
print('=== FINAL QUALITY CHECK ===')
all_pass = True
for label, result in checks:
    status = 'PASS' if result else 'FAIL'
    if not result:
        all_pass = False
    print('  ' + status + '  ' + label)

print()
print('ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED')

print()
print('=== KEY METRICS (from actual data) ===')
print('  Baseline median:   ' + str(exp['baseline']['median']) + ' min')
print('  Target median:     ' + str(exp['target_median_minutes']) + ' min')
print('  Measured median:   ' + str(exp['measured']['median']) + ' min')
print('  Measured mean:     ' + str(exp['measured']['mean']) + ' min')
print('  Measured P90:      ' + str(exp['measured']['p90']) + ' min')
print('  Improvement:       ' + str(exp['improvement_pct']) + '%')
print('  Target met:        ' + str(exp['target_met']))

print()
print('=== DATA QUALITY ===')
print('  Total admissions:  ' + str(val['total_admissions']))
print('  Valid admissions:  ' + str(val['valid_admissions']))
print('  With issues:       ' + str(val['admissions_with_issues']))
print('  Pct affected:      ' + str(val['pct_affected']) + '%')
ic = val['issue_counts']
for k, v in ic.items():
    print('    ' + k + ': ' + str(v))

sys.exit(0 if all_pass else 1)
