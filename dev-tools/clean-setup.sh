#!/bin/bash
# EMBArk - The firmware security scanning environment
#
# Copyright 2020-2022 Siemens Energy AG
#
# EMBArk comes with ABSOLUTELY NO WARRANTY.
#
# EMBArk is licensed under MIT
#
# Author(s): Benedikt Kuehne

# Description:  Script for cleaning up all docker- container and images

cd "$(dirname "${0}")" || exit 1
cd ..
echo -e "\n${GREEN}""${BOLD}""Reset docker container & networks""${NC}"

docker images
docker container ls -a

while docker images | grep -qE "\<none\>"; do
  IMAGE_ID=$(docker images | grep -E "\<none\>" | awk '{print $3}')
  echo -e "${GREEN}""${BOLD}""Remove failed docker image""${NC}"
  docker image rm "${IMAGE_ID}" -f
done

if docker images | grep -qE "^mysql[[:space:]]*latest"; then
  echo -e "\n${GREEN}""${BOLD}""Found mysql docker environment - removing it""${NC}"
  CONTAINER_ID=$(docker container ls -a | grep -E "embark_db" | awk '{print $1}')
  echo -e "${GREEN}""${BOLD}""Stop mysql docker container""${NC}"
  docker container stop "${CONTAINER_ID}"
  echo -e "${GREEN}""${BOLD}""Remove mysql docker container""${NC}"
  docker container rm "${CONTAINER_ID}" -f
  echo -e "${GREEN}""${BOLD}""Remove mysql docker image""${NC}"
  docker image rm mysql:latest -f
fi

if docker images | grep -qE "^redis[[:space:]]*5"; then
  echo -e "\n${GREEN}""${BOLD}""Found redis docker environment - removing it""${NC}"
  CONTAINER_ID=$(docker container ls -a | grep -E "embark_redis" | awk '{print $1}')
  echo -e "${GREEN}""${BOLD}""Stop redis docker container""${NC}"
  docker container stop "${CONTAINER_ID}"
  echo -e "${GREEN}""${BOLD}""Remove redis docker container""${NC}"
  docker container rm "${CONTAINER_ID}" -f
  echo -e "${GREEN}""${BOLD}""Remove redis docker image""${NC}"
  docker image rm redis:5 -f
fi

#networks

if docker network ls | grep -E "embark_dev"; then
  echo -e "\n${GREEN}""${BOLD}""Found EMBArk_dev network - removing it""${NC}"
  NET_ID=$(docker network ls | grep -E "embark_dev" | awk '{print $1}')
  echo -e "${GREEN}""${BOLD}""Remove EMBArk_dev network""${NC}"
  docker network rm "${NET_ID}" 
fi

if docker network ls | grep -E "embark_frontend"; then
  echo -e "\n${GREEN}""${BOLD}""Found EMBArk_frontend network - removing it""${NC}"
  NET_ID=$(docker network ls | grep -E "embark_frontend" | awk '{print $1}')
  echo -e "${GREEN}""${BOLD}""Remove EMBArk_frontend network""${NC}"
  docker network rm "${NET_ID}" 
fi

if docker network ls | grep -E "embark_backend"; then
  echo -e "\n${GREEN}""${BOLD}""Found EMBArk_backend network - removing it""${NC}"
  NET_ID=$(docker network ls | grep -E "embark_backend" | awk '{print $1}')
  echo -e "${GREEN}""${BOLD}""Remove EMBArk_backend network""${NC}"
  docker network rm "${NET_ID}" 
fi

echo -e "\n${GREEN}""${BOLD}""Clearing Migrations""${NC}"
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc"  -delete

fuser -k 8001/tcp
fuser -k 80/tcp
fuser -k 8080/tcp

docker container prune

echo -e "${ORANGE}""${BOLD}""Consider running \$docker system prune""${NC}"
rm -Rf -I ./embark_db

find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
pipenv run ./embark/manage.py flush
