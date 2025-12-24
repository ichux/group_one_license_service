from django.urls import path

from apps.licenses import views

urlpatterns = [
    path(
        "<uuid:brand_id>/license-keys/",
        views.create_license_key,
        name="brand-license-keys-create",
    ),
    path(
        "<uuid:brand_id>/license-keys/<str:key>/",
        views.get_license_key,
        name="brand-license-keys-detail",
    ),
    path(
        "<uuid:brand_id>/license-keys/<str:key>/licenses/",
        views.add_license,
        name="brand-license-keys-add-license",
    ),
]
