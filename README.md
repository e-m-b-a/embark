# EMBArk - The firmware security scanning environment <br>


<p align="center">
  <img src="./documentation/embark.svg" alt="" width="250"/>
</p>
<p align="center">
  <a href="https://github.com/e-m-b-a/embark/blob/master/LICENSE"><img src="https://img.shields.io/github/license/e-m-b-a/embark?label=License"></a>
  <a href="https://github.com/e-m-b-a/embark/stargazers"><img src="https://img.shields.io/github/stars/e-m-b-a/embark?label=Stars"></a>
  <a href="https://github.com/e-m-b-a/embark/network/members"><img src="https://img.shields.io/github/forks/e-m-b-a/embark?label=Forks"></a>
</p>

## About

*Embark* is being developed to provide the firmware security analyzer *[emba](https://github.com/e-m-b-a/emba)* as a containerized service and to ease 
accessibility to *emba* regardless of system and operating system.

Furthermore *Embark* improves the data provision by aggregating the various scanning results in a aggregated management dashboard.

## Setup
1. Change directory to root of the repository i.e `embark`
2. Clone original `emba` repository (`git clone https://github.com/e-m-b-a/emba.git`)
3. Run `cd emba && ./installer.sh -F` to force install all the dependencies on host. This enables functionalities like CVE Search.  
4. Setup docker containers (See [build instructions](https://github.com/e-m-b-a/embark/wiki/Build-embark))

You can inspect the [emba](https://github.com/e-m-b-a/emba) repository and get more [information about usage of *emba* in the wiki](https://github.com/e-m-b-a/emba/wiki/Usage). Additionally you should check the [embark wiki](https://github.com/e-m-b-a/embark/wiki).

## Sponsor and history
This project was originally sponsored by [Siemens Energy](https://www.siemens-energy.com/) as [AMOS project](https://oss.cs.fau.de/teaching/the-amos-project/) in cooperation with the [FAU](https://oss.cs.fau.de/).

See also the [emba AMOS project](https://github.com/amosproj/amos2021ss01-emba-service) and [AMOS](https://github.com/amosproj).
