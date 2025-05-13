#!/bin/bash

# Exit on any error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Run Django migrations
python manage.py migrate

# Collect static files without prompting
python manage.py collectstatic --noinput
