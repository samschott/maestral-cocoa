import sys
import os
import shutil
import compileall
import subprocess
from pathlib import Path
from importlib.metadata import distribution
from importlib.util import find_spec

BUNDLE_PATH = Path(sys.argv[1])
RESOURCE_PATH = BUNDLE_PATH / "Contents" / "Resources"
APP_PATH = BUNDLE_PATH / "Contents" / "Resources" / "app"
APP_PACKAGES_PATH = BUNDLE_PATH / "Contents" / "Resources" / "app_packages"
LIB_PATH = BUNDLE_PATH / "Contents" / "Resources" / "support" / "python-stdlib"
DIST_INFO_TARGET_PATH = next(APP_PATH.glob("maestral_cocoa-*.dist-info"))

print("# ==== create entry-points metadata required by maestral =======================")
#!/usr/bin/env python3

d = distribution("maestral-cocoa")

with open(DIST_INFO_TARGET_PATH / "entry_points.txt", "w") as f:
    for e in d.entry_points:
        f.write(f"[{e.group}]\n")
        f.write(f"{e.name} = {e.value}\n\n")

print("# ==== copy over cli executable =================================================")

shutil.copy("macOS/maestral-cli", BUNDLE_PATH / "Contents" / "MacOS")

print("# ==== prune unneeded modules ===================================================")

# This performs a hacky version of tree-shaking: We import the main entry points
# of maestral and maestral-cocoa and inspect sys.imports to see which dependencies
# are actually required at runtime. Note that the CLI performs some lazy imports on
# function calls for better performance, those are imported separately as "hidden imports".

check_imports_script = f"""
import sys

# hidden imports
import survey
import Pyro5.svr_threads
import packaging.requirements
import click._textwrap
import click._compat
import click._textwrap
import click._termui_impl

# regular imports
import maestral.__main__
import maestral.main
import maestral.cli.cli_main
import maestral_cocoa.app
import maestral_cocoa.__main__

modules = list(sys.modules.values())
paths  = [m.__file__ for m in modules if hasattr(m, "__file__") and m.__file__  is not None]
for p in paths:
    print(p)
"""

required_paths = subprocess.check_output(
    [sys.executable, "-X", "utf8", "-c", check_imports_script],
    env={
        "PYTHONPATH": f"{LIB_PATH}:{LIB_PATH}/lib-dynload:{APP_PATH}:{APP_PACKAGES_PATH}"
    }
).decode().split("\n")

# clean_required_paths = []
#
# version = f"{sys.version_info.major}.{sys.version_info.minor}"
# sdt_lib = os.path.join(sys.prefix, sys.platlibdir, f"python{version}")
# sdt_lib_so = os.path.join(sys.prefix, sys.platlibdir, f"python{version}/lib-dynload")
#
# for path in required_paths:
#     path = path.replace(sdt_lib, str(LIB_PATH.absolute()))
#     path = path.replace(sdt_lib_so, str(LIB_PATH.absolute() / "lib-dynload"))
#     clean_required_paths.append(path)


for path in APP_PACKAGES_PATH.glob("**/*.py"):
    if str(path.absolute()) not in required_paths:
        print(str(path))
        path.unlink()

for path in LIB_PATH.glob("**/*.py"):
    if str(path.absolute()) not in required_paths:
        print(str(path))
        path.unlink()

for path in LIB_PATH.glob("**/*.so"):
    if str(path.absolute()) not in required_paths:
        print(str(path))
        path.unlink()

print("# ==== prune py files and replace with pyc ======================================")

print("compiling py -> pyc")
compileall.compile_dir(str(RESOURCE_PATH), optimize=2, ddir="", legacy=True)

print("removing py files")
for path in RESOURCE_PATH.glob("**/*.py"):
    path.unlink()

print("removing __pycache__ dirs")
for path in RESOURCE_PATH.glob("**/__pycache__"):
    shutil.rmtree(path)
