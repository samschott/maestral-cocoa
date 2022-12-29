# -*- coding: utf-8 -*-

# system imports
import sys

from importlib_metadata import metadata


# detect if we have been built with briefcase or frozen with PyInstaller
FROZEN = "Briefcase-Version" in metadata(__package__) or getattr(sys, "frozen", False)
