import logging
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse

from bookings.models import Driver, Booking, Attendance

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────

def driver_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        driver_id = request.session.get("driver_id")
        if not driver_id:
            messages.warning(request, "Please login to continue.")
            return redirect("driver_login")
        driver = Driver.objects.filter(id=driver_id, is_active=True).first()
        if not driver:
            request.session.flush()
            messages.error(request, "Your account is not active. Contact admin.")
            return redirect("driver_login")
        request.driver = driver
        return view_func(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────
# Login / Logout
# ─────────────────────────────────────────────

def driver_login(request):
    if request.session.get("driver_id"):
        return redirect("driver_dashboard")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        driver = Driver.objects.filter(email__iexact=email).first()

        if driver and driver.check_password(password):
            if not driver.is_active:
                messages.error(request, "Your account has been deactivated by admin.")
                return render(request, "driverpanel/login.html")
            request.session["driver_id"] = driver.id
            messages.success(request, f"Welcome back, {driver.name}!")
            return redirect("driver_dashboard")

        messages.error(request, "Invalid email or password.")

    return render(request, "driverpanel/login.html")


def driver_logout(request):
    request.session.flush()
    messages.success(request, "Logged out successfully.")
    return redirect("driver_login")


# ─────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────

@driver_required
def driver_dashboard(request):
    driver = request.driver

    # A ride currently offered to THIS driver, awaiting accept/reject
    pending_ride = Booking.objects.filter(driver=driver, status="waiting").order_by("-created_at").first()

    # A ride this driver has accepted and is currently running (not completed yet)
    active_ride = Booking.objects.filter(driver=driver, status="confirmed").order_by("-created_at").first()

    # Past rides
    history = Booking.objects.filter(driver=driver, status="completed").order_by("-created_at")[:15]

    today_attendance = Attendance.objects.filter(driver=driver, date=timezone.localdate(), check_out__isnull=True).first()

    context = {
        "driver": driver,
        "pending_ride": pending_ride,
        "active_ride": active_ride,
        "history": history,
        "is_punched_in": bool(today_attendance),
    }
    return render(request, "driverpanel/dashboard.html", context)


# ─────────────────────────────────────────────
# Live status ping — lets the dashboard auto-refresh the moment a new
# ride request is offered to this driver, instead of the driver having
# to manually reload the page to see it.
# ─────────────────────────────────────────────

@driver_required
def dashboard_status(request):
    driver = request.driver

    pending_ride = Booking.objects.filter(driver=driver, status="waiting").order_by("-created_at").first()
    active_ride = Booking.objects.filter(driver=driver, status="confirmed").order_by("-created_at").first()

    return JsonResponse({
        "ok": True,
        "pending_ride_id": pending_ride.id if pending_ride else None,
        "active_ride_id": active_ride.id if active_ride else None,
        "is_available": driver.is_available,
    })


# ─────────────────────────────────────────────
# Accept / Reject ride
# ─────────────────────────────────────────────

@driver_required
def accept_ride(request, booking_id):
    driver = request.driver
    booking = get_object_or_404(Booking, id=booking_id, driver=driver, status="waiting")

    booking.status = "confirmed"
    booking.save(update_fields=["status"])

    driver.is_available = False
    driver.save(update_fields=["is_available"])

    try:
        from bookings.views import _notify_customer_confirmed
        _notify_customer_confirmed(booking)
    except Exception:
        logger.exception(f"Customer confirm notify failed for booking #{booking.id}")

    messages.success(request, f"Ride #{booking.id} accepted! Customer location is now visible below.")
    return redirect("driver_dashboard")


@driver_required
def reject_ride(request, booking_id):
    driver = request.driver
    booking = get_object_or_404(Booking, id=booking_id, driver=driver, status="waiting")

    booking.rejected_by.add(driver)
    next_driver = booking.assign_next_driver()

    if next_driver:
        messages.info(request, f"Ride #{booking.id} rejected. Sent to the next available driver.")
    else:
        messages.info(request, f"Ride #{booking.id} rejected. No other driver was available — booking marked as no-driver.")

    return redirect("driver_dashboard")


@driver_required
def complete_ride(request, booking_id):
    driver = request.driver
    booking = get_object_or_404(Booking, id=booking_id, driver=driver, status="confirmed")

    booking.status = "completed"
    booking.save(update_fields=["status"])

    driver.is_available = True
    driver.save(update_fields=["is_available"])

    messages.success(request, f"Ride #{booking.id} marked as completed. Great job!")
    return redirect("driver_dashboard")


# ─────────────────────────────────────────────
# Attendance — punch in / punch out
# ─────────────────────────────────────────────

@driver_required
def toggle_duty(request):
    driver = request.driver
    today = timezone.localdate()

    open_record = Attendance.objects.filter(driver=driver, date=today, check_out__isnull=True).first()

    if open_record:
        open_record.check_out = timezone.now()
        open_record.save(update_fields=["check_out"])
        driver.is_on_duty = False
        driver.is_available = False
        driver.save(update_fields=["is_on_duty", "is_available"])
        messages.success(request, "Punched out. See you next time!")
    else:
        Attendance.objects.create(driver=driver, date=today)
        driver.is_on_duty = True
        driver.is_available = True
        driver.save(update_fields=["is_on_duty", "is_available"])
        messages.success(request, "Punched in. You're now on duty and can receive rides.")

    return redirect("driver_dashboard")


# ─────────────────────────────────────────────
# Live location update (called periodically from dashboard JS)
# ─────────────────────────────────────────────

def update_location(request):
    if request.method != "POST":
        return redirect("driver_dashboard")
    driver_id = request.session.get("driver_id")
    if not driver_id:
        return redirect("driver_login")

    lat = request.POST.get("lat")
    lon = request.POST.get("lon")
    Driver.objects.filter(id=driver_id).update(current_lat=lat or None, current_lon=lon or None)
    from django.http import JsonResponse
    return JsonResponse({"ok": True})
