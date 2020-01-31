# Build DEB package

```shell
sudo apt -y install python-setuptools debhelper dh-exec dh-python git-buildpackage
find -name *.pyc -exec rm {} \;
rm -fr .tox patchman.egg-info
gbp dch --auto  # modify changelog manually
git add debian/changelog
vim VERSION.txt # modify version
git add VERSION.txt
version=$(cat VERSION.txt)
git commit -m "release ${version}"
git tag ${version}
gbp buildpackage --git-ignore-new --git-force-create -uc -us
```

# Build RPM packages

```shell
sudo yum -y install rpm-build git python-setuptools
python setup.py bdist_rpm
rpmbuild -bb patchman-client.spec
```
