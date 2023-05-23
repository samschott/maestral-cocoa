# -*- coding: utf-8 -*-
import asyncio
import enum
import os

# external imports
import click
import toga
from toga.handlers import wrapped_handler
from toga.widgets.base import Widget
from toga.style.pack import Pack
from toga.constants import ROW, RIGHT, TRANSPARENT

# local imports
from .platform import get_platform_factory
from .constants import TRUNCATE_TAIL, ImageTemplate


os.environ["TOGA_BACKEND"] = "maestral_cocoa.private.implementation.cocoa"

# ==== layout widgets ==================================================================


class Spacer(toga.Box):
    """A widget to take up space and push others to the side."""

    def __init__(self, direction=ROW):
        style = Pack(flex=1, direction=direction, background_color=TRANSPARENT)
        super().__init__(style=style)


# ==== buttons =========================================================================


class DialogButtons(toga.Box):
    """
    A dialog button box. Buttons will be created from the given list of labels (defaults
    to ['Ok', 'Cancel']). If a callback ``on_press`` is provided, will be executed if
    any button is pressed, with the label of the respective button as an argument.

    :param labels: An iterable of label strings.
    :param str default: A default button to select. Value must match one of the labels
    :param on_press: Callback when any button is pressed. Takes the button
        label as argument.
    """

    MIN_BUTTON_WIDTH = 80

    def __init__(
        self,
        labels=("Ok", "Cancel"),
        default="Ok",
        on_press=None,
        id=None,
        style=None,
    ):
        self._buttons = []
        super().__init__(id=id, style=style)

        # always display buttons in a row, to the right
        self.style.update(direction=ROW)
        self.add(Spacer())

        for label in labels[::-1]:
            style = Pack(padding_left=10, alignment=RIGHT, background_color=TRANSPARENT)
            btn = toga.Button(text=label, style=style)

            if label == default:
                # TODO: remove private API access
                btn._impl.native.keyEquivalent = "\r"

            self.add(btn)
            self._buttons.insert(0, btn)

            btn.style.width = max(self.MIN_BUTTON_WIDTH, btn.intrinsic.width.value)

        self.on_press = on_press

    @property
    def on_press(self):
        return self._on_press

    @on_press.setter
    def on_press(self, handler):
        if not handler:
            new_handler = None
        elif asyncio.iscoroutinefunction(handler):

            async def new_handler(widget):
                return await handler(widget.text)

        else:

            def new_handler(widget):
                return handler(widget.text)

        for btn in self._buttons:
            btn.on_press = new_handler

        self._on_press = new_handler

    def __getitem__(self, item):
        return next(btn for btn in self._buttons if btn.text == item)

    def __iter__(self):
        return iter(self._buttons)

    @property
    def enabled(self):
        return any(btn.enabled for btn in self)

    @enabled.setter
    def enabled(self, yes):
        for btn in self._buttons:
            btn.enabled = yes


class Switch(toga.Switch):
    """Reimplements toga.Switch to allow *programmatic* setting of
    an intermediate state."""

    @property
    def state(self):
        """Button state: 0 = off, 1 = mixed, 2 = on."""
        return self._impl.get_state()

    @state.setter
    def state(self, value):
        """Setter: Button state: 0 = off, 1 = mixed, 2 = on."""
        self._impl.set_state(value)


class RadioButton(Switch):
    class Group(enum.Enum):
        A = "A"
        B = "B"

    def __init__(
        self,
        text,
        group=Group.A,
        id=None,
        style=None,
        on_change=None,
        value=False,
    ):
        super().__init__(text, id=id, style=style)

        self._impl = self.factory.RadioButton(interface=self)
        self.text = text
        self._on_change = None
        self.value = value
        self.on_change = on_change

        self._impl.set_group(group)


