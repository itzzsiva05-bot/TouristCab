from django.urls import path
from . import views

urlpatterns = [
    # Pages
    path('',                views.home,          name='home'),
    path('book/',           views.book_ride,     name='book_ride'),
    path('airport/',        views.airport_taxi,  name='airport_taxi'),
    path('outstation/',     views.outstation,    name='outstation'),
    path('rentals/',        views.rentals,       name='rentals'),
    path('driver-partner/', views.driver_partner,name='driver_partner'),
    path('contact/',        views.contact,       name='contact'),
    path('packages/',       views.packages,      name='packages'),

    # OTP
    path('send-otp/',   views.send_otp,   name='send_otp'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),

    # Booking
    path('submit/',                  views.submit_booking, name='submit_booking'),
    path('status/<int:booking_id>/', views.booking_status, name='booking_status'),

    # Driver accept / reject
    # WhatsApp button-ல் base URL = https://yourdomain.com/bookings/driver-action/
    # dynamic suffix             = "12/accept/?driver_id=3"  ← views.py அனுப்புறது
    path('driver-action/<int:booking_id>/accept/', views.driver_action, {'action': 'accept'}, name='driver_accept'),
    path('driver-action/<int:booking_id>/reject/', views.driver_action, {'action': 'reject'}, name='driver_reject'),

    # Driver location — FIX: "bookings/" prefix நீக்கு (project urls.py already include பண்றது)
    path('driver-location/<int:booking_id>/', views.driver_location, name='driver_location'),
]