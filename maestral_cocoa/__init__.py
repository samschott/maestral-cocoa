# -*- coding: utf-8 -*-
import os.path as osp
from ctypes import util


# patch find_library to work around library
# discovery issue on macOS Big Sur https://bugs.python.org/issue41100

def _find_library(name):
    paths = [
        f'/System/Library/Frameworks/{name}.framework/{name}',
        f'/usr/lib/lib{name}.dylib',
        f'{name}.dylib',
    ]

    for path in paths:
        if osp.islink(path):
            return path

    return None


util.find_library = _find_library


__author__ = 'Sam Schott'
__version__ = '1.2.0.dev1'
__url__ = 'https://github.com/SamSchott/maestral'
