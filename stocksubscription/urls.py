"""stocksubscription URL Configuration - Ultra-minimal JWT-only setup"""
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# No Django admin - using custom React admin interface at /admin
urlpatterns = [
    path('api/auth/', include('authentication.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)