# EMBArk - the emba enterprise environment <br>


<p align="center">
  <img src="./helpers/embark.svg" alt="" width="250"/>
</p>

- [About](#About)
- [Setup](#Setup)
- [Docker](#Docker)
- [Pipelines](#Pipelines)
- [Logging](#Logging)

## About

*Embark* is being developed to provide the Linux-based firmware analyzer *emba* as a containerized service, to ease 
accessibility to *emba* regardless of system and operating system.

Furthermore *Embark* is improves the data provision by aggregating the various *emba* outputs in a fancy dashboard.

## Setup
1. Change directory to root of the repository i.e `embark`
2. Clone original `emba` repository (`git clone https://github.com/e-m-b-a/emba.git`)
3. Run `cd emba && ./installer.sh -F` to force install all the dependencies on host. This enables functionalities like CVE Search.  
4. Setup docker containers (See [docker instructions](https://github.com/e-m-b-a/embark/blob/main/docker.md))


## Docker

See [docker.md](https://github.com/e-m-b-a/embark/blob/main/docker.md)


## Pipelines

Currently there are two Pipelines running:
* Linter (pycodestyle / pep8)  
To check your conformity with pep8 locally: `pycodestyle . `  
To get further information about the violation run: `pycodestyle --show-source . `  
For further setting see [pycodestyle documentation](https://pycodestyle.pycqa.org/en/latest/intro.html)

* Unit Tests  
Pipeline runs the django test environment: `python manage.py test`  
This invokes all methodes in test classes labeled with ``test_``


## Logging

For logging use pythons logging environment.  
Configuration can be found in `embark/manage.py`  

Example:
```console
logger = logging.getLogger('web')

[...]

logger.info("log message")
```

For further reading see [how to logging](https://docs.python.org/3/howto/logging.html).


You can inspect the emba repository [emba](https://github.com/e-m-b-a/emba) and get more [information about usage of *emba* in the wiki](https://github.com/e-m-b-a/emba/wiki/Usage).

## Sponsor and history
This project was originally sponsored by Siemens Energy as [AMOS project](https://oss.cs.fau.de/teaching/the-amos-project/) in cooperation with the [FAU](https://oss.cs.fau.de/)
See also: https://github.com/amosproj/amos2021ss01-emba-service
