from django.urls import path
from . import views

urlpatterns = [
    path("login/",  views.admin_login,  name="admin_login"),
    path("logout/", views.admin_logout, name="admin_logout"),
    path("",         views.dashboard,   name="admin_dashboard"),

    path("drivers/",                       views.driver_list,          name="admin_driver_list"),
    path("drivers/add/",                   views.driver_add,           name="admin_driver_add"),
    path("drivers/<int:driver_id>/edit/",  views.driver_edit,          name="admin_driver_edit"),
    path("drivers/<int:driver_id>/toggle/",views.driver_toggle_active, name="admin_driver_toggle"),

    path("bookings/",                              views.booking_list,          name="admin_booking_list"),
    path("bookings/<int:booking_id>/skip/",         views.booking_skip_to_next,  name="admin_booking_skip"),
    path("bookings/<int:booking_id>/assign/",       views.booking_force_assign,  name="admin_booking_assign"),
    path("bookings/<int:booking_id>/cancel/",       views.booking_cancel,        name="admin_booking_cancel"),

    path("attendance/", views.attendance_report, name="admin_attendance"),
    path("salary/",     views.salary_report,     name="admin_salary"),
]
