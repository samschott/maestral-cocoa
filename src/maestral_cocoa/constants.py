# -*- coding: utf-8 -*-

# system imports
import sys

try:
    from importlib import metadata as importlib_metadata
except ImportError:
    # Backwards compatibility - importlib.metadata was added in Python 3.8
    import importlib_metadata


app_module = sys.modules["__main__"].__package__
metadata = importlib_metadata.metadata(app_module)

FROZEN = "Briefcase-Version" in metadata or getattr(sys, "frozen", False)
