# Offline worker configuration

As the offline worker has no internet access, dependencies have to be fetched on the host first.

The dependencies are:
- EMBA source code
- Docker package incl. dependencies (e.g. `iptables`)
- Docker compose package
- `inotify` package
- Exported EMBA docker image (`embeddedanalyzer/emba`)
- External data (NVD Json data feeds, EPSS data)

Note: While EMBA uses a virtual environment for execution, no additional python packages are needed. Thus, the virutal environment is faked to minimize dependencies. To send desktop notifications, the dependency `libnotify-bin` would be needed. However, as this is not required for a worker node, the dependency is mocked.

# Dependencies: Kali latest example

Using a Kali linux minimal installation, the required dependencies are:

```sh
+- emba.tar.gz                    # EMBA source code
+- pkg/
|  +- libip4.deb                  # libip4tc2 package
|  +- libip6.deb                  # libip6tc2 package
|  +- libnetfilter.deb            # libnetfilter-conntrack3 package
|  +- libnfnetlink.deb            # libnfnetlink0 package
|  +- iptables.db                 # iptables package
|  +- containered.deb             # containerd.io package
|  +- docker-buildx-plugin.deb
|  +- docker-ce-cli.deb
|  +- docker-ce.deb
|  +- docker-compose-plugin.deb
|  +- inotify.deb                 # inotify-tools package
|  +- libinotify.deb              # libinotifytools0 package
+- emba-docker-image.tar
+- external/
|  +- nvd-json-data-feeds
|  +- EPSS-data
+- emba_venv
   +- bin/
      +- activate                 # empty file, fakes unused virtual environment
```

An automated example, which fetches the dependencies, can be found in `./examples/setup_worker/host.sh`.

# Automated installation

Once all dependencies are fetched, the installer can be executed (Example in `./examples/setup_worker/installer.sh`). It installs all the provided dependencies, and creates files where needed.

The result is a working EMBA installation in `/root/emba`, ready for use.

If the installation should be removed, an example of an uninstaller can be found in `./examples/setup_worker/uninstaller.sh`.

# Testing EMBA

An exemplary invocation of EMBA by EMBArk can be found in `./examples/setup_worker/run_emba_test.sh`.

