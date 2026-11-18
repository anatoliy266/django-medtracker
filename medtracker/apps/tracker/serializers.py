from rest_framework import serializers
from .models import *

class MedicineScheduleSerializer(serializers.ModelSerializer):
    time = serializers.TimeField(format='%H:%M', input_formats=['%H:%M'])
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = MedicineSchedule
        fields = ['id', 'medicine', 'time', 'status', 'status_display']
        read_only_fields = ['id', 'status_display']

    def validate_medicine(self, medicine):
        request = self.context.get('request')
        if request and medicine.user != request.user:
            raise serializers.ValidationError("Нельзя добавить расписание к чужому лекарству.")
        return medicine


class MedicineSerializer(serializers.ModelSerializer):
    # Только для чтения подтягиваем список расписаний этого лекарства
    schedules = MedicineScheduleSerializer(many=True, read_only=True)
    frequency = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')

    class Meta:
        model = Medicine
        fields = ['id', 'name', 'dose', 'frequency', 'created_at', 'schedules']
        read_only_fields = ['id', 'created_at']