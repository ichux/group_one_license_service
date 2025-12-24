from django.urls import path

from apps.licenses import views

urlpatterns = [
    path("licenses/by-email/", views.list_by_email, name="admin-licenses-by-email"),
]
