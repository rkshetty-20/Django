"""
Waitlist Auto-Promotion Manual Drop Test
-----------------------------------------
Steps:
  1. Show current state
  2. Create a new student + rank-1 preference for a full course → WAITLISTED
  3. Delete an existing AllocationResult for that course (simulate a drop)
  4. Verify the waitlisted student was promoted → ALLOCATED + new AllocationResult
  5. Print before/after table
  6. Clean up test data
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from electives.models import Course, Student, Preference, AllocationResult, Department

SEP = '=' * 60

def banner(msg):
    print(f'\n{SEP}\n  {msg}\n{SEP}')

# ── 1. Show initial state ─────────────────────────────────────────
banner('STEP 1: Initial State')
print(f'  Allocations  : {AllocationResult.objects.count()}')
print(f'  Waitlisted   : {Preference.objects.filter(status="WAITLISTED").count()}')
print(f'  Rejected     : {Preference.objects.filter(status="REJECTED").count()}')

# ── 2. Pick a full course ─────────────────────────────────────────
banner('STEP 2: Find a Full Course')
# Use a course that already has an allocation (so current_seats >= 1)
alloc = AllocationResult.objects.select_related('course', 'student').first()
target_course = alloc.course

# Temporarily set capacity = current_seats to make it "full"
original_capacity = target_course.capacity
target_course.capacity = target_course.current_seats
target_course.save()

print(f'  Target course : {target_course.name} ({target_course.code})')
print(f'  Seats         : {target_course.current_seats}/{target_course.capacity}  → FULL')

# ── 3. Create a test waitlisted student ───────────────────────────
banner('STEP 3: Create Waitlisted Test Student')

# Create User + Student
test_user, _ = User.objects.get_or_create(username='test_waitlist_student')
test_user.set_password('testpass123')
test_user.save()

dept = Department.objects.first()
test_student, _ = Student.objects.get_or_create(
    user=test_user,
    defaults={
        'full_name'  : 'Test Waitlist Student',
        'usn'        : 'TEST9999',
        'cgpa'       : 9.5,
        'semester'   : 6,
        'department' : dept,
    }
)

# Create rank-1 preference pointing to the full course
test_pref, _ = Preference.objects.get_or_create(
    student=test_student,
    course=target_course,
    defaults={'rank': 1}
)
# Force WAITLISTED status (since the course is now full)
test_pref.status = 'WAITLISTED'
test_pref.score = (test_student.cgpa * 5) + 30  # rank bonus for rank=1
test_pref.save()

print(f'  Student       : {test_student.full_name}  (CGPA {test_student.cgpa})')
print(f'  Preference    : Rank 1 → {target_course.name}')
print(f'  Status        : {test_pref.status}')
print(f'  Score         : {test_pref.score}')

# ── 4. Restore capacity & trigger drop ───────────────────────────
banner('STEP 4: Restore Capacity → Trigger Drop (delete allocation)')

# Restore to original capacity so the drop signal sees a free seat
target_course.capacity = original_capacity
target_course.save()
print(f'  Course capacity restored to: {target_course.capacity}')
print(f'  Current seats before drop  : {target_course.current_seats}')

# Delete the original allocation → fires post_delete signal
victim = alloc
print(f'\n  Dropping: {victim.student.full_name} from {victim.course.name}')
victim.delete()

# Re-fetch updated objects
target_course.refresh_from_db()
test_pref.refresh_from_db()

# ── 5. Verify promotion ───────────────────────────────────────────
banner('STEP 5: Verify Waitlist Promotion')

new_alloc = AllocationResult.objects.filter(student=test_student, course=target_course).first()

promoted = test_pref.status == 'ALLOCATED' and new_alloc is not None

print(f'  Preference status   : {test_pref.status}  (expected: ALLOCATED)')
print(f'  New AllocationResult: {"EXISTS" if new_alloc else "MISSING"}')
print(f'  Course seats now    : {target_course.current_seats}/{target_course.capacity}')
print()
if promoted:
    print('  ✓  WAITLIST AUTO-PROMOTION WORKS CORRECTLY!')
    print(f'  ✓  {test_student.full_name} (CGPA {test_student.cgpa}) promoted from WAITLISTED → ALLOCATED')
    print(f'  ✓  AllocationResult id={new_alloc.id}, score={new_alloc.score}')
else:
    print('  ✗  PROMOTION FAILED — check signals.py wiring')

# ── 6. Cleanup ────────────────────────────────────────────────────
banner('STEP 6: Cleanup Test Data')
if new_alloc:
    new_alloc.delete()
test_pref.delete()
test_student.delete()
test_user.delete()
# Restore victim allocation
from electives.models import AllocationResult as AR
AR.objects.create(
    student=alloc.student,
    course=alloc.course,
    preference_rank=alloc.preference_rank,
    score=alloc.score,
)
# Restore alloc preference status
Preference.objects.filter(student=alloc.student, course=alloc.course).update(status='ALLOCATED')
target_course.current_seats = AllocationResult.objects.filter(course=target_course).count()
target_course.save()

print(f'  Test student deleted')
print(f'  Original allocation restored')
print(f'  Course seats restored: {target_course.current_seats}/{target_course.capacity}')

banner('RESULT: ' + ('ALL CHECKS PASSED' if promoted else 'TEST FAILED'))
