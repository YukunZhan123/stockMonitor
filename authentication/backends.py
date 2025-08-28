from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q


class EmailAuthBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using their email address
    instead of username. This is more user-friendly and common in modern applications.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Try to find user by email first, then by username as fallback
            user = User.objects.get(
                Q(email=username) | Q(username=username)
            )
        except User.DoesNotExist:
            return None
        
        # Check password and return user if valid
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None