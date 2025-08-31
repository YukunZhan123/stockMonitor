from django.urls import path
from . import views

"""
High-level purpose: Define API endpoints for secure authentication
- /register/: Create new user account with httpOnly cookies
- /login/: Authenticate and set secure cookies  
- /logout/: Clear authentication cookies
- /verify/: Check authentication status from cookies
- /refresh/: Refresh tokens using cookies
"""

# Ultra-minimal JWT-only endpoints (no CSRF endpoint needed)
urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify/', views.verify_auth_view, name='verify_auth'),
    path('refresh/', views.refresh_token_view, name='refresh_token'),
]