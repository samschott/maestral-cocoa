#!/usr/bin/env bash

set -e

if [ -z "$1" ]; then
    echo "Specify bundle path as first parameter"
    exit 1
fi
BUNDLE_PATH="$1"

echo "# ==== copy over entry-points metadata required by maestral ====================="

echo "creating dist info"
python3 -m pip install --upgrade --no-deps . --target dist 1> /dev/null
DIST_INFO_PATH=$( find dist -name "maestral_cocoa-*.dist-info" )
DIST_INFO_DIRNAME=${DIST_INFO_PATH##*/}
DIST_INFO_TARGET_PATH=$( find "$BUNDLE_PATH/Contents/Resources/app" -name $DIST_INFO_DIRNAME )
echo "copying dist info"
cp "$DIST_INFO_PATH/entry_points.txt" "$DIST_INFO_TARGET_PATH/entry_points.txt"
echo "cleanup"
rm -Rf dist

echo "# ==== copy over cli executable ================================================="

echo "cp maestral-cli"
cp macOS/maestral-cli "$BUNDLE_PATH/Contents/MacOS"

echo "# ==== prune unneeded modules ==================================================="

for PACKAGE in "ply" "pygments" "pyparsing" "setuptools" "commonmark" "core" "cocoa" "gtk" "winforms" "web" "iOS" "android" "dummy"
do
  echo $PACKAGE
  rm -Rf "$BUNDLE_PATH/Contents/Resources/app_packages/$PACKAGE"
done

for MODULE in "unittest" "lib2to3" "pydoc_data" "distutils"
do
  echo $MODULE
  rm -Rf "$BUNDLE_PATH/Contents/Resources/support/python-stdlib/$MODULE"
done

echo "# ==== prune py files and replace with pyc ======================================"

# compile all py files
echo "compiling py -> pyc"
python3 -OO -m compileall -b -d "" "$BUNDLE_PATH" 1> /dev/null

# remove all py files
echo "removing py files"
find "$BUNDLE_PATH/Contents" -name "*.py" ! -name "nslog.py" -delete

# remove all __pycache__ dirs
echo "removing __pycache__ dirs"
find "$BUNDLE_PATH/Contents" -name "__pycache__" -prune -exec rm -rf {} \;