class FreestandingIconButton(toga.Widget):
    """A freestanding button with an icon."""

    def __init__(
        self,
        text,
        icon=None,
        id=None,
        style=None,
        on_press=None,
    ):
        super().__init__(id=id, style=style)

        # Create a platform specific implementation of a Button
        self._impl = self.factory.FreestandingIconButton(interface=self)

        # Set all the properties
        self.text = text
        self.on_press = on_press
        self.icon = icon

    @property
    def on_press(self):
        """The handler to invoke when the button is pressed."""
        return self._on_press

    @on_press.setter
    def on_press(self, handler):
        self._on_press = wrapped_handler(self, handler)

    @property
    def text(self):
        """
        Returns:
            The button text as a ``str``
        """
        return self._text

    @text.setter
    def text(self, value):
        if value is None:
            self._text = ""
        else:
            self._text = str(value)
        self._impl.set_text(value)
        self._impl.rehint()

    @property
    def icon(self):
        """
        Returns:
            The button icon
        """
        return self._icon

    @icon.setter
    def icon(self, value):
        self._icon = value
        self._impl.set_icon(value)
        self._impl.rehint()


class FollowLinkButton(FreestandingIconButton):
    def __init__(
        self,
        text,
        url=None,
        locate=False,
        id=None,
        style=None,
    ):
        icon = Icon(template=ImageTemplate.FollowLink)
        self.url = url
        self.locate = locate
        super().__init__(text, icon=icon, id=id, style=style)

        def handler(widget):
            click.launch(widget.url, locate=widget.locate)

        self._on_press = wrapped_handler(self, handler)


class FileSelectionButton(toga.Widget):
    MIN_WIDTH = 100

    def __init__(
        self,
        initial="",
        select_files=True,
        select_folders=False,
        on_select=None,
        dialog_title="",
        dialog_message="",
        show_full_path=False,
        id=None,
        style=None,
    ):
        super().__init__(id=id, style=style)

        self._select_files = select_files
        self._select_folders = select_folders

        # Create a platform specific implementation
        self._impl = self.factory.FileSelectionButton(interface=self)

        # Set all the properties
        self.show_full_path = show_full_path
        self.current_selection = str(initial)
        self.select_files = select_files
        self.select_folders = select_folders
        self.on_select = on_select
        self.dialog_title = dialog_title
        self.dialog_message = dialog_message

    @property
    def select_files(self):
        return self._select_files

    @select_files.setter
    def select_files(self, value):
        self._select_files = value
        self._impl.set_select_files(value)

    @property
    def select_folders(self):
        return self._select_folders

    @select_folders.setter
    def select_folders(self, value):
        self._select_folders = value
        self._impl.set_select_folders(value)

    @property
    def current_selection(self):
        return self._impl.get_current_selection()

    @current_selection.setter
    def current_selection(self, value):
        self._impl.set_current_selection(str(value))

    @property
    def dialog_title(self):
        return self._dialog_title

    @dialog_title.setter
    def dialog_title(self, value):
        self._dialog_title = value
        self._impl.set_dialog_title(self._dialog_title)

    @property
    def dialog_message(self):
        return self._dialog_message

    @dialog_message.setter
    def dialog_message(self, value):
        self._dialog_message = value
        self._impl.set_dialog_message(self._dialog_message)

    @property
    def show_full_path(self):
        return self._show_full_path

    @show_full_path.setter
    def show_full_path(self, value):
        self._show_full_path = value
        self._impl.set_show_full_path(self._show_full_path)

    @property
    def on_select(self):
        return self._on_select

    @on_select.setter
    def on_select(self, handler):
        self._on_select = wrapped_handler(self, handler)
        self._impl.set_on_select(self._on_select)


# ==== labels ==========================================================================


class Label(toga.Label):
    """Reimplements toga.Label with text wrapping."""

    def __init__(
        self,
        text,
        linebreak_mode=TRUNCATE_TAIL,
        id=None,
        style=None,
    ):
        self._linebreak_mode = linebreak_mode
        super().__init__(text, id=id, style=style)
        self.linebreak_mode = linebreak_mode

    @property
    def linebreak_mode(self):
        return self._linebreak_mode

    @linebreak_mode.setter
    def linebreak_mode(self, value):
        self._linebreak_mode = value
        self._impl.set_linebreak_mode(value)


class LinkLabel(Widget):
    """A label with a hyperlink."""

    def __init__(self, text, url, id=None, style=None):
        super().__init__(id=id, style=style)

        self._text = text
        self._url = url

        self._impl = self.factory.LinkLabel(interface=self)
        self.text = text
        self.url = url

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value
        self._impl.set_text(value)

    @property
    def url(self):
        return self._text

    @url.setter
    def url(self, value):
        self._url = value
        self._impl.set_url(value)


