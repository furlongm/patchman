find -name *.pyc -exec rm {} \;
rm -fr .tox
rm -fr patchman.egg-info
gbp dch --auto
git tag `cat VERSION.txt`
gbp buildpackage --git-ignore-new --git-force-create
