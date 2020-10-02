class Renderer:
    """
    Renderer base class

    :param renderer_mapping: A dictionary mapping renderer attributes to data source
        accessors. For instance the "path" attribute of a data source can be mapped to the
        "text" or "icon" attribute of the renderer.
    """

    ATTRIBUTES = tuple()

    def __init__(self, **renderer_mapping):
        self._renderer_mapping = renderer_mapping

    def _attr_for_row(self, name, row, default=None):

        if name not in self.ATTRIBUTES:
            raise ValueError("{0} has no attribute {1}".format(self.__class__.__name__, name))

        try:
            accessor = self._renderer_mapping[name]
            return getattr(row, accessor)
        except AttributeError:
            return default
