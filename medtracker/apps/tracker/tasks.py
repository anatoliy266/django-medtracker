import logging
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from .models import MedicineSchedule, Status
from .views import _invalidate_medicines_cache

logger = logging.getLogger(__name__)


@shared_task
def check_overdue_medicines():
    now = timezone.localtime().time()

    overdue_qs = MedicineSchedule.objects.filter(
        status=Status.PLANNED,
        time__lt=now,
    ).select_related('medicine', 'medicine__user')

    affected_user_ids = set()
    updated_count = 0

    for schedule in overdue_qs:
        schedule.status = Status.OVERDUE
        schedule.save(update_fields=['status'])

        user = schedule.medicine.user
        affected_user_ids.add(user.id)
        updated_count += 1

        _send_overdue_notification(user, schedule)

    # Сбрасываем кэш в Redis только для тех пользователей, у кого обновились статусы
    for user_id in affected_user_ids:
        _invalidate_medicines_cache(user_id)

    return f"Checked overdue: updated {updated_count} schedules"


@shared_task
def reset_daily_schedules():
    """Сбрасывает статусы приема в начале нового дня"""
    schedules = MedicineSchedule.objects.exclude(status=Status.PLANNED).select_related('medicine')
    user_ids = set(schedules.values_list('medicine__user_id', flat=True))
    count = schedules.update(status=Status.PLANNED)

    for user_id in user_ids:
        _invalidate_medicines_cache(user_id)

    return f"Reset {count} schedules to PLANNED"


def _send_overdue_notification(user, schedule):
    msg = (
        f"Напоминание: вы пропустили прием лекарства «{schedule.medicine.name}» "
        f"({schedule.medicine.dose}), запланированный на {schedule.time.strftime('%H:%M')}."
    )
    logger.warning(f"[NOTIFICATION -> {user.username}]: {msg}")

    if user.email:
        try:
            send_mail(
                subject=f"Пропущен прием: {schedule.medicine.name}",
                message=msg,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@medtracker.local'),
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Ошибка отправки email пользователю {user.username}: {e}")