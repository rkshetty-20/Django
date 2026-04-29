from django.db import transaction
from .models import Preference, Course, AllocationResult, Student

# ─── Allocation Engine ────────────────────────────────────────────────────────

def allocate_electives():
    """
    Priority-based ranked-choice allocation.

    Score formula:
        base_score = (CGPA × 5)   → max 50 pts
        time_bonus                 → max 20 pts  (earlier = higher)
        preference_bonus           → 30 / 20 / 10 pts per rank

    Algorithm:
        Round 1 → All students compete for Choice 1
        Round 2 → Unallocated students compete for Choice 2
        Round 3 → Still-unallocated students compete for Choice 3
    """
    with transaction.atomic():
        # Reset previous run
        Preference.objects.all().update(status='PENDING', score=0.0)
        AllocationResult.objects.all().delete()
        Course.objects.all().update(current_seats=0)

        # Need at least one preference to proceed
        first_prefs = Preference.objects.filter(rank=1).order_by('timestamp')
        if not first_prefs.exists():
            return 0

        earliest = first_prefs.first().timestamp
        latest   = first_prefs.last().timestamp
        max_delta = (latest - earliest).total_seconds()

        def base_score(student):
            cgpa_score = student.cgpa * 5           # max 50
            try:
                sub_time = student.preferences.filter(rank=1).first().timestamp
                if max_delta > 0:
                    elapsed = (sub_time - earliest).total_seconds()
                    time_score = 20 * (1 - elapsed / max_delta)
                else:
                    time_score = 20
            except Exception:
                time_score = 10
            return round(cgpa_score + time_score, 2)

        # Pre-compute base scores
        students = Student.objects.filter(preferences__isnull=False).distinct()
        score_map = {s.id: base_score(s) for s in students}

        pref_bonus = {1: 30, 2: 20, 3: 10}
        allocated_students = set()
        allocated_count = 0

        for rank in [1, 2, 3]:
            rank_prefs = list(
                Preference.objects.select_related('student', 'course')
                .filter(rank=rank)
                .exclude(student_id__in=allocated_students)
            )
            # Sort: highest base_score first, then earlier timestamp
            rank_prefs.sort(key=lambda p: (-score_map.get(p.student_id, 0), p.timestamp))

            for pref in rank_prefs:
                if pref.student_id in allocated_students:
                    continue

                course = Course.objects.select_for_update().get(pk=pref.course_id)

                final_score = round(score_map.get(pref.student_id, 0) + pref_bonus[rank], 2)

                if course.current_seats < course.capacity:
                    pref.status = 'ALLOCATED'
                    pref.score  = final_score
                    pref.save(update_fields=['status', 'score'])

                    course.current_seats += 1
                    course.save(update_fields=['current_seats'])

                    AllocationResult.objects.create(
                        student=pref.student,
                        course=course,
                        preference_rank=rank,
                        score=final_score,
                    )
                    allocated_students.add(pref.student_id)
                    allocated_count += 1
                else:
                    # Rank-1 overflow → WAITLISTED; ranks 2 & 3 → REJECTED
                    new_status = 'WAITLISTED' if rank == 1 else 'REJECTED'
                    pref.status = new_status
                    pref.score  = final_score
                    pref.save(update_fields=['status', 'score'])

        # Any remaining unresolved → Rejected
        Preference.objects.filter(status='PENDING').exclude(
            student_id__in=allocated_students
        ).update(status='REJECTED')

        return allocated_count


# ─── AI Recommendation Engine ─────────────────────────────────────────────────

BRANCH_KEYWORDS = {
    'CSE': ['AI', 'Machine Learning', 'Cloud', 'Data', 'Network', 'Security',
            'Artificial', 'Deep Learning', 'NLP', 'Web', 'IoT'],
    'ECE': ['IoT', 'Signal', 'Embedded', 'Wireless', 'VLSI', 'Microprocessor',
            'Communication', 'Electronics', 'Sensor'],
    'ME':  ['Robotics', 'Manufacturing', 'CAD', 'Thermal', 'Automobile',
            'FEA', 'Dynamics', 'Fluid', 'Design'],
    'CIVIL': ['Structural', 'Environmental', 'Geotechnical', 'Transportation',
              'Concrete', 'Surveying', 'Construction'],
    'MBA': ['Management', 'Finance', 'Marketing', 'HR', 'Operations',
            'Strategy', 'Entrepreneurship'],
    'IS':  ['Security', 'AI', 'Machine Learning', 'Cloud', 'Data',
            'Network', 'Blockchain', 'Web'],
}

def get_recommendations(student, limit=4):
    """
    Content-based collaborative filtering using branch keywords + CGPA tier.
    Returns queryset of recommended Course objects.
    """
    dept_code = student.department.code.upper()
    keywords  = BRANCH_KEYWORDS.get(dept_code, BRANCH_KEYWORDS['CSE'])

    # Exclude already applied courses
    applied_ids = student.preferences.values_list('course_id', flat=True)
    available   = Course.objects.exclude(id__in=applied_ids).select_related('department')

    scored = []
    for course in available:
        text  = f"{course.name} {course.job_perspective} {course.salient_features}".lower()
        score = sum(1 for kw in keywords if kw.lower() in text)

        # Bonus: high-CGPA students get advanced courses boosted
        if student.cgpa >= 8.5 and any(w in text for w in ['advanced', 'machine learning', 'ai', 'deep']):
            score += 2
        # Bonus: availability weight
        if course.available_seats > 0:
            score += 1

        scored.append((score, course.id))

    scored.sort(key=lambda x: -x[0])
    top_ids = [cid for _, cid in scored[:limit]]

    # Preserve order
    courses = {c.id: c for c in Course.objects.filter(id__in=top_ids)}
    return [courses[cid] for cid in top_ids if cid in courses]