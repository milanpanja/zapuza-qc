from django.urls import path
from . import views

urlpatterns = [
    path("machines/", views.machine_list, name="machine_list"),
    path("machines/<int:pk>/pm/", views.machine_pm, name="machine_pm"),
    path("machines/<int:pk>/qr.png", views.machine_qr, name="machine_qr"),
]
