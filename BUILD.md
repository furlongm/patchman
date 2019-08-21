# Build DEB package

```shell
sudo apt -y install python-setuptools debhelper dh-exec dh-python git-buildpackage
find -name *.pyc -exec rm {} \;
rm -fr .tox patchman.egg-info
gbp dch --auto  # modify changelog manually
git add debian/changelog
version=$(cat VERSION.txt)
git commit -m "update debian changelog for ${version}"
git tag ${version}
gbp buildpackage --git-ignore-new --git-force-create -uc -us
```

# Build RPM packages

```shell
sudo yum -y install rpm-build git python-setuptools
python setup.py bdist_rpm
rpmbuild -bb patchman-client.spec
```
