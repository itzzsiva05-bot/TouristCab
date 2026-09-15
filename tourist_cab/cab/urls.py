from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('bookings.urls')),        # home, book/, etc.
    path('bookings/', include('bookings.urls')), # API: /bookings/submit/ etc.

    # Shared login hub — pick Customer (Google) / Driver / Admin
    path('login/', include('accounts.urls')),

    # Driver mobile-friendly dashboard: login, accept/reject ride, attendance
    path('driver/', include('driverpanel.urls')),

    # Custom staff dashboard: manage drivers, bookings, attendance, salary
    path('dashboard/', include('adminpanel.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)