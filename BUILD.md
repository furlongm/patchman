# Build DEB package

```shell
sudo apt install python-setuptools debhelper
find -name *.pyc -exec rm {} \;
rm -fr .tox patchman.egg-info
gbp dch --auto  # modify changelog manually
git add debian/changelog
version=$(cat VERSION.txt)
git commit -m "update debian changelog for ${version}"
git tag ${version}
gbp buildpackage --git-ignore-new --git-force-create -uc -us
```

# Build RPM package

```shell
python setup.py bdist_rpm
```