# ==== icons ===========================================================================


class Icon(toga.Icon):
    """
    Reimplements toga.Icon to provide the icon for the file / folder type
    instead of loading an icon from the file content.

    :param path: File to path.
    """

    def __init__(self, path=None, for_path=None, template=None):
        self.factory = get_platform_factory()
        self.path = path
        self.for_path = for_path
        self.template = template

        self._impl = self.factory.Icon(
            interface=self,
            path=self.path,
            for_path=self.for_path,
            template=self.template,
        )


# ==== menus and menu items ============================================================


class MenuItem:
    """
    A menu item to be used in a Menu.

    Args:
        label: A label for the item.
        icon: (optional) a path to an icon resource to decorate the item.
        action: (optional) a function to invoke when the item is clicked.
        submenu: A Menu to use as a submenu. It will become visible when this item is
            clicked.
    """

    def __init__(
        self,
        label,
        icon=None,
        checkable=False,
        action=None,
        shortcut=None,
        submenu=None,
    ):
        self.factory = get_platform_factory()
        self._impl = self.factory.MenuItem(interface=self)

        self._checkable = checkable
        self.action = action
        self.label = label
        self.icon = icon
        self.shortcut = shortcut
        self.submenu = submenu

    @property
    def icon(self):
        return self._icon

    @icon.setter
    def icon(self, icon_or_name):
        if isinstance(icon_or_name, Icon) or icon_or_name is None:
            self._icon = icon_or_name
        else:
            self._icon = Icon(icon_or_name)

        self._impl.set_icon(self._icon)

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, label):
        self._label = label
        self._impl.set_label(label)

    @property
    def shortcut(self):
        return self._shortcut

    @shortcut.setter
    def shortcut(self, value):
        self._shortcut = value
        if self._impl is not None:
            self._impl.set_shortcut(value)

    @property
    def submenu(self):
        return self._submenu

    @submenu.setter
    def submenu(self, submenu):
        self._submenu = submenu
        if submenu:
            self._impl.set_submenu(submenu._impl)
        else:
            self._impl.set_submenu(None)

    @property
    def action(self):
        return self._action

    @action.setter
    def action(self, action):
        self._impl.set_enabled(action is not None)

        if self._checkable:

            def new_action(*args):
                self.checked = not self.checked
                if action:
                    action(args)

        else:
            new_action = action

        self._action = wrapped_handler(self, new_action)
        self._impl.set_action(self._action)

        if self._action:
            self.enabled = True

    @property
    def checked(self):
        return self._checked

    @checked.setter
    def checked(self, yes):
        if self._checkable:
            self._checked = yes
            self._impl.set_checked(yes)


class MenuItemSeparator:
    """A horizontal separator between menu items."""

    def __init__(self):
        self.factory = get_platform_factory()
        self._impl = self.factory.MenuItemSeparator(self)


class Menu:
    """
    A menu, to be used as context menu, status bar menu or in the menu bar.

    Args:
        items: A list of MenuItem.
    """

    def __init__(self, items=None, on_open=None, on_close=None):
        self.factory = get_platform_factory()
        self._items = []
        self.on_open = on_open
        self.on_close = on_close

        self._impl = self.factory.Menu(self)

        if items:
            self.add(*items)

    def add(self, *items):
        """Add items to the menu."""
        self._items += items
        for item in items:
            self._impl.add_item(item._impl)

    def insert(self, index, item):
        """Insert item at a given index."""
        if item not in self._items:
            self._items.insert(index, item)
            self._impl.insert_item(index, item._impl)

    def remove(self, *items):
        """Remove items from the menu."""
        for item in items:
            try:
                self._items.remove(item)
            except ValueError:
                pass
            else:
                self._impl.remove_item(item._impl)

    def clear(self):
        """Clear the menu (removes all items)"""
        for item in self.items:
            self._impl.remove_item(item._impl)
        self._items.clear()

    @property
    def items(self):
        """All MenuItems in the menu."""
        return self._items

    @property
    def visible(self):
        """True if the menu is currently visible."""
        return self._impl.visible

    @property
    def on_open(self):
        return self._on_open

    @on_open.setter
    def on_open(self, callback):
        self._on_open = wrapped_handler(self, callback)

    @property
    def on_close(self):
        return self._on_close

    @on_close.setter
    def on_close(self, callback):
        self._on_close = wrapped_handler(self, callback)


