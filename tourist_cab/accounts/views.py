import json
import logging

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

from .models import Customer

logger = logging.getLogger(__name__)


@ensure_csrf_cookie
def login_hub(request):
    """The ONE login page: email+password (Admin/Driver, auto-detected)
    plus a Continue with Google button (Customer)."""
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        # 1) Try Admin (Django auth User, is_staff)
        from django.contrib.auth import authenticate, login as auth_login
        user = authenticate(request, username=email, password=password)
        if user and user.is_staff:
            auth_login(request, user)
            return redirect("admin_dashboard")

        # 2) Try Driver
        from bookings.models import Driver
        driver = Driver.objects.filter(email__iexact=email).first()
        if driver and driver.check_password(password):
            if not driver.is_active:
                messages.error(request, "Your driver account has been deactivated by admin.")
            else:
                request.session["driver_id"] = driver.id
                messages.success(request, f"Welcome back, {driver.name}!")
                return redirect("driver_dashboard")
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "accounts/login_hub.html", {
        "google_client_id": getattr(settings, "GOOGLE_CLIENT_ID", ""),
    })


@csrf_exempt
def google_auth_callback(request):
    """Receives the Google ID token from the Sign-In-With-Google JS button,
    verifies it with Google, and creates/logs-in the Customer."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)

    credential = request.POST.get("credential")
    if not credential:
        return JsonResponse({"ok": False, "error": "Missing credential"}, status=400)

    client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
    if not client_id:
        return JsonResponse({"ok": False, "error": "GOOGLE_CLIENT_ID not configured on server (.env)"}, status=500)

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        payload = id_token.verify_oauth2_token(credential, google_requests.Request(), client_id)
    except Exception:
        logger.exception("Google token verification failed")
        return JsonResponse({"ok": False, "error": "Invalid Google token"}, status=400)

    email = payload.get("email")
    if not email:
        return JsonResponse({"ok": False, "error": "Google account has no email"}, status=400)

    customer, _ = Customer.objects.update_or_create(
        google_sub=payload.get("sub"),
        defaults={
            "email": email,
            "name": payload.get("name", email.split("@")[0]),
            "photo_url": payload.get("picture", ""),
        },
    )

    request.session["customer_id"] = customer.id
    request.session["customer_name"] = customer.name
    request.session["customer_email"] = customer.email

    return JsonResponse({"ok": True, "redirect": "/"})


def customer_required(view_func):
    from functools import wraps

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        customer_id = request.session.get("customer_id")
        if not customer_id:
            messages.warning(request, "Please login with Google to view your dashboard.")
            return redirect("login_hub")
        customer = Customer.objects.filter(id=customer_id).first()
        if not customer:
            request.session.pop("customer_id", None)
            return redirect("login_hub")
        request.customer = customer
        return view_func(request, *args, **kwargs)
    return wrapper


@customer_required
def customer_dashboard(request):
    customer = request.customer
    bookings = customer.bookings.all().order_by("-created_at")
    total_spent = sum(
        float(b.total_fare) for b in bookings if b.status == "completed"
    )
    return render(request, "accounts/customer_dashboard.html", {
        "customer": customer,
        "bookings": bookings,
        "total_spent": total_spent,
    })

def customer_logout(request):
    for key in ("customer_id", "customer_name", "customer_email"):
        request.session.pop(key, None)
    messages.success(request, "Logged out.")
    return redirect("home")


# ─────────────────────────────────────────────
# Backward-compat alias — old bookmarks/links to /login/staff/ now land on
# the single combined login page (login_hub handles email+password directly).
# ─────────────────────────────────────────────

def staff_login(request):
    return redirect("login_hub")
