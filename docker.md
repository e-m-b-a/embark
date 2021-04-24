##How to:

Build your image  
`docker-compose build`

Bring your containers up  
`docker-compose up -d`


Test if django came up  
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


If you want to run something from inside the container like a shell script to analyze some firmware
1. Paste that firmware inside directory `embark`
2. Exec(Enter) into your container with `docker exec -it amos-ss2021-emba-service_emba_1 bash`
3. Run your script.