# ==== StatusBarItem ===================================================================


class StatusBarItem:
    """A status bar item which can have an icon and a menu."""

    def __init__(self, icon, menu=None):
        self.factory = get_platform_factory()
        self._impl = self.factory.StatusBarItem(self)

        self.icon = icon
        self.menu = menu

    @property
    def menu(self):
        return self._menu

    @menu.setter
    def menu(self, menu):
        self._menu = menu
        if menu:
            self._impl.set_menu(menu._impl)

    @property
    def icon(self):
        return self._icon

    @icon.setter
    def icon(self, icon_or_name):
        if isinstance(icon_or_name, Icon) or icon_or_name is None:
            self._icon = icon_or_name
        else:
            self._icon = Icon(icon_or_name)

        self._impl.set_icon(self._icon)


# ==== Custom Window ===================================================================


class Window(toga.Window):
    def __init__(
        self,
        id=None,
        title=None,
        position=(100, 100),
        size=(640, 480),
        toolbar=None,
        resizeable=True,
        closeable=True,
        minimizable=True,
        release_on_close=True,
        is_dialog=False,
        app=None,
        on_close=lambda x: True,  # See https://github.com/beeware/toga/issues/1482
    ):
        super().__init__(
            id=id,
            title=title,
            position=position,
            size=size,
            toolbar=toolbar,
            resizeable=resizeable,
            closeable=closeable,
            minimizable=minimizable,
            on_close=on_close,
        )
        app.windows += self

        self.release_on_close = release_on_close
        self.is_dialog = is_dialog

        if not position:
            self.center()

    # visibility and positioning

    @property
    def visible(self):
        return self._impl.is_visible()

    def center(self):
        self._impl.center()

    def raise_(self):
        self.show()
        self._impl.force_to_front()

    def close(self):
        self._impl.close()

    # sheet support

    def show_as_sheet(self, window):
        self._impl.show_as_sheet(window)

    @property
    def is_dialog(self):
        return self._is_dialog

    @is_dialog.setter
    def is_dialog(self, yes):
        self._is_dialog = yes
        self._impl.set_dialog(yes)

    # memory management

    @property
    def release_on_close(self):
        return self._release_on_close

    @release_on_close.setter
    def release_on_close(self, value):
        self._release_on_close = value
        self._impl.set_release_on_close(value)


# ==== Application =====================================================================


class SystemTrayApp(toga.App):
    def __init__(
        self,
        formal_name=None,
        app_id=None,
        app_name=None,
        id=None,
        icon=None,
        author=None,
        version=None,
        home_page=None,
        description=None,
        startup=None,
        on_exit=None,
    ):
        super().__init__(
            formal_name=formal_name,
            app_id=app_id,
            app_name=app_name,
            id=id,
            icon=icon,
            author=author,
            version=version,
            home_page=home_page,
            description=description,
            startup=startup,
            on_exit=on_exit,
        )

    def _create_impl(self):
        return self.factory.SystemTrayApp(interface=self)

    def show_dock_icon(self):
        self._impl.show_dock_icon()

    def hide_dock_icon(self):
        self._impl.hide_dock_icon()

    def alert(
        self,
        title,
        message,
        details=None,
        details_title="Traceback",
        button_labels=("Ok",),
        checkbox_text=None,
        level="info",
        icon=None,
    ):
        icon = icon or self.icon

        return self._impl.alert(
            title,
            message,
            details,
            details_title,
            button_labels,
            checkbox_text,
            level,
            icon,
        )

    async def alert_async(
        self,
        title,
        message,
        details=None,
        details_title="Traceback",
        button_labels=("Ok",),
        checkbox_text=None,
        level="info",
        icon=None,
    ):
        icon = icon or self.icon

        return await self._impl.alert_async(
            title,
            message,
            details,
            details_title,
            button_labels,
            checkbox_text,
            level,
            icon,
        )


# ==== helpers =========================================================================


def apply_round_clipping(image_view: toga.ImageView):
    """Clips an image in a given toga.ImageView to a circular mask."""
    factory = get_platform_factory()
    return factory.apply_round_clipping(image_view._impl)
