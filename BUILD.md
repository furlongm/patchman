# Bump version and tag release

```shell
vim VERSION.txt  # modify version
git add VERSION.txt
version=$(<VERSION.txt)
git commit -m "Release v${version}"
git tag v${version}
```

# Build DEB package

```shell
sudo apt -y install python-setuptools debhelper dh-exec dh-python git-buildpackage
gbp dch --commit
gbp buildpackage -uc -us
```

# Build RPM packages

```shell
sudo dnf -y install rpm-build git python3-setuptools
python3 setup.py bdist_rpm
rpmbuild -bb patchman-client.spec
```
