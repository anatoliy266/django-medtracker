import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Medicine, MedicineSchedule, UserActionLog, ActionType
from .serializers import MedicineSerializer, MedicineScheduleSerializer

logger = logging.getLogger(__name__)
CACHE_TTL = 60 * 15


def _get_medicines_cache_key(user_id):
    return f"medicines:user:{user_id}"


def _invalidate_medicines_cache(user_id):
    try:
        cache.delete(_get_medicines_cache_key(user_id))
    except Exception as e:
        logger.warning(f"Не удалось очистить кэш Redis для user_id={user_id}: {e}")


def _log_user_action(user, action, details, payload):
    try:
        UserActionLog.objects.create(
            user_id=user.id,
            username=user.username,
            action=action,
            details=details,
            data=payload,
        )
    except Exception as e:
        logger.error(f"Ошибка записи в UserActionLog (user_id={user.id}, action={action}): {e}")


# 1. Обычная вьюха для рендера HTML-страницы
@login_required(login_url='accounts:login')
def medicine_list(request):
    cache_key = _get_medicines_cache_key(request.user.id)
    medicines = None

    try:
        medicines = cache.get(cache_key)
    except Exception as e:
        logger.warning(f"Ошибка чтения из Redis для user_id={request.user.id}: {e}")

    if medicines is None:
        medicines = list(
            Medicine.objects.filter(user=request.user).prefetch_related('schedules')
        )
        try:
            cache.set(cache_key, medicines, timeout=CACHE_TTL)
        except Exception as e:
            logger.warning(f"Ошибка записи в Redis для user_id={request.user.id}: {e}")

    return render(request, 'tracker/medicine_list.html', {
        'medicines': medicines,
        'title': 'Мои лекарства',
    })


# 2. REST API для лекарств (GET, POST, PATCH, DELETE)
class MedicineViewSet(viewsets.ModelViewSet):
    serializer_class = MedicineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Изоляция данных: юзер видит и меняет только свои лекарства
        return Medicine.objects.filter(user=self.request.user).prefetch_related('schedules')

    def perform_create(self, serializer):
        medicine = serializer.save(user=self.request.user)
        _invalidate_medicines_cache(self.request.user.id)
        _log_user_action(
            user=self.request.user,
            action=ActionType.CREATE,
            details=f"Добавлено лекарство: {medicine.name}",
            payload={'old_data': None, 'new_data': MedicineSerializer(medicine).data},
        )

    def perform_update(self, serializer):
        old_data = MedicineSerializer(self.get_object()).data
        medicine = serializer.save()
        _invalidate_medicines_cache(self.request.user.id)
        _log_user_action(
            user=self.request.user,
            action=ActionType.UPDATE,
            details=f"Обновлено лекарство: {medicine.name}",
            payload={'old_data': old_data, 'new_data': MedicineSerializer(medicine).data},
        )

    def perform_destroy(self, instance):
        old_data = MedicineSerializer(instance).data
        med_name = instance.name
        instance.delete()
        _invalidate_medicines_cache(self.request.user.id)
        _log_user_action(
            user=self.request.user,
            action=ActionType.DELETE,
            details=f"Удалено лекарство: {med_name}",
            payload={'old_data': old_data, 'new_data': None},
        )


# 3. REST API для расписаний (добавление времени и смена статуса)
class MedicineScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = MedicineScheduleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MedicineSchedule.objects.filter(medicine__user=self.request.user)

    def perform_update(self, serializer):
        old_status = self.get_object().status
        schedule = serializer.save()
        _invalidate_medicines_cache(self.request.user.id)
        _log_user_action(
            user=self.request.user,
            action=ActionType.STATUS_CHANGE,
            details=f"Смена статуса {schedule.medicine.name} ({schedule.time.strftime('%H:%M')})",
            payload={
                'old_data': {'id': schedule.id, 'status': old_status},
                'new_data': {'id': schedule.id, 'status': schedule.status},
            },
        )

    def perform_destroy(self, instance):
        instance.delete()
        _invalidate_medicines_cache(self.request.user.id)
