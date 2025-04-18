# Bump version and tag release

```shell
vim VERSION.txt  # modify version
git add VERSION.txt
version=$(<VERSION.txt)
git commit -m "Release v${version}"
```

# Build DEB package

```shell
sudo apt -y install python3-setuptools debhelper dh-exec dh-python git-buildpackage
version=$(<VERSION.txt)
gbp dch --commit --new-version=${version}-1 --release --distribution=stable
git tag v${version}
gbp buildpackage -uc -us --git-upstream-tree=main
```

# Build RPM packages

```shell
sudo dnf -y install rpm-build git python3-setuptools
version=$(<VERSION.txt)
git tag v${version}
python3 setup.py bdist_rpm --python=/usr/bin/python3
rpmbuild -bb patchman-client.spec
```
