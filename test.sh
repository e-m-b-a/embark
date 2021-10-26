#!/bin/bash
DJANGO_SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
echo -e "$ORANGE""$BOLD""Creating a default EMBArk configuration file .env""$NC"
{
    echo "DATABASE_NAME=embark"
    echo "DATABASE_USER=root"
    echo "DATABASE_PASSWORD=embark"
    echo "DATABASE_HOST=172.21.0.5"
    echo "DATABASE_PORT=3306"
    echo "MYSQL_ROOT_PASSWORD=embark"
    echo "MYSQL_DATABASE=embark"
    echo "REDIS_HOST=172.21.0.8"
    echo "REDIS_PORT=7777"
    echo "SECRET_KEY=$DJANGO_SECRET_KEY"
} >> .env