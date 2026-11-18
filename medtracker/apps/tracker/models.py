from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Medicine(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название")
    dose = models.CharField(max_length=50, verbose_name="Дозировка")
    frequency = models.CharField(max_length=255, verbose_name="Частота приема")

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="medicines")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Status(models.TextChoices):
    PLANNED = 'planned', 'Запланировано'
    COMPLETED = 'completed', 'Выполнено'
    OVERDUE = 'overdue', 'Просрочено'

class MedicineSchedule(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='schedules')
    time = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
        verbose_name="Статус"
    )


    class Meta:
        ordering = ['time']

    def __str__(self):
        return f"{self.medicine.name} — {self.time.strftime('%H:%M')} ({self.get_status_display()})"

class ActionType(models.TextChoices):
    CREATE = 'create', 'Добавление лекарства'
    UPDATE = 'update', 'Редактирование лекарства'
    DELETE = 'delete', 'Удаление лекарства'
    STATUS_CHANGE = 'status_change', 'Изменение статуса приема'


class UserActionLog(models.Model):
    user_id = models.IntegerField(verbose_name="ID пользователя")
    username = models.CharField(max_length=150, verbose_name="Имя пользователя")
    action = models.CharField(
        max_length=20,
        choices=ActionType.choices,
        verbose_name="Действие"
    )
    details = models.CharField(max_length=255, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время события")
    data = models.JSONField(default=dict, verbose_name="Данные события")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Лог действия"
        verbose_name_plural = "Логи действий пользователей"

    def __str__(self):
        return f"[{self.created_at.strftime('%d.%m %H:%M')}] {self.username}: {self.get_action_display()}"