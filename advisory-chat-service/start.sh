#!/bin/bash
set -e

# Enable pgvector extension
python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'advisory_chat_service.settings')
django.setup()
from django.db import connection
cursor = connection.cursor()
cursor.execute('CREATE EXTENSION IF NOT EXISTS vector')
print('pgvector extension enabled')
"

# Run migrations
python manage.py makemigrations app
python manage.py migrate

# Start server
python manage.py runserver 0.0.0.0:8000
