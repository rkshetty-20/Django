"""
Waitlist Auto-Promotion Signal
-------------------------------
When an AllocationResult is deleted (student drops / admin removes),
the system automatically promotes the highest-scoring WAITLISTED
student for that same course.

CO Mapping: CO2 (model logic) + CO4 (audit trail via status update)
SDG 4.5: Equitable access — no seat goes to waste after a drop.
"""

from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.db import transaction

from .models import AllocationResult, Preference, Course


@receiver(post_delete, sender=AllocationResult)
def promote_waitlisted_student(sender, instance, **kwargs):
    """
    Triggered after an AllocationResult row is deleted.
    Finds the next-best WAITLISTED preference for the freed course
    and promotes them to ALLOCATED, creating a new AllocationResult.
    """
    course = instance.course

    with transaction.atomic():
        # Re-fetch with lock to prevent race conditions
        course_locked = Course.objects.select_for_update().get(pk=course.pk)

        # Only promote if a seat is actually now free
        if course_locked.current_seats <= 0:
            return

        # Find best waitlisted candidate: highest score → earliest timestamp
        next_pref = (
            Preference.objects
            .select_related('student')
            .filter(course=course_locked, status='WAITLISTED')
            .order_by('-score', 'timestamp')
            .first()
        )

        if not next_pref:
            # No waitlisted students — just decrement the seat count
            course_locked.current_seats = max(course_locked.current_seats - 1, 0)
            course_locked.save(update_fields=['current_seats'])
            return

        # Promote the waitlisted student
        next_pref.status = 'ALLOCATED'
        next_pref.save(update_fields=['status'])

        AllocationResult.objects.create(
            student=next_pref.student,
            course=course_locked,
            preference_rank=next_pref.rank,
            score=next_pref.score,
        )

        # Seat count stays the same (one out, one in)
        # No change to current_seats needed
