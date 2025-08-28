from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register('', views.StockSubscriptionViewSet, basename='stocksubscription')
router.register('logs', views.NotificationLogViewSet, basename='notificationlog')

urlpatterns = [
    # ViewSet routes (CRUD operations)
    path('', include(router.urls)),
    
    # Additional utility endpoints
    path('stats/', views.subscription_stats, name='subscription-stats'),
]