from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("core.urls")),
    path("plant/", include("plant.urls")),
    path("materials/", include("materials.urls")),
    path("quality/", include("quality.urls")),
    path("production/", include("production.urls")),
    path("dispatch/", include("dispatch.urls")),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
