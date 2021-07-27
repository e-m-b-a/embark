# EMBArk - the firmware security scanning enterprise environment <br>


<p align="center">
  <img src="./helpers/embark.svg" alt="" width="250"/>
</p>

## About

*Embark* is being developed to provide the firmware security analyzer *[emba](https://github.com/e-m-b-a/emba)* as a containerized service, to ease 
accessibility to *emba* regardless of system and operating system.

Furthermore *Embark* improves the data provision by aggregating the various scanning results in a nice dashboard.

## Setup
1. Change directory to root of the repository i.e `embark`
2. Clone original `emba` repository (`git clone https://github.com/e-m-b-a/emba.git`)
3. Run `cd emba && ./installer.sh -F` to force install all the dependencies on host. This enables functionalities like CVE Search.  
4. Setup docker containers (See [docker instructions](https://github.com/e-m-b-a/embark/blob/main/docker.md))

You can inspect the emba repository [emba](https://github.com/e-m-b-a/emba) and get more [information about usage of *emba* in the wiki](https://github.com/e-m-b-a/emba/wiki/Usage). Additionally you should check the [embark wiki](https://github.com/e-m-b-a/embark/wiki).

## Sponsor and history
This project was originally sponsored by [Siemens Energy](https://www.siemens-energy.com/) as [AMOS project](https://oss.cs.fau.de/teaching/the-amos-project/) in cooperation with the [FAU](https://oss.cs.fau.de/)

See also: https://github.com/amosproj/amos2021ss01-emba-service
