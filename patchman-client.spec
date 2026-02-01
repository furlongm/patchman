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
Requires: curl which coreutils util-linux gawk jq

%define _binary_payload w9.gzdio

%description
patchman-client provides a client that uploads reports to a patchman server

%prep
find . -mindepth 1 -delete
cp -af %{SOURCEURL0}/. .

%install
mkdir -p %{buildroot}%{_sbindir}
mkdir -p %{buildroot}%{_sysconfdir}/patchman
install -m 755 client/%{name} %{buildroot}%{_sbindir}/%{name}
install -m 644 client/%{name}.conf %{buildroot}%{_sysconfdir}/patchman/%{name}.conf

%files
%defattr(-,root,root)
%{_sbindir}/patchman-client
%dir %{_sysconfdir}/patchman
%config(noreplace) %{_sysconfdir}/patchman/patchman-client.conf

%changelog
