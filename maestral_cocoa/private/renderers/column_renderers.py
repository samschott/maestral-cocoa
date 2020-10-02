from toga import Icon

from .base import Renderer


class RendererText(Renderer):
    """Renderer for a text column."""
    ATTRIBUTES = ("text",)

    def text_for_row(self, row):
        """
        Returns the text to render in the column for a certain row. Rendering is performed
        by the backend. Can be subclassed by the user as long as the return type does not
        change.

        :param row: :class:`toga.sources.Row` instance for a :class:`toga.Table` or
            :class:`toga.sources.Node` instance for a :class:`toga.Tree`.
        :returns: Text to render in the cell.
        :rtype: str
        """
        value = self._attr_for_row("text", row)
        return str(value)


class RendererIconText(RendererText):
    """Renderer for a column with icon and text."""

    ATTRIBUTES = ("icon", "text")

    def icon_for_row(self, row):
        """
        Returns the icon to render in the column for a certain row. Rendering is performed
        by the backend. Can be subclassed by the user as long as the return type does not
        change.

        :param row: :class:`toga.sources.Row` instance for a :class:`toga.Table` or
            :class:`toga.sources.Node` instance for a :class:`toga.Tree`.
        :returns: Icon to render in the cell.
        :rtype: :class:`toga.Icon`
        """
        value = self._attr_for_row("icon", row, default="")

        if isinstance(value, Icon):
            return value
        elif isinstance(value, str):
            return Icon(value)
        else:
            raise ValueError("Need icon or file path")


class RendererCheckboxText(RendererText):
    """Renderer for a column with a checkbox and text."""

    ATTRIBUTES = ("checked_state", "text")

    def checked_state_for_row(self, row):
        """
        Returns the checked state to render in the column for a certain row. Rendering is
        performed by the backend. Can be subclassed by the user as long as the return type
        does not change.

        :param row: :class:`toga.sources.Row` instance for a :class:`toga.Table` or
            :class:`toga.sources.Node` instance for a :class:`toga.Tree`.
        :returns: Checked state
        :rtype: bool
        """
        value = self._attr_for_row("checked_state", row)

        if isinstance(value, bool):
            return value
        elif value in (0, 1):
            return bool(value)
        else:
            raise ValueError("Need a boolean")


class RendererCheckboxIconText(RendererCheckboxText, RendererIconText):
    """Renderer for a column with a checkbox, an icon and text."""

    ATTRIBUTES = ("checked_state", "icon", "text")


class RendererProgress(Renderer):
    """Renderer for a column with progress bars."""

    ATTRIBUTES = ("value", "max", "running")

    def value_for_row(self, row):
        """
        Returns the progress to render in the column for a certain row. Rendering is
        performed by the backend. Can be subclassed by the user as long as the return type
        does not change.

        :param row: :class:`toga.sources.Row` instance for a :class:`toga.Table` or
            :class:`toga.sources.Node` instance for a :class:`toga.Tree`.
        :returns: Current progress of progress bar.
        :rtype: float
        """
        value = self._attr_for_row("checked_state", row, default=0)

        if not isinstance(value, float):
            raise ValueError("Need a float")

        return max(0.0, value)

    def max_for_row(self, row):
        """
        Returns the maximum progress to render in the column for a certain row. Rendering
        is performed by the backend. Can be subclassed by the user as long as the return
        type does not change.

        :param row: :class:`toga.sources.Row` instance for a :class:`toga.Table` or
            :class:`toga.sources.Node` instance for a :class:`toga.Tree`.
        :returns: Maximum value of progress bar. None for an indeterminate progress bar.
        :rtype: float | None
        """
        value = self._attr_for_row("checked_state", row)

        if value is None or value > 0:
            return value
        else:
            raise ValueError("Need a float > 0 or None")


class RendererActivity(Renderer):
    """Renderer for a column with activity indicators."""

    ATTRIBUTES = ("running",)

    def running_for_row(self, row):
        """
        Returns the activity state to render in the column for a certain row. Rendering
        is performed by the backend. Can be subclassed by the user as long as the return
        type does not change.

        :param row: :class:`toga.sources.Row` instance for a :class:`toga.Table` or
            :class:`toga.sources.Node` instance for a :class:`toga.Tree`.
        :returns: Whether to show an activity indicator.
        :rtype: bool
        """
        value = self._attr_for_row("running", row, default=False)

        if isinstance(value, bool):
            return value
        else:
            raise ValueError("Need a boolean")
