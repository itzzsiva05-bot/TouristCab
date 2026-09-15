from django.urls import path
from . import views

urlpatterns = [
    path("login/",  views.driver_login,  name="driver_login"),
    path("logout/", views.driver_logout, name="driver_logout"),
    path("",        views.driver_dashboard, name="driver_dashboard"),
    path("status/", views.dashboard_status, name="driver_dashboard_status"),

    path("ride/<int:booking_id>/accept/",   views.accept_ride,   name="driver_ride_accept"),
    path("ride/<int:booking_id>/reject/",   views.reject_ride,   name="driver_ride_reject"),
    path("ride/<int:booking_id>/complete/", views.complete_ride, name="driver_ride_complete"),

    path("duty/toggle/", views.toggle_duty, name="driver_toggle_duty"),
    path("location/",    views.update_location, name="driver_update_location"),
]
