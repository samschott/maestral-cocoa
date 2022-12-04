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

print("# ==== create entry-points metadata required by maestral ===============")

d = distribution("maestral-cocoa")

with open(DIST_INFO_TARGET_PATH / "entry_points.txt", "w") as f:
    for e in d.entry_points:
        f.write(f"[{e.group}]\n")
        f.write(f"{e.name} = {e.value}\n\n")

print("# ==== copy over cli executable =========================================")

shutil.copy("macOS/maestral-cli", BUNDLE_PATH / "Contents" / "MacOS")

print("# ==== prune unneeded modules ===========================================")

# This performs a hacky version of tree-shaking: We import the main entry points
# of maestral and maestral-cocoa and inspect sys.imports to see which dependencies
# are actually required at runtime. Note some modules are imported lazily within
# function calls for better performance, or because they are only required from
# an app bundle. Those are imported separately here as "hidden imports".

check_imports_script = f"""
import sys

# hidden imports
import survey
import packaging.requirements
import click._textwrap
import click._compat
import click._textwrap
import click._termui_impl
import Pyro5.svr_threads
import _strptime
import desktop_notifier.macos

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

required_paths = (
    subprocess.check_output(
        [sys.executable, "-X", "utf8", "-c", check_imports_script],
        env={
            "PYTHONPATH": f"{LIB_PATH}:{LIB_PATH}/lib-dynload:{APP_PATH}:{APP_PACKAGES_PATH}"
        },
    )
    .decode()
    .split("\n")
)
required_paths = set(Path(p) for p in required_paths)

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

py_module_paths = set(path.resolve() for path in RESOURCE_PATH.glob("**/*.py"))
binary_module_paths = set(path.resolve() for path in RESOURCE_PATH.glob("**/*.so"))
all_modules = py_module_paths | binary_module_paths
removals = (py_module_paths | binary_module_paths) - set(required_paths)

for path in removals:
    print(f"Removing {path!s}")
    path.unlink()

print("# ==== prune py files and replace with pyc ==============================")

print("compiling py -> pyc")
compileall.compile_dir(str(RESOURCE_PATH), optimize=2, ddir="", legacy=True)

print("removing py files")
for path in RESOURCE_PATH.glob("**/*.py"):
    path.unlink()

print("removing __pycache__ dirs")
for path in RESOURCE_PATH.glob("**/__pycache__"):
    shutil.rmtree(path)