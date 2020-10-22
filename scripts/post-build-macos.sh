#!/usr/bin/env bash

BUNDLE_PATH="macOS/Maestral/Maestral.app"

echo "# ==== copy over CLI executable ================================================="

cp bin/maestral_cli "$BUNDLE_PATH/Contents/MacOS/maestral_cli"
chmod +x "$BUNDLE_PATH/Contents/MacOS/maestral_cli"

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
