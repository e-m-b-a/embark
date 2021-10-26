#!/bin/bash
# setup .env for dev bridge-network
DJANGO_SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
echo -e "$ORANGE""$BOLD""Creating a Developer EMBArk configuration file .env""$NC"
{
  echo "DATABASE_NAME=embark"
  echo "DATABASE_USER=root" 
  echo "DATABASE_PASSWORD=embark"
  echo "DATABASE_HOST=172.20.0.5"
  echo "DATABASE_PORT=3306"
  echo "MYSQL_ROOT_PASSWORD=embark"
  echo "MYSQL_DATABASE=embark"
  echo "REDIS_HOST=172.20.0.8"
  echo "REDIS_PORT=7777"
  echo "SECRET_KEY=$DJANGO_SECRET_KEY"
} >> .env

# setup backend-container and detach
echo -e "\n$GREEN""$BOLD""Building EMBArk docker images""$NC"
docker-compose -f docker-compose-dev.yml build
DB_RETURN=$?
if [[ $DB_RETURN -eq 0 ]] ; then
  echo -e "$GREEN""$BOLD""Finished building EMBArk docker images""$NC"
else
  echo -e "$ORANGE""$BOLD""Failed building EMBArk docker images""$NC"
fi

echo -e "\n$GREEN""$BOLD""Setup mysql and redis docker images""$NC"
docker-compose up -d
DU_RETURN=$?
if [[ $DU_RETURN -eq 0 ]] ; then
  echo -e "$GREEN""$BOLD""Finished setup mysql and redis docker images""$NC"
else
  echo -e "$ORANGE""$BOLD""Failed setup mysql and redis docker images""$NC"
fi