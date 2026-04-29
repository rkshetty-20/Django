from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

CATEGORY_CHOICES = [
    ('PROFESSIONAL', 'Professional Elective'),
    ('OPEN', 'Open Elective'),
    ('ABILITY', 'Ability Enhancement'),
]

STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('ALLOCATED', 'Allocated'),
    ('WAITLISTED', 'Waitlisted'),
    ('REJECTED', 'Rejected'),
]


class Department(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Course(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='courses')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    job_perspective = models.TextField()
    salient_features = models.TextField(blank=True)
    prerequisites = models.TextField(blank=True, default='None')
    is_open_elective = models.BooleanField(default=False)
    capacity = models.PositiveIntegerField(default=30)
    current_seats = models.PositiveIntegerField(default=0)

    @property
    def available_seats(self):
        return max(self.capacity - self.current_seats, 0)

    @property
    def fill_percentage(self):
        if self.capacity == 0:
            return 0
        return int((self.current_seats / self.capacity) * 100)

    def __str__(self):
        return f"{self.code} – {self.name}"


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    cgpa = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)],
        default=7.0
    )
    semester = models.PositiveIntegerField(default=6)
    full_name = models.CharField(max_length=100, blank=True)
    usn = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.full_name or self.user.username

    @property
    def has_submitted_preference(self):
        return self.preferences.exists()

    @property
    def allocation_status(self):
        result = getattr(self, 'allocation_result', None)
        if result:
            return 'ALLOCATED'
        if self.has_submitted_preference:
            return 'PENDING'
        return 'NOT_SUBMITTED'


class Preference(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='preferences')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    rank = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    score = models.FloatField(default=0.0)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('student', 'course')]
        ordering = ['rank']

    def __str__(self):
        return f"{self.student} – Choice {self.rank}: {self.course.name}"


class AllocationResult(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='allocation_result')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='allocations')
    preference_rank = models.PositiveIntegerField()
    score = models.FloatField()
    allocated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} → {self.course.name} (Choice #{self.preference_rank})"


class StudentCourseHistory(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='history')
    course_name = models.CharField(max_length=200)
    course_code = models.CharField(max_length=20)
    is_future = models.BooleanField(default=False)

    class Meta:
        unique_together = [('student', 'course_code')]

    def __str__(self):
        return f"{self.student} – {self.course_code}"