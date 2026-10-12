"""Production entry point (gunicorn):  gunicorn -w 1 --threads 8 -b 0.0.0.0:5000 wsgi:app"""
from app import create_app, init_platform, start_scheduler

app = create_app()
init_platform(app)
start_scheduler(app)
