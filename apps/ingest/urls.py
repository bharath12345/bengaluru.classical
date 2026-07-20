from django.urls import path

from apps.ingest import views

app_name = "ingest"

urlpatterns = [
    path("email/", views.inbound_email, name="inbound_email"),
]
