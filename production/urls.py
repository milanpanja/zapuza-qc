from django.urls import path
from . import views

urlpatterns = [
    path("", views.trav_list, name="trav_list"),
    path("<int:pk>/", views.trav_detail, name="trav_detail"),
    path("<int:pk>/qr.png", views.trav_qr, name="trav_qr"),
    path("op/<int:pk>/start/", views.op_start, name="op_start"),
    path("op/<int:pk>/finish/", views.op_finish, name="op_finish"),
    path("run/<int:pk>/", views.run_detail, name="run_detail"),
    path("handover/", views.handover_list, name="handover_list"),
    path("handover/new/", views.handover_new, name="handover_new"),
    path("handover/<int:pk>/ack/", views.handover_ack, name="handover_ack"),
    path("bottlenecks/", views.bottlenecks, name="bottlenecks"),
]
