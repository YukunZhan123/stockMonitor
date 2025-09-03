"""stocksubscription URL Configuration"""
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# API endpoints only (admin removed)
urlpatterns = [
    path('api/auth/', include('authentication.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)