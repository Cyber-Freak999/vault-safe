from django.urls import path

from . import views

urlpatterns = [
    path("auth/register", views.RegisterView.as_view(), name="register"),
    path("auth/preauth", views.PreauthView.as_view(), name="preauth"),
]
