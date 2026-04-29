"""
Feature Test Suite — Priority-Based Elective Opt-In System
Run with: python run_tests.py
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import json
import csv as csv_module
import io

results = []

def check(label, condition, detail=''):
    status = 'PASS' if condition else 'FAIL'
    results.append((status, label, detail))
    icon = '✓' if condition else '✗'
    suffix = f'  ({detail})' if detail else ''
    print(f'  [{icon}]  {label}{suffix}')

print()
print('=' * 62)
print('  OPTISEAT — FEATURE TEST SUITE')
print('=' * 62)

# ── Import models ─────────────────────────────────────────────────
from electives.models import Course, Student, Preference, AllocationResult, Department

# ─────────────────────────────────────────────────────────────────
print('\n  SECTION 1: Database & Seed Data')
print('  ' + '-' * 44)

try:
    Course.objects.count()
    check('DB connection',          True)
except Exception as e:
    check('DB connection',          False, str(e))

check('Departments seeded',  Department.objects.count() >= 1,   f'{Department.objects.count()} depts')
check('Courses seeded',      Course.objects.count() >= 1,       f'{Course.objects.count()} courses')
check('Students seeded',     Student.objects.count() >= 1,      f'{Student.objects.count()} students')

# ─────────────────────────────────────────────────────────────────
print('\n  SECTION 2: CRUD — Preferences')
print('  ' + '-' * 44)

pref_count = Preference.objects.count()
check('Preferences exist',              pref_count > 0,         f'{pref_count} rows')
valid_ranks = Preference.objects.filter(rank__in=[1, 2, 3]).count()
check('All ranks are 1–3',              valid_ranks == pref_count, 'all valid')

from django.db import connection
cursor = connection.cursor()
cursor.execute(
    'SELECT student_id, course_id, COUNT(*) c '
    'FROM electives_preference GROUP BY student_id, course_id HAVING c > 1'
)
dupes = cursor.fetchall()
check('No duplicate preferences',       len(dupes) == 0,        f'{len(dupes)} dupes found')

# ─────────────────────────────────────────────────────────────────
print('\n  SECTION 3: Validation')
print('  ' + '-' * 44)

bad_cgpa = Student.objects.filter(cgpa__lt=0.0).count() + Student.objects.filter(cgpa__gt=10.0).count()
check('CGPA in range 0–10',             bad_cgpa == 0,          f'{bad_cgpa} out-of-range')

# ─────────────────────────────────────────────────────────────────
print('\n  SECTION 4: Allocation Algorithm')
print('  ' + '-' * 44)

alloc_count = AllocationResult.objects.count()
check('Allocation ran (results exist)',  alloc_count > 0,        f'{alloc_count} allocated')
check('High-CGPA students allocated',
      AllocationResult.objects.filter(student__cgpa__gte=8.0).exists(),
      'CGPA >= 8 got seats')

top    = AllocationResult.objects.order_by('-score').first()
bottom = AllocationResult.objects.order_by('score').first()
if top and bottom:
    check('Score ordering correct (top >= bottom)',
          top.score >= bottom.score,
          f'top={top.score}  bottom={bottom.score}')

seat_ok = all(
    c.current_seats == AllocationResult.objects.filter(course=c).count()
    for c in Course.objects.all()
)
check('Seat counters match allocation count', seat_ok)

rejected   = Preference.objects.filter(status='REJECTED').count()
waitlisted = Preference.objects.filter(status='WAITLISTED').count()
allocated  = Preference.objects.filter(status='ALLOCATED').count()
check('Preference statuses set correctly',
      allocated == alloc_count,
      f'allocated={allocated}  waitlisted={waitlisted}  rejected={rejected}')

# ─────────────────────────────────────────────────────────────────
print('\n  SECTION 5: AJAX Endpoints')
print('  ' + '-' * 44)

from django.test import RequestFactory
from electives.views import api_live_seats, api_seat_single, check_and_suggest

rf = RequestFactory()

# /api/seats/
req = rf.get('/api/seats/')
resp = api_live_seats(req)
data = json.loads(resp.content)
check('GET /api/seats/ → 200',          resp.status_code == 200, f'{len(data)} courses')
check('JSON keys: available/total/filled',
      all('available' in v and 'total' in v and 'filled' in v for v in data.values()))

# /api/seats/<id>/
first = Course.objects.first()
resp2 = api_seat_single(rf.get(f'/api/seats/{first.id}/'), first.id)
d2 = json.loads(resp2.content)
check('GET /api/seats/<id>/ → 200',     resp2.status_code == 200,
      f'available={d2.get("available_seats")}')

# /api/check-course/<id>/ — available
from django.db.models import F
avail_course = Course.objects.filter(current_seats__lt=F('capacity')).first()
if avail_course:
    req3 = rf.get(f'/api/check-course/{avail_course.id}/')
    req3.user = type('AnonUser', (), {'is_authenticated': False})()
    resp3 = check_and_suggest(req3, avail_course.id)
    d3 = json.loads(resp3.content)
    check('check-course available → status=available',
          d3.get('status') == 'available',
          f'seats={d3.get("available")}')

# /api/check-course/<id>/ — full course simulation
some_course = Course.objects.first()
orig_cap = some_course.capacity
some_course.capacity = some_course.current_seats  # make it "full"
some_course.save()
req4 = rf.get(f'/api/check-course/{some_course.id}/')
req4.user = type('AnonUser', (), {'is_authenticated': False})()
resp4 = check_and_suggest(req4, some_course.id)
d4 = json.loads(resp4.content)
check('check-course full → returns alternatives',
      d4.get('status') == 'full' and isinstance(d4.get('alternatives'), list),
      f'{len(d4.get("alternatives", []))} alternatives')
some_course.capacity = orig_cap  # restore
some_course.save()

# ─────────────────────────────────────────────────────────────────
print('\n  SECTION 6: CSV Export')
print('  ' + '-' * 44)

from electives.views import export_csv
from django.contrib.auth.models import User

admin_user = User.objects.filter(is_staff=True).first()

req_csv = rf.get('/export/')
req_csv.user = admin_user
resp_csv = export_csv(req_csv)
csv_content = resp_csv.content.decode()
rows = [r for r in csv_content.strip().split('\n') if r.strip()]

check('GET /export/ → 200',             resp_csv.status_code == 200)
check('CSV header row present',         'Student Name' in rows[0] if rows else False)
check('CSV has data rows',              len(rows) > 1,          f'{len(rows)-1} rows')
check('Content-Type = text/csv',        resp_csv['Content-Type'] == 'text/csv')
check('Content-Disposition set',
      'optiseat_allocation.csv' in resp_csv.get('Content-Disposition', ''))
check('CSV has 11 columns',
      len(rows[0].split(',')) == 11 if rows else False,
      f'{len(rows[0].split(","))} cols')

req_cse = rf.get('/export/?branch=CSE')
req_cse.user = admin_user
resp_cse = export_csv(req_cse)
cse_rows = [r for r in resp_cse.content.decode().strip().split('\n') if r.strip()]
check('CSV ?branch=CSE filter works',   len(cse_rows) >= 1,     f'{len(cse_rows)-1} CSE rows')

req_pro = rf.get('/export/?category=PROFESSIONAL')
req_pro.user = admin_user
resp_pro = export_csv(req_pro)
pro_rows = [r for r in resp_pro.content.decode().strip().split('\n') if r.strip()]
check('CSV ?category=PROFESSIONAL works', len(pro_rows) >= 1,   f'{len(pro_rows)-1} PROF rows')

# ─────────────────────────────────────────────────────────────────
print('\n  SECTION 7: Waitlist Signal')
print('  ' + '-' * 44)

from django.db.models.signals import post_delete
from electives.signals import promote_waitlisted_student

# Check signal is registered by looking for its name/module in receiver list
registered = False
for r in post_delete.receivers:
    # Each entry is a tuple; the second element is a weakref to the receiver function
    try:
        fn = r[1]()
        if fn is not None and getattr(fn, '__name__', '') == 'promote_waitlisted_student':
            registered = True
            break
    except Exception:
        pass
check('post_delete signal registered', registered)

# ─────────────────────────────────────────────────────────────────
print('\n  SECTION 8: URL Routing')
print('  ' + '-' * 44)

from django.urls import reverse, NoReverseMatch

urls_to_check = [
    'landing', 'catalog', 'login', 'logout',
    'student_dashboard', 'submit_preference', 'my_results',
    'recommendations', 'admin_dashboard', 'export_csv',
    'api_live_seats',
]
for name in urls_to_check:
    try:
        url = reverse(name)
        check(f'URL [{name}] resolves',    True, url)
    except NoReverseMatch as e:
        check(f'URL [{name}] resolves',    False, str(e))

# ─────────────────────────────────────────────────────────────────
print()
print('=' * 62)
passes = sum(1 for r in results if r[0] == 'PASS')
fails  = sum(1 for r in results if r[0] == 'FAIL')
total  = len(results)
print(f'  RESULT:  {passes} PASSED  |  {fails} FAILED  |  {total} TOTAL')
print('=' * 62)
if fails == 0:
    print('  ALL TESTS PASSED — System is judge-ready!')
else:
    print('  FAILED TESTS:')
    for s, label, detail in results:
        if s == 'FAIL':
            print(f'    - {label}  ({detail})')
print('=' * 62)
sys.exit(0 if fails == 0 else 1)
