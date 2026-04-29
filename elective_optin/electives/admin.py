from django.contrib import admin
from .models import Department, Student, Course, Preference, AllocationResult, StudentCourseHistory


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']
    search_fields = ['name', 'code']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'department', 'category', 'capacity', 'current_seats', 'available_seats']
    list_filter  = ['category', 'department', 'is_open_elective']
    search_fields = ['name', 'code']
    readonly_fields = ['current_seats']

    def available_seats(self, obj):
        return obj.available_seats
    available_seats.short_description = 'Available'


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display  = ['full_name', 'usn', 'user', 'department', 'cgpa', 'semester', 'allocation_status']
    list_filter   = ['department', 'semester']
    search_fields = ['full_name', 'usn', 'user__username']

    def allocation_status(self, obj):
        return obj.allocation_status
    allocation_status.short_description = 'Status'


@admin.register(Preference)
class PreferenceAdmin(admin.ModelAdmin):
    list_display  = ['student', 'rank', 'course', 'status', 'score', 'timestamp']
    list_filter   = ['status', 'rank']
    search_fields = ['student__full_name', 'course__name']


@admin.register(AllocationResult)
class AllocationResultAdmin(admin.ModelAdmin):
    list_display  = ['student', 'course', 'preference_rank', 'score', 'allocated_at']
    list_filter   = ['preference_rank', 'course__department']
    search_fields = ['student__full_name', 'course__name']


@admin.register(StudentCourseHistory)
class StudentCourseHistoryAdmin(admin.ModelAdmin):
    list_display  = ['student', 'course_code', 'course_name']
    search_fields = ['student__full_name', 'course_code']