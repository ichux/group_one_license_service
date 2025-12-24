from django.urls import path

from apps.licenses import views

urlpatterns = [
    path("activate/", views.activate_license, name="license-activate"),
    path("deactivate/", views.deactivate_license, name="license-deactivate"),
    path("status/", views.check_status, name="license-status"),
]
