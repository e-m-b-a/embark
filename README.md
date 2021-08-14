# EMBArk - The firmware security scanning environment <br>


<p align="center">
  <img src="./documentation/embark.svg" alt="" width="250"/>
</p>
<p align="center">
  <a href="https://github.com/e-m-b-a/embark/blob/master/LICENSE"><img src="https://img.shields.io/github/license/e-m-b-a/embark?label=License"></a>
  <a href="https://img.shields.io/badge/python-3.7+-blue.svg"><img src="https://img.shields.io/badge/python-3.7+-blue.svg"></a>
  <a href="https://github.com/e-m-b-a/embark/stargazers"><img src="https://img.shields.io/github/stars/e-m-b-a/embark?label=Stars"></a>
  <a href="https://github.com/e-m-b-a/embark/network/members"><img src="https://img.shields.io/github/forks/e-m-b-a/embark?label=Forks"></a>
  <a href="https://github.com/e-m-b-a/embark/graphs/contributors"><img src="https://img.shields.io/github/contributors/e-m-b-a/embark?color=9ea"></a>
</p>

## About

*EMBArk* is being developed to provide the firmware security analyzer *[emba](https://github.com/e-m-b-a/emba)* as a containerized service and to ease 
accessibility to *emba* regardless of system and operating system.

Furthermore *EMBArk* improves the data provision by aggregating the various scanning results in a aggregated management dashboard.

## Setup - automated
1. Change directory to root of the repository i.e `embark`
2. Run `sudo ./installer.sh -r` to force install all the dependencies on host. This rebuilds the complete docker environment including a fresh emba installation.
3. Further details are available in the wiki (See [build instructions](https://github.com/e-m-b-a/embark/wiki/Build-Deployment_Documentation))

## Setup - manual
1. Change directory to root of the repository i.e `embark`
2. Clone original `emba` repository (`git clone https://github.com/e-m-b-a/emba.git`)
3. Run `cd emba && sudo ./installer.sh -F` to force install all the dependencies on host. This enables functionalities like CVE Search.  
4. Setup docker containers (See [build instructions](https://github.com/e-m-b-a/embark/wiki/Build-Deployment_Documentation))

You can inspect the [EMBA](https://github.com/e-m-b-a/emba) repository and get more [information about usage of *emba* in the wiki](https://github.com/e-m-b-a/emba/wiki/Usage). Additionally you should check the [EMBArk wiki](https://github.com/e-m-b-a/embark/wiki).

## Get involved
The IoT is growing, the development is ongoing, and there are many new features that we want to add.
We welcome [pull requests](https://github.com/e-m-b-a/embark/pulls) and [issues](https://github.com/e-m-b-a/embark/issues) on GitHub.

## Contact Us
If what you want to tell us something that is not a suitable github issue, feel free to send us an email at <a href="mailto:michael.messner@siemens-energy.com">michael.messner@siemens-energy.com</a> or via <a href="https://twitter.com/s3cur1ty_de">twitter</a>.

## Sponsor and history
This project was originally sponsored by [Siemens Energy](https://www.siemens-energy.com/) as [AMOS project](https://oss.cs.fau.de/teaching/the-amos-project/) in cooperation with the [FAU](https://oss.cs.fau.de/).

See also the [EMBArk AMOS project](https://github.com/amosproj/amos2021ss01-emba-service) and [AMOS](https://github.com/amosproj).
