#!/usr/bin/env bash

BUNDLE_PATH="macOS/Maestral/Maestral.app"

echo "# ==== copy over CLI executable ================================================="

cp bin/maestral_cli "$BUNDLE_PATH/Contents/MacOS/maestral_cli"
chmod +x "$BUNDLE_PATH/Contents/MacOS/maestral_cli"

echo "# ==== prune py files and replace with pyc ======================================"

# compile all py files
"$BUNDLE_PATH/Contents/Resources/Support/bin/Python3" -OO -m compileall -b "$BUNDLE_PATH"

# remove all py files
find "$BUNDLE_PATH/Contents" -name "*.py" -delete

# remove all __pycache__ dirs
find "$BUNDLE_PATH/Contents" -name "__pycache__" -prune -exec rm -rf {} \;
