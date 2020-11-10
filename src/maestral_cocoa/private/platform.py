# -*- coding: utf-8 -*-

import sys


def get_platform_factory(factory=None):
    """This function figures out what the current host platform is and
    imports the adequate factory. The factory is the interface to all platform
    specific implementations.

    Args:
        factory (:obj:`module`): (optional) Provide a custom factory that is
        automatically returned unchanged.

    Returns: The suitable factory for the current host platform
        or the factory that was given as a argument.

    Raises:
        RuntimeError: If no supported host platform can be identified.
    """
    if factory is not None:
        return factory

    elif sys.platform == "darwin":
        from .implementation.cocoa import factory

        return factory
    elif sys.platform == "linux":
        from .implementation.gtk import factory

        return factory
    else:
        raise RuntimeError("Couldn't identify a supported host platform.")
