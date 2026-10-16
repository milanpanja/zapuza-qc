from django.urls import path
from . import views

urlpatterns = [
    path("templates/", views.tpl_list, name="tpl_list"),
    path("templates/<int:pk>/release/", views.tpl_release, name="tpl_release"),
    path("scan/", views.scan, name="scan"),
    path("inspection/<int:pk>/", views.inspection, name="inspection"),
    path("queue/", views.queue, name="queue"),
    path("review/<int:pk>/", views.review, name="review"),
    path("mrb/", views.mrb, name="mrb"),
    path("api/sync/", views.sync, name="sync"),
]
