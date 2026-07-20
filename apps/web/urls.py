from django.urls import path

from apps.web import feeds, views

app_name = "web"

urlpatterns = [
    path("health/", views.health, name="health"),
    path("", views.event_list, name="event_list"),
    path("events/", views.event_list),
    path("events/<slug:slug>/", views.event_detail, name="event_detail"),
    path("calendar/", views.calendar_view, name="calendar"),
    path("calendar.ics", feeds.ics_feed, name="ics_feed"),
    path("archive/", views.archive_view, name="archive"),
    path("festivals/<slug:slug>/", views.series_detail, name="series_detail"),
]
