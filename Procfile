web: python -m gunicorn stocksubscription.wsgi:application --worker-tmp-dir /dev/shm --bind 0.0.0.0:$PORT --workers 2
worker: celery -A stocksubscription worker --loglevel=info
beat: celery -A stocksubscription beat --loglevel=info