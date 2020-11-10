#!/usr/bin/env python3

from pathlib import Path
from briefcase.platforms.macOS.xcode import macOSXcodeCreateCommand

command = macOSXcodeCreateCommand(Path.cwd())
command.parse_config("pyproject.toml")
app = command.apps["maestral-cocoa"]

binary_path = command.distribution_path(app)
print(str(binary_path))
