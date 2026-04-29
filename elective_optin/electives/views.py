import json
import csv

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Avg, Q, F
from django.views.decorators.http import require_POST, require_GET

from .models import Course, Student, Preference, AllocationResult, Department, StudentCourseHistory
from .forms import PreferenceForm, StudentLoginForm
from .utils import allocate_electives, get_recommendations


# ─── Helpers ──────────────────────────────────────────────────────────────────

def is_staff(user):
    return user.is_staff


def get_student_or_none(user):
    try:
        return user.student
    except Exception:
        return None


# ─── Public ───────────────────────────────────────────────────────────────────

def landing(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('student_dashboard')
    total_courses   = Course.objects.count()
    total_seats     = sum(c.capacity for c in Course.objects.all())
    total_depts     = Department.objects.count()
    return render(request, 'electives/landing.html', {
        'total_courses': total_courses,
        'total_seats':   total_seats,
        'total_depts':   total_depts,
    })


def student_login(request):
    if request.user.is_authenticated:
        return redirect('landing')
    form = StudentLoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        if user.is_staff:
            return redirect('admin_dashboard')
        return redirect('student_dashboard')
    return render(request, 'registration/login.html', {'form': form})


def student_logout(request):
    logout(request)
    return redirect('landing')


# ─── Catalog (public) ─────────────────────────────────────────────────────────

def catalog(request):
    courses   = Course.objects.select_related('department').all()
    cat_filter  = request.GET.get('category', '')
    dept_filter = request.GET.get('department', '')
    q_filter    = request.GET.get('q', '')

    if cat_filter:
        courses = courses.filter(category=cat_filter)
    if dept_filter:
        courses = courses.filter(department__code=dept_filter)
    if q_filter:
        courses = courses.filter(
            Q(name__icontains=q_filter) |
            Q(code__icontains=q_filter) |
            Q(job_perspective__icontains=q_filter)
        )

    student = get_student_or_none(request.user) if request.user.is_authenticated else None

    return render(request, 'electives/catalog.html', {
        'courses':      courses,
        'departments':  Department.objects.all(),
        'category_filter': cat_filter,
        'dept_filter':  dept_filter,
        'q_filter':     q_filter,
        'is_student':   student is not None,
    })


# ─── Student Dashboard ────────────────────────────────────────────────────────

@login_required
def student_dashboard(request):
    student = get_student_or_none(request.user)
    if not student:
        messages.warning(request, 'Student profile not found. Please contact admin.')
        return redirect('catalog')

    preferences    = student.preferences.select_related('course__department').order_by('rank')
    allocation     = getattr(student, 'allocation_result', None)
    recommendations = get_recommendations(student, limit=3)

    return render(request, 'electives/student_dashboard.html', {
        'student':        student,
        'preferences':    preferences,
        'allocation':     allocation,
        'recommendations': recommendations,
    })


# ─── Preference Submission ────────────────────────────────────────────────────

@login_required
def submit_preference(request):
    student = get_student_or_none(request.user)
    if not student:
        messages.error(request, 'No student profile linked to your account.')
        return redirect('catalog')

    # Check if already allocated
    if hasattr(student, 'allocation_result'):
        messages.info(request, 'Allocation has already been finalized. You cannot change your preferences.')
        return redirect('my_results')

    existing = {p.rank: p.course for p in student.preferences.all()}

    if request.method == 'POST':
        form = PreferenceForm(request.POST)
        if form.is_valid():
            choices = [
                form.cleaned_data['choice1'],
                form.cleaned_data['choice2'],
                form.cleaned_data['choice3'],
            ]
            # Validate: no duplicate
            if len(set(c.id for c in choices)) < 3:
                messages.error(request, 'Please select three different courses.')
            else:
                # Remove old preferences
                student.preferences.all().delete()
                # Save new
                for rank, course in enumerate(choices, start=1):
                    Preference.objects.create(student=student, course=course, rank=rank)
                messages.success(request, '✅ Preferences saved successfully!')
                return redirect('student_dashboard')
    else:
        initial = {}
        if existing:
            initial = {
                'choice1': existing.get(1),
                'choice2': existing.get(2),
                'choice3': existing.get(3),
            }
        form = PreferenceForm(initial=initial)

    return render(request, 'electives/submit.html', {
        'form':     form,
        'student':  student,
        'existing': existing,
    })


# ─── Results ──────────────────────────────────────────────────────────────────

@login_required
def my_results(request):
    student    = get_student_or_none(request.user)
    if not student:
        return redirect('catalog')
    preferences = student.preferences.select_related('course__department').order_by('rank')
    allocation  = getattr(student, 'allocation_result', None)
    return render(request, 'electives/results.html', {
        'student':     student,
        'preferences': preferences,
        'allocation':  allocation,
    })


# ─── AI Recommendations ───────────────────────────────────────────────────────

@login_required
def recommendations_view(request):
    student = get_student_or_none(request.user)
    if not student:
        return redirect('catalog')
    recs = get_recommendations(student, limit=6)
    return render(request, 'electives/recommendations.html', {
        'student': student,
        'recommendations': recs,
    })


# ─── Admin Dashboard ──────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff)
def admin_dashboard(request):
    if request.method == 'POST' and 'run_allocation' in request.POST:
        count = allocate_electives()
        messages.success(request, f'✅ Allocation complete! {count} students allotted.')
        return redirect('admin_dashboard')

    courses      = Course.objects.select_related('department').all()
    allocations  = AllocationResult.objects.select_related('student', 'course__department').all()
    students     = Student.objects.select_related('department').all()

    # Analytics data for Chart.js
    # 1. Most demanded (preference count per course)
    demand_data = (
        Preference.objects.values('course__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:8]
    )

    # 2. Seats filled vs remaining per course
    seat_data = [
        {'name': c.name, 'filled': c.current_seats, 'remaining': c.available_seats}
        for c in courses[:8]
    ]

    # 3. Department-wise participation
    dept_data = (
        Preference.objects.values('course__department__name')
        .annotate(count=Count('student', distinct=True))
        .order_by('-count')
    )

    # 4. Avg CGPA per allotted course
    cgpa_data = (
        AllocationResult.objects.values('course__name')
        .annotate(avg_cgpa=Avg('student__cgpa'))
        .order_by('-avg_cgpa')[:8]
    )

    # 5. Top rejected courses (course with most rejections)
    rejected_data = (
        Preference.objects.filter(status='REJECTED')
        .values('course__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:6]
    )

    stats = {
        'total_students':   students.count(),
        'submitted':        students.filter(preferences__isnull=False).distinct().count(),
        'allocated':        allocations.count(),
        'total_courses':    courses.count(),
    }

    return render(request, 'electives/admin_dashboard.html', {
        'courses':         courses,
        'allocations':     allocations,
        'stats':           stats,
        'demand_json':     json.dumps(list(demand_data)),
        'seat_json':       json.dumps(seat_data),
        'dept_json':       json.dumps(list(dept_data)),
        'cgpa_json':       json.dumps([{'name': d['course__name'], 'avg': round(d['avg_cgpa'] or 0, 2)} for d in cgpa_data]),
        'rejected_json':   json.dumps(list(rejected_data)),
    })


# ─── Live Seat API ────────────────────────────────────────────────────────────

@require_GET
def api_live_seats(request):
    data = {
        str(c.id): {
            'available': c.available_seats,
            'total':     c.capacity,
            'filled':    c.current_seats,
        }
        for c in Course.objects.all()
    }
    return JsonResponse(data)


@require_GET
def api_seat_single(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    return JsonResponse({
        'available_seats': course.available_seats,
        'total':           course.capacity,
        'filled':          course.current_seats,
    })


# ─── Intelligent Course Suggestion (AJAX) ────────────────────────────────────

@require_GET
def check_and_suggest(request, course_id):
    """
    CO5 – AJAX endpoint.
    If a course has seats → return {"status": "available"}.
    If full → return top-5 alternatives sorted by:
      1. Same department as the student (priority)
      2. Same category as the requested course
      3. Most available seats (tiebreaker)
    """
    course = get_object_or_404(Course, pk=course_id)

    if course.available_seats > 0:
        return JsonResponse({'status': 'available', 'available': course.available_seats})

    # Build smart alternatives
    student = get_student_or_none(request.user)
    already_chosen_ids = []
    if student:
        already_chosen_ids = list(
            student.preferences.values_list('course_id', flat=True)
        )

    # Start with same category, seats available, not the full course, not already chosen
    qs = (
        Course.objects.filter(current_seats__lt=F('capacity'))
        .exclude(pk=course_id)
        .exclude(pk__in=already_chosen_ids)
        .select_related('department')
    )

    # Prioritise same department then same category
    same_dept = qs.filter(department=course.department).annotate(
        free_seats=F('capacity') - F('current_seats')
    ).order_by('-free_seats')[:3]
    same_cat  = qs.filter(category=course.category).exclude(
        pk__in=[c.pk for c in same_dept]
    ).annotate(
        free_seats=F('capacity') - F('current_seats')
    ).order_by('-free_seats')[:2]

    alternatives = list(same_dept) + list(same_cat)

    # If still fewer than 3, pad with any available
    if len(alternatives) < 3:
        seen_ids = [c.pk for c in alternatives] + [course_id]
        extra = (
            qs.exclude(pk__in=seen_ids)
            .annotate(free_seats=F('capacity') - F('current_seats'))
            .order_by('-free_seats')
            [: 5 - len(alternatives)]
        )
        alternatives += list(extra)

    data = [
        {
            'id':       c.id,
            'name':     c.name,
            'code':     c.code,
            'dept':     c.department.name,
            'category': c.get_category_display(),
            'seats':    c.capacity - c.current_seats,
            'capacity': c.capacity,
        }
        for c in alternatives[:5]
    ]

    return JsonResponse({
        'status':       'full',
        'course_name':  course.name,
        'alternatives': data,
    })


# ─── CSV Export ───────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff)
def export_csv(request):
    category = request.GET.get('category', '')
    dept     = request.GET.get('department', '') or request.GET.get('branch', '')

    qs = AllocationResult.objects.select_related(
        'student__user', 'student__department', 'course__department'
    ).all()

    if category:
        qs = qs.filter(course__category=category)
    if dept:
        qs = qs.filter(course__department__code=dept)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="optiseat_allocation.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Student Name', 'USN', 'Department', 'CGPA', 'Semester',
        'Allotted Course', 'Course Code', 'Course Category',
        'Preference Rank', 'Score', 'Allocated At'
    ])

    for result in qs:
        s = result.student
        c = result.course
        writer.writerow([
            s.full_name or s.user.username,
            s.usn,
            s.department.name,
            s.cgpa,
            s.semester,
            c.name,
            c.code,
            c.get_category_display(),
            result.preference_rank,
            result.score,
            result.allocated_at.strftime('%Y-%m-%d %H:%M'),
        ])

    return response