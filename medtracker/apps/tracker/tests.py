from datetime import time
from unittest.mock import patch
from django.test import SimpleTestCase
from django.urls import reverse
from django.db import connections
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from settings.db_router import LogsRouter
from apps.tracker.models import (
    Medicine,
    MedicineSchedule,
    Status,
    UserActionLog,
    ActionType,
)


# ==========================================
# 1. UNIT-ТЕСТЫ (изолированная логика, без БД)
# ==========================================
class LogsRouterUnitTests(SimpleTestCase):
    def setUp(self):
        self.router = LogsRouter()

    def test_routing_for_user_action_log(self):
        self.assertEqual(self.router.db_for_read(UserActionLog), 'logs')
        self.assertEqual(self.router.db_for_write(UserActionLog), 'logs')
        self.assertTrue(self.router.allow_migrate('logs', 'tracker', model_name='useractionlog'))
        self.assertFalse(self.router.allow_migrate('default', 'tracker', model_name='useractionlog'))

    def test_routing_for_other_models(self):
        self.assertEqual(self.router.db_for_read(Medicine), 'default')
        self.assertEqual(self.router.db_for_write(Medicine), 'default')
        self.assertTrue(self.router.allow_migrate('default', 'tracker', model_name='medicine'))
        self.assertFalse(self.router.allow_migrate('logs', 'tracker', model_name='medicine'))


