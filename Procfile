web: gunicorn --worker-tmp-dir /dev/shm --bind 0.0.0.0:$PORT stocksubscription.wsgi
worker: celery -A stocksubscription worker --loglevel=info
beat: celery -A stocksubscription beat --loglevel=info