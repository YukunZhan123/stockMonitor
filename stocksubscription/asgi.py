"""
ASGI config for stocksubscription project.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stocksubscription.settings')

application = get_asgi_application()