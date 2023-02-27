Name: patchman-client
%define version %(cat VERSION.txt)
%define _rpmdir %(pwd)/dist
Version: %{version}
Release: 1
Summary: patchman-client uploads reports to the patchman server
License: GPLv3
URL: http://patchman.openbytes.ie
Source: %{expand:%%(pwd)}
BuildArch: noarch
Requires: curl which coreutils util-linux

%description
patchman-client provides a client that uploads reports to a patchman server

%prep
find . -mindepth 1 -delete
cp -af %{SOURCEURL0}/. .

%install
mkdir -p %{buildroot}/usr/sbin
mkdir -p %{buildroot}/etc/patchman
cp ./client/%{name} %{buildroot}/usr/sbin
cp ./client/%{name}.conf %{buildroot}/etc/patchman

%files
%defattr(755,root,root)
/usr/sbin/patchman-client
%config(noreplace) /etc/patchman/patchman-client.conf

%changelog
