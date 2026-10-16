from django.urls import path
from . import views

urlpatterns = [
    path("gate/<int:pk>/", views.gate_pass, name="gate_pass"),
    path("gate/<int:pk>/qr.png", views.cert_qr, name="cert_qr"),
    path("cert/<str:token>/", views.cert, name="cert"),
]
