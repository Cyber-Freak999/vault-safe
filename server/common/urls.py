from django.urls import path

from . import views

urlpatterns = [
    path("health", views.HealthView.as_view(), name="health"),
    path("audit", views.AuditLogView.as_view(), name="audit"),
]
