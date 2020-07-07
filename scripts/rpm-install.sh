#!/bin/sh
#
# This file becomes the install section of the generated spec file.
#

# This is what dist.py normally does.
python3 setup.py install --single-version-externally-managed --root=${RPM_BUILD_ROOT} --record="INSTALLED_FILES"

# Sort the filelist so that directories appear before files. This avoids
# duplicate filename problems on some systems.
touch DIRS
for i in `cat INSTALLED_FILES`; do
  if [ -f ${RPM_BUILD_ROOT}/$i ]; then
    echo $i >>FILES
  fi
  if [ -d ${RPM_BUILD_ROOT}/$i ]; then
    echo %dir $i >>DIRS
  fi
done

cat DIRS > INSTALLED_FILES
sed -e '/\/etc\//s|^|%config(noreplace) |' FILES >>INSTALLED_FILES
