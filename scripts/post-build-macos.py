import sys
import shutil
import compileall
import subprocess
from pathlib import Path
from setuptools.dist import Distribution
from setuptools.command.egg_info import write_entries

BUNDLE_PATH = Path(sys.argv[1])
RESOURCE_PATH = BUNDLE_PATH / "Contents" / "Resources"
APP_PATH = BUNDLE_PATH / "Contents" / "Resources" / "app"
APP_PACKAGES_PATH = BUNDLE_PATH / "Contents" / "Resources" / "app_packages"
LIB_PATH = BUNDLE_PATH / "Contents" / "Resources" / "support" / "python-stdlib"
DIST_INFO_TARGET_PATH = next(APP_PATH.glob("maestral_cocoa-*.dist-info"))

print("# ==== create entry-points metadata required by maestral ===============")

d = Distribution()
d.parse_config_files(["setup.cfg"])
cmd = d.get_command_obj("egg_info")
write_entries(cmd, "entry_points", DIST_INFO_TARGET_PATH / "entry_points.txt")

print("# ==== copy over cli executable =========================================")

shutil.copy("scripts/maestral-cli", BUNDLE_PATH / "Contents" / "MacOS")

print("# ==== prune py files and replace with pyc ==============================")

print("compiling py -> pyc")
compileall.compile_dir(str(RESOURCE_PATH), optimize=2, ddir="", legacy=True)

print("removing py files")
for path in RESOURCE_PATH.glob("**/*.py"):
    path.unlink()

print("removing __pycache__ dirs")
for path in RESOURCE_PATH.glob("**/__pycache__"):
    shutil.rmtree(path)
