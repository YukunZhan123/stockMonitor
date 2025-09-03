from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'', views.StockSubscriptionViewSet, basename='stocksubscription')
router.register(r'logs', views.NotificationLogViewSet, basename='notificationlog')

urlpatterns = [
    # ViewSet routes (CRUD operations and actions)
    path('', include(router.urls)),
    
    # Webhook endpoint (no authentication required)
    path('webhook/trigger-notifications/', views.trigger_notifications_webhook, name='trigger-webhook'),
]