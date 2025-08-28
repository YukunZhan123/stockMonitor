from django.db import models

# Using Django's built-in User model with is_staff for admin functionality
# High-level approach:
# - is_staff=True for admin users (can see all subscriptions)
# - is_staff=False for regular users (see only their subscriptions)
# - email field already exists in default User model
