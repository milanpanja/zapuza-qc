from django.urls import path
from . import views

urlpatterns = [
    path("", views.lot_list, name="lot_list"),
    path("new/", views.lot_new, name="lot_new"),
    path("<int:pk>/reject/", views.lot_reject, name="lot_reject"),
    path("<int:pk>/clear/", views.lot_clear, name="lot_clear"),
    path("<int:pk>/label.png", views.lot_label, name="lot_label"),
]
