# from django.urls import path
# from . import views

# app_name = "tracker"

# urlpatterns = [
#     path('', views.medicine_list, name='medicine_list'),
#     path('create/', views.medicine_create, name='medicine_create'),
#     path('<int:pk>/update/', views.medicine_update, name='medicine_update'),
#     path('<int:pk>/delete/', views.medicine_delete, name='medicine_delete'),
# ]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "tracker"

router = DefaultRouter()
router.register(r'api/medicines', views.MedicineViewSet, basename='api-medicines')
router.register(r'api/schedules', views.MedicineScheduleViewSet, basename='api-schedules')

urlpatterns = [
    path('', views.medicine_list, name='medicine_list'),
    path('api/', include(router.urls)),
]