#!/bin/bash
echo -e "\n$GREEN""$BOLD""Reset docker container & networks""$NC"

docker images
docker container ls -a

if docker images | grep -qE "^embark[[:space:]]*latest"; then
echo -e "\n$GREEN""$BOLD""Found EMBArk docker environment - removing it""$NC"
CONTAINER_ID=$(docker container ls -a | grep -E "embark_embark_1" | awk '{print $1}')
echo -e "$GREEN""$BOLD""Stop EMBArk docker container""$NC"
docker container stop "$CONTAINER_ID"
echo -e "$GREEN""$BOLD""Remove EMBArk docker container""$NC"
docker container rm "$CONTAINER_ID" -f
echo -e "$GREEN""$BOLD""Remove EMBArk docker image""$NC"
docker image rm embark:latest -f
fi

if docker images | grep -qE "^mysql[[:space:]]*latest"; then
echo -e "\n$GREEN""$BOLD""Found mysql docker environment - removing it""$NC"
CONTAINER_ID=$(docker container ls -a | grep -E "embark_db" | awk '{print $1}')
echo -e "$GREEN""$BOLD""Stop mysql docker container""$NC"
docker container stop "$CONTAINER_ID"
echo -e "$GREEN""$BOLD""Remove mysql docker container""$NC"
docker container rm "$CONTAINER_ID" -f
echo -e "$GREEN""$BOLD""Remove mysql docker image""$NC"
docker image rm mysql:latest -f
fi

if docker images | grep -qE "^redis[[:space:]]*5"; then
echo -e "\n$GREEN""$BOLD""Found redis docker environment - removing it""$NC"
CONTAINER_ID=$(docker container ls -a | grep -E "embark_redis" | awk '{print $1}')
echo -e "$GREEN""$BOLD""Stop redis docker container""$NC"
docker container stop "$CONTAINER_ID"
echo -e "$GREEN""$BOLD""Remove redis docker container""$NC"
docker container rm "$CONTAINER_ID" -f
echo -e "$GREEN""$BOLD""Remove redis docker image""$NC"
docker image rm redis:5 -f
fi

#networks

if docker network ls | grep -E "embark_dev"; then
echo -e "\n$GREEN""$BOLD""Found EMBArk_dev network - removing it""$NC"
NET_ID=$(docker network ls | grep -E "embark_dev" | awk '{print $1}')
echo -e "$GREEN""$BOLD""Remove EMBArk_dev network""$NC"
docker network rm "$NET_ID" 
fi

if docker network ls | grep -E "embark_frontend"; then
echo -e "\n$GREEN""$BOLD""Found EMBArk_frontend network - removing it""$NC"
NET_ID=$(docker network ls | grep -E "embark_frontend" | awk '{print $1}')
echo -e "$GREEN""$BOLD""Remove EMBArk_frontend network""$NC"
docker network rm "$NET_ID" 
fi

if docker network ls | grep -E "embark_backend"; then
echo -e "\n$GREEN""$BOLD""Found EMBArk_backend network - removing it""$NC"
NET_ID=$(docker network ls | grep -E "embark_backend" | awk '{print $1}')
echo -e "$GREEN""$BOLD""Remove EMBArk_backend network""$NC"
docker network rm "$NET_ID" 
fi