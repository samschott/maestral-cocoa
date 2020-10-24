#!/usr/bin/env bash

BUNDLE_PATH="macOS/Maestral/Maestral.app"

echo "# ==== copy over entry-points metadata required by app =========================="

python3 -m pip install --upgrade --no-deps . --target dist
DIST_INFO_PATH=$( find dist -name "maestral_cocoa-*.dist-info" )
DIST_INFO_TARGET_PATH=$( find "$BUNDLE_PATH/Contents/Resources/app/" -name "maestral_cocoa-*.dist-info" )
cp "$DIST_INFO_PATH/entry_points.txt" "$DIST_INFO_TARGET_PATH/entry_points.txt"

echo "# ==== prune py files and replace with pyc ======================================"

# compile all py files
"$BUNDLE_PATH/Contents/Resources/Support/bin/Python3" -OO -m compileall -b "$BUNDLE_PATH" &> /dev/null

# remove all py files
find "$BUNDLE_PATH/Contents" -name "*.py" -delete

# remove all __pycache__ dirs
find "$BUNDLE_PATH/Contents" -name "__pycache__" -prune -exec rm -rf {} \;

echo "# ==== add custom Info.plist entries ============================================"

PLIST_PATH="$BUNDLE_PATH/Contents/Info.plist"

/usr/libexec/PlistBuddy -c "Add :LSUIElement string 1" "$PLIST_PATH"
/usr/libexec/PlistBuddy -c "Add :LSMinimumSystemVersion string 10.13.0" "$PLIST_PATH"
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier string com.samschott.maestral.maestral" "$PLIST_PATH"
/usr/libexec/PlistBuddy -c "Add :NSHumanReadableCopyright string 'Copyright © 2020 Sam Schott. All rights reserved.'" "$PLIST_PATH"
