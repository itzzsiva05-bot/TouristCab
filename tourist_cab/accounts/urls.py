from django.urls import path
from . import views

urlpatterns = [
    path("",                       views.login_hub,            name="login_hub"),
    path("customer/dashboard/",    views.customer_dashboard,   name="customer_dashboard"),
    path("customer/callback/",     views.google_auth_callback, name="google_auth_callback"),
    path("customer/logout/",       views.customer_logout,      name="customer_logout"),
    path("staff/",                 views.staff_login,          name="staff_login"),
]
