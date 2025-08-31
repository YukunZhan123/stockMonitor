from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'', views.StockSubscriptionViewSet, basename='stocksubscription')
router.register(r'logs', views.NotificationLogViewSet, basename='notificationlog')

urlpatterns = [
    # ViewSet routes (CRUD operations)
    path('', include(router.urls)),
    
    # Manual send-now endpoint (workaround for router issue)
    path('<uuid:pk>/send-now/', views.send_now_view, name='subscription-send-now'),
    
    # Additional utility endpoints
    path('trigger-periodic/', views.trigger_periodic_notifications, name='trigger-periodic'),
]