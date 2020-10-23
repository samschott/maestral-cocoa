# -*- coding: utf-8 -*-

# system imports
import sys
import os
import os.path as osp
import shutil
import platform
from pathlib import Path
from typing import Optional

try:
    from importlib.metadata import files, PackageNotFoundError  # type: ignore
except ImportError:  # Python 3.7 and lower
    from importlib_metadata import files, PackageNotFoundError  # type: ignore

# external imports
from maestral.utils.autostart import (
    AutoStartBase,
    AutoStartLaunchd,
    AutoStartXDGDesktop,
    SupportedImplementations,
)
from maestral.constants import BUNDLE_ID

# local imports
from .constants import FROZEN


class AutoStart:
    """Creates auto-start files in the appropriate system location to automatically
    start Maestral when the user logs in. Supports launchd on macOS and XDG dekstop
    entries on Linux."""

    _impl: AutoStartBase

    def __init__(self, config_name: str) -> None:

        self.maestral_path = self.get_maestral_command_path()
        self.implementation = self._get_available_implementation()

        start_cmd = f"{self.maestral_path} gui -c {config_name}"
        bundle_id = "{}.{}".format(BUNDLE_ID, config_name)

        if self.implementation == SupportedImplementations.launchd:
            self._impl = AutoStartLaunchd(bundle_id, start_cmd)

        elif self.implementation == SupportedImplementations.xdg_desktop:
            self._impl = AutoStartXDGDesktop(
                filename=f"maestral-{config_name}.desktop",
                app_name="Maestral",
                start_cmd=start_cmd,
                TryExec=self.maestral_path,
                Icon="maestral",
                Terminal="false",
                Categories="Network;FileTransfer;",
                GenericName="File Synchronizer",
                Comment="Sync your files with Dropbox",
            )
        else:
            self._impl = AutoStartBase()

    @property
    def enabled(self) -> bool:
        """True if autostart is enabled."""
        return self._impl.enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        if value:
            self.enable()
        else:
            self.disable()

    def toggle(self) -> None:
        """Toggles autostart on or off."""
        if self.enabled:
            self.disable()
        else:
            self.enable()

    def enable(self) -> None:
        """Setter: True if autostart is enabled."""

        if self.enabled:
            return

        if self.maestral_path:
            self._impl.enable()
        else:
            raise OSError("Could not find path of maestral executable")

    def disable(self) -> None:
        """Setter: True if autostart is enabled."""

        if not self.enabled:
            return

        self._impl.disable()

    def get_maestral_command_path(self) -> str:
        """
        :returns: The path to the maestral executable. May be an empty string if the
            executable cannot be found.
        """

        if FROZEN:
            return sys.executable

        try:
            dist_files = files("maestral")
        except PackageNotFoundError:
            # we may be in an app bundle or have installation issues
            dist_files = []

        path: Optional[os.PathLike]

        if dist_files:
            try:
                rel_path = next(p for p in dist_files if p.match("**/bin/maestral"))
                path = rel_path.locate()
            except StopIteration:
                path = None
        else:
            path = None

        if isinstance(path, Path):
            # resolve any symlinks and “..” components
            path = path.resolve()

        if path and osp.isfile(path):
            return str(path)
        else:
            return shutil.which("maestral") or ""

    def _get_available_implementation(self) -> Optional[SupportedImplementations]:
        """Returns the supported implementation depending on the platform."""

        system = platform.system()

        if system == "Darwin":
            return SupportedImplementations.launchd
        elif system == "Linux":
            return SupportedImplementations.xdg_desktop
        else:
            return None
