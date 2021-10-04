# Patchman


## Summary

Patchman is a Django-based patch status monitoring tool for linux systems.
Patchman provides a web interface for monitoring the package updates available
for linux hosts.

[![](https://raw.githubusercontent.com/furlongm/patchman/gh-pages/screenshots/dashboard.png)](https://github.com/furlongm/patchman/tree/gh-pages/screenshots)


## How does Patchman work?

Patchman clients send a list of installed packages and enabled repositories to
the Patchman server. The Patchman server updates its package list for each
repository and determines which hosts require updates, and whether those updates
are normal or security updates. The web interface also gives information on
potential issues, such as installed packages that are not from any repository.

Hosts, packages, repositories and operating systems can all be filtered. For
example, it is possible to find out which hosts have a certain version of a
package installed, and which repository it comes from.

Patchman does not install update packages on hosts, it determines and displays
what updates are available for each host.

`yum`, `apt` and `zypper` plugins can send reports to the Patchman server every
time packages are installed or removed on a host.


## Installation

See [the installation guide](https://github.com/furlongm/patchman/blob/master/INSTALL.md)
for installation options.


## Usage

The web interface contains a dashboard with items that need attention, and
various pages to manipulate hosts, repositories, packages, operating systems and
reports.

To populate the database, simply run the client on some hosts:

```shell
$ patchman-client -s http://patchman.example.org
```

This should provide some initial data to work with.

On the server, the `patchman` command line utility can be used to run certain
maintenance tasks, e.g. processing the reports sent from hosts, downloading
repository update information from the web. Run `patchman -h` for a rundown of
the usage:

```shell
$ sbin/patchman -h
usage: patchman [-h] [-f] [-q] [-r] [-R REPO] [-lr] [-lh] [-u] [-A] [-H HOST]
                [-p] [-c] [-d] [-n] [-a] [-D hostA hostB]

Patchman CLI tool

optional arguments:
  -h, --help            show this help message and exit
  -f, --force           Ignore stored checksums and force-refresh all mirrors
  -q, --quiet           Quiet mode (e.g. for cronjobs)
  -r, --refresh-repos   Refresh repositories
  -R REPO, --repo REPO  Only perform action on a specific repository (repo_id)
  -lr, --list-repos     List all repositories
  -lh, --list-hosts     List all hosts
  -u, --host-updates    Find host updates
  -A, --host-updates-alt
                        Find host updates (alternative algorithm that may be
                        faster when there are many homogeneous hosts)
  -H HOST, --host HOST  Only perform action on a specific host (fqdn)
  -p, --process-reports
                        Process pending reports
  -c, --clean-reports   Remove all but the last three reports
  -d, --dbcheck         Perform some sanity checks and clean unused db entries
  -n, --dns-checks      Perform reverse DNS checks if enabled for that host
  -a, --all             Convenience flag for -r -A -p -c -d -n
  -D hostA hostB, --diff hostA hostB
                        Show differences between two hosts in diff-like output
  -e, --errata          Download CentOS errata from https://cefs.steve-
                        meier.de/
```

## Dependencies

### Server-side dependencies


```
python3-django
python3-django-tagging
python3-django-extensions
python3-django-bootstrap3
python3-djangorestframework
python3-debian
python3-rpm
python3-progressbar
python3-lxml
python3-defusedxml
python3-requests
python3-colorama
python3-magic
python3-humanize
```

The server can optionally make use of celery to asynchronously process the
reports sent by hosts.


### Client-side dependencies

The client-side dependencies are kept to a minimum. `rpm` and `dpkg` are
required to report packages, `yum`, `dnf`, `zypper` and/or `apt` are required
to report repositories. These packages are normally installed by default on
most systems.

deb-based OS's do not always change the kernel version when a kernel update is
installed, so the `update-notifier-common` package can optionally be installed
to enable this functionality. rpm-based OS's can tell if a reboot is required
to install a new kernel by looking at `uname -r` and comparing it to the
highest installed kernel version, so no extra packages are required on those
OS's.


## Concepts

The default settings will be fine for most people but depending on your setup,
there may be some initial work required to logically organise the data sent in
the host reports. The following explanations may help in this case.

There are a number of basic objects - Hosts, Repositories, Packages, Operating
Systems and Reports. There are also Operating System Groups (which are optional)
and Mirrors.

### Host
A Host is a single host, e.g. test01.example.org.

### Operating System
A Host runs an Operating System, e.g. CentOS 7.7, Debian 10.1, Ubuntu 18.04

### Package
A Package is a package that is either installed on a Host, or is available to
download from a Repository mirror, e.g. `strace-4.8-11.el7.x86_64`,
`grub2-tools-2.02-0.34.el7.centos.x86_64`, etc.

### Mirror
A Mirror is a collection of Packages available on the web, e.g. a `yum`, `yast`
or `apt` repo.

### Repository
A Repository is a collection of Mirrors. Typically all the Mirrors will contain
the same Packages. For Red Hat-based Hosts, Repositories automatically link
their Mirrors together. For Debian-based hosts, you may need to link all
Mirrors that form a Repository using the web interface. This may reduce the
time required to find updates. Repositories can be marked as being security or
non-security. This makes most sense with Debian and Ubuntu repositories where
security updates are delivered via security repositories. For CentOS security
updates, see the Erratum section below.

### Report
A Host creates a Report using `patchman-client`. This Report is sent to the
Patchman server. The Report contains the Host's Operating System, and lists
of the installed Packages and enabled Repositories on the Host. The Patchman
server processes and records the list of Packages and Repositories contained in
the Report.

### Operating System Group (optional)
An OSGroup is a collection of OS's. For example, an OSGroup named "Ubuntu 18.04"
would be comprised of the following OS's:

```
Ubuntu 18.04.1
Ubuntu 18.04.2
Ubuntu 18.04.5
```

Likewise, an OSGroup named "CentOS 7" would be made up of the following OS's:

```
CentOS 7.5
CentOS 7.7.1511
```

Repositories can be associated with an OSGroup, or with the Host itself. If the
`use_host_repos variable` is set to True for a Host, then updates are found by
looking only at the Repositories that belong to that Host. This is the default
behaviour and does not require OSGroups to be configured.

If `use_host_repos` is set to False, the update-finding process looks at the
OSGroup that the Host's Operating System is in, and uses the OSGroup's
Repositories to determine the applicable updates. This is useful in environments
where many hosts are homogeneous (e.g. cloud/cluster environments).

### Erratum
Errata for CentOS can be downloaded from https://cefs.steve-meier.de/ .
These errata are parsed and stored in the database. If a PackageUpdate
contains a package that is a security update in the errata, then that update is
marked as being a security update.
