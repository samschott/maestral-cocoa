import shutil
import compileall
import subprocess
import argparse
from pathlib import Path
from setuptools.dist import Distribution
from setuptools.command.egg_info import write_entries

parser = argparse.ArgumentParser()
parser.add_argument("bundlepath")
parser.add_argument("-i", "--identity", help="code signing identity")
parser.add_argument("-e", "--entitlements", help="code signing entitlements")

args = parser.parse_args()

BUNDLE_PATH = Path(args.bundlepath)
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

cli_executable_path = BUNDLE_PATH / "Contents" / "MacOS" / "maestral-cli"
shutil.copy("scripts/maestral-cli", cli_executable_path)

print("# ==== sign cli executable ==============================================")

subprocess.run(
    [
        "codesign",
        str(cli_executable_path),
        "--sign",
        args.identity,
        "--force",
        "--entitlements",
        args.entitlements,
        "--options",
        "runtime",
    ],
    check=True,
)

print("# ==== prune py files and replace with pyc ==============================")

print("compiling py -> pyc")
compileall.compile_dir(str(RESOURCE_PATH), optimize=2, ddir="", legacy=True)

print("removing py files")
for path in RESOURCE_PATH.glob("**/*.py"):
    path.unlink()

print("removing __pycache__ dirs")
for path in RESOURCE_PATH.glob("**/__pycache__"):
    shutil.rmtree(path)
