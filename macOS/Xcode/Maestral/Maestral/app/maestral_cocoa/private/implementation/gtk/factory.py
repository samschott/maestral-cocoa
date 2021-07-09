# -*- coding: utf-8 -*-

from toga_gtk.factory import *  # noqa: F401,F406
from toga_gtk.widgets import Box as TogaBox


# ==== layout widgets ====================================================================


class VibrantBox(TogaBox):
    """A box with vibrancy. Since this is not supported in Gtk, we just
    create a regular box"""

    def set_material(self, material):
        pass
