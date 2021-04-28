
**NOTE: Make sure you have already cloned original `emba` repository in the `emba` directory**

### Building and running containers

Build your image  
`docker-compose build`

Bring your containers up  
`docker-compose up -d`

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
`docker-compose restart`

### Updating environment variables
Todo


### Exec inside the containers

If you want to run something from inside the container like a shell script to analyze some firmware
1. Paste that firmware inside directory `embark`
2. Exec(Enter) into your container with `docker exec -it amos-ss2021-emba-service_emba_1 bash`
3. Run your script.
