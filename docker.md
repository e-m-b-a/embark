
**NOTE: Make sure you have already cloned original `emba` repository in the `emba` directory**

**NOTE: If you are using docker desktop on a Mac or windows machine. Remove line `network_mode: host` from docker-compose.yml**

**NOTE: If you are using docker desktop windows machine. The database host inside env would be `host.docker.internal`**

**NOTE: For now our compose file is compatible with docker-compose version `1.27.x`. `1.28.x` and `1.29.x` are already available and by default you will end up with latest version unless you specify explicitly while installing. Please install version`1.27.x` untill we fix this**


### Updating environment variables
Refer to `template.env`, you will see the following env variables
```                                                                                                                                                                        1,1           All
1. DATABASE_NAME: Name of the sql database
2. DATABASE_USER: User of the database
3. DATABASE_PASSWORD: For for logging in to the database
4. DATABASE_HOST: Host for MySQL database
5. DATABASE_PORT: Port for MySQL database
6. MYSQL_ROOT_PASSWORD: Root password to connect to mysql server
7. MYSQL_DATABASE: Database that gets created on container startup. Same as DATABASE_NAME
8. REDIS_HOST: Host for Redis DB
9. REDIS_PORT: Port for Redis DB
``` 

We are not maintaining a central copy for now. Till then please main your own copy wherever you setup your dev environment.





### Building and running containers

1. Build your image  
`docker-compose build`
   
2. Before bringing your containers up rename `template.env -> .env` and edit `.env` file should to look like:
```
DATABASE_NAME=<Name you are going to give your db>
DATABASE_USER=root
DATABASE_PASSWORD=<value of MYSQL_ROOT_PASSWORD>
DATABASE_HOST=0.0.0.0(or host.docker.internal for windows or MacOs)
DATABASE_PORT=3306
REDIS_HOST=0.0.0.0(or host.docker.internal for windows or MacOs)
REDIS_PORT=6379
MYSQL_ROOT_PASSWORD=<This should be set>
MYSQL_DATABASE=<Same as DATABASE_NAME>
```

3. Bring your containers up  
`docker-compose up -d`
   
### Run migrations
To run migrations for any changes in django db models
```
python3 manage.py makemigrations uploader users
python3 manage.py migrate
```



### Testing Django setup

Test if django application (uWSGI workers) came up  
`curl -XGET 'http://0.0.0.0:8000'`  
You should get a response like this:
```<!-- Base Template for home page-->
<!DOCTYPE html>
<html>
<head>
    <title></title>
</head>
<body>
    <h1>EMBArk home!</h1>
</body>
```

### Updating code
Whenever you change any code in `embark`(django project). You will have to make it live. Since all our code is mounted through compose.
Developers just need to run the following command -  
`docker-compose restart emba`


### Exec inside the containers

If you want to run something from inside the container like a shell script to analyze some firmware
1. Paste that firmware inside directory `embark`
2. Exec(Enter) into your container with `docker exec -it amos-ss2021-emba-service_emba_1 bash`
3. Run your script.