# ==========================================
# 2. ИНТЕГРАЦИОННЫЕ ТЕСТЫ REST API + КЭШ + 2 БД
# ==========================================
class TrackerRESTIntegrationTests(APITestCase):
    databases = {'default', 'logs'}

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='alice', password='StrongPassword123!')
        self.other_user = User.objects.create_user(username='bob', password='StrongPassword123!')
        self.client.force_login(self.user)

        self.page_url = reverse('tracker:medicine_list')
        self.medicines_list_url = reverse('tracker:api-medicines-list')
        self.schedules_list_url = reverse('tracker:api-schedules-list')

    def test_create_medicine_and_schedule_via_rest_api(self):
        """POST /api/medicines/ и POST /api/schedules/ возвращают 201 и пишут в 2 БД"""
        # 1. Создаем лекарство
        med_resp = self.client.post(
            self.medicines_list_url,
            data={'name': 'Витамин D3', 'dose': '2000 МЕ', 'frequency': ''},
            format='json',
        )
        self.assertEqual(med_resp.status_code, status.HTTP_201_CREATED)
        med_id = med_resp.data['id']

        # 2. Добавляем к нему время приема
        sched_resp = self.client.post(
            self.schedules_list_url,
            data={'medicine': med_id, 'time': '09:00'},
            format='json',
        )
        self.assertEqual(sched_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(sched_resp.data['time'], '09:00')

        # Проверяем БД default и БД logs
        self.assertEqual(Medicine.objects.using('default').count(), 1)
        self.assertEqual(MedicineSchedule.objects.using('default').count(), 1)
        self.assertEqual(UserActionLog.objects.using('logs').count(), 1)
        self.assertNotIn('tracker_useractionlog', connections['default'].introspection.table_names())

    def test_validation_returns_400_bad_request(self):
        """Пустые поля или кривое время отдают 400 Bad Request, а не 200 или 500"""
        bad_med = self.client.post(
            self.medicines_list_url,
            data={'name': '   ', 'dose': ''},
            format='json',
        )
        self.assertEqual(bad_med.status_code, status.HTTP_400_BAD_REQUEST)

        med = Medicine.objects.create(user=self.user, name='Магний', dose='500 мг', frequency='')
        bad_time = self.client.post(
            self.schedules_list_url,
            data={'medicine': med.id, 'time': '99:99'},
            format='json',
        )
        self.assertEqual(bad_time.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_medicine_and_audit_diff(self):
        """PATCH /api/medicines/{id}/ обновляет запись (200) и пишет dict в JSONField лога"""
        med = Medicine.objects.create(user=self.user, name='Аспирин', dose='100 мг', frequency='Утром')
        detail_url = reverse('tracker:api-medicines-detail', args=[med.id])

        resp = self.client.patch(
            detail_url,
            data={'name': 'Аспирин Кардио', 'dose': '150 мг'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        med.refresh_from_db()
        self.assertEqual(med.name, 'Аспирин Кардио')

        log = UserActionLog.objects.using('logs').first()
        self.assertEqual(log.action, ActionType.UPDATE)
        self.assertEqual(log.data['old_data']['name'], 'Аспирин')
        self.assertEqual(log.data['new_data']['name'], 'Аспирин Кардио')

    def test_patch_schedule_status(self):
        """PATCH /api/schedules/{id}/ меняет статус приема"""
        med = Medicine.objects.create(user=self.user, name='Омега-3', dose='1 капс', frequency='')
        sched = MedicineSchedule.objects.create(medicine=med, time=time(10, 0))
        sched_url = reverse('tracker:api-schedules-detail', args=[sched.id])

        resp = self.client.patch(sched_url, data={'status': Status.COMPLETED}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], Status.COMPLETED)

        sched.refresh_from_db()
        self.assertEqual(sched.status, Status.COMPLETED)

    def test_delete_medicine_returns_204(self):
        """DELETE /api/medicines/{id}/ удаляет запись и возвращает 204 No Content"""
        med = Medicine.objects.create(user=self.user, name='Удаляемое', dose='10 мг', frequency='Раз в день')
        detail_url = reverse('tracker:api-medicines-detail', args=[med.id])

        resp = self.client.delete(detail_url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Medicine.objects.count(), 0)
        self.assertEqual(UserActionLog.objects.using('logs').first().action, ActionType.DELETE)

    def test_user_isolation(self):
        """Нельзя получить, удалить или привязать расписание к чужому лекарству"""
        other_med = Medicine.objects.create(user=self.other_user, name='Чужое', dose='10 мг', frequency='Раз в день')
        other_detail_url = reverse('tracker:api-medicines-detail', args=[other_med.id])

        self.assertEqual(self.client.get(other_detail_url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(other_detail_url).status_code, status.HTTP_404_NOT_FOUND)

        # Попытка привязать свое расписание к чужому лекарству -> 400
        bad_attach = self.client.post(
            self.schedules_list_url,
            data={'medicine': other_med.id, 'time': '12:00'},
            format='json',
        )
        self.assertEqual(bad_attach.status_code, status.HTTP_400_BAD_REQUEST)

    def test_redis_caching_and_invalidation(self):
        """Повторный GET /tracker/ берет данные из кэша без SQL-запросов, а мутация сбрасывает кэш"""
        Medicine.objects.create(user=self.user, name='Кэш-тест', dose='1 таб', frequency='Утром')

        # 1-й запрос: прогревает кэш (идет в БД)
        resp1 = self.client.get(self.page_url)
        self.assertEqual(resp1.status_code, 200)

        # 2-й запрос: только 2 системных запроса middleware (session + auth_user), 0 запросов к таблицам лекарств
        with self.assertNumQueries(2):
            resp2 = self.client.get(self.page_url)
            self.assertEqual(resp2.status_code, 200)

        # Мутация через API сбрасывает кэш
        self.client.post(
            self.medicines_list_url,
            data={'name': 'Новое', 'dose': '2 таб', 'frequency': 'Вечером'},
            format='json',
        )
        self.assertIsNone(cache.get(f"medicines:user:{self.user.id}"))

    @patch('apps.tracker.views.UserActionLog.objects.create', side_effect=Exception('DB logs down'))
    def test_graceful_degradation_when_log_db_fails(self, mock_log):
        """Если БД логов упала, создание лекарства всё равно проходит (201 Created)"""
        resp = self.client.post(
            self.medicines_list_url,
            data={'name': 'Отказоустойчивое', 'dose': '100 мг', 'frequency': 'Днем'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Medicine.objects.count(), 1)