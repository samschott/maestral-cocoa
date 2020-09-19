# -*- coding: utf-8 -*-

from ctypes import util, cdll


# patch find_library to work around library
# discovery issue on macOS Big Sur https://bugs.python.org/issue41100

def _find_library(name):
    paths = [
        f'/System/Library/Frameworks/{name}.framework/{name}',
        f'/usr/lib/lib{name}.dylib',
        f'{name}.dylib',
    ]

    for path in paths:
        try:
            cdll.LoadLibrary(path)
            return path
        except OSError:
            pass

    return None


util.find_library = _find_library


__author__ = 'Sam Schott'
__version__ = '1.2.1.dev0'
__url__ = 'https://github.com/SamSchott/maestral'
