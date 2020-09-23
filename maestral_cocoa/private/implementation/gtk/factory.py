# -*- coding: utf-8 -*-

# system import
import os.path as osp
import mimetypes

# external imports
from travertino.size import at_least
from toga.platform import get_platform_factory
from toga_gtk.factory import *  # noqa: F401,F406
from toga_gtk.widgets.base import Widget
from toga_gtk.widgets.box import Box as TogaBox
from toga_gtk.widgets.button import Button as TogaButton
from toga_gtk.widgets.label import Label as TogaLabel
from toga_gtk.widgets.multilinetextinput import (
    MultilineTextInput as TogaMultilineTextInput,
)
from toga_gtk.window import Window as TogaWindow
from toga_gtk.app import App as TogaApp
from toga_gtk.libs import GdkPixbuf, Gtk, Gio, Pango

# local imports
from ...constants import (
    WORD_WRAP,
    CHARACTER_WRAP,
    TRUNCATE_HEAD,
    TRUNCATE_MIDDLE,
    TRUNCATE_TAIL,
    ON,
    OFF,
    MIXED,
    ImageTemplate,
)


# ==== icons =============================================================================


class Icon:
    """Reimplements toga.Icon but provides the icon for the file / folder type
    instead of loading an icon from the file content."""

    _to_gtk_template = {
        None: None,
        ImageTemplate.Refresh: "view-refresh",
        ImageTemplate.FollowLink: "go-next",
        ImageTemplate.Reveal: "system-search",
        ImageTemplate.InvalidData: "go-previous",
        ImageTemplate.StopProgress: "process-stop",
    }

    EXTENSIONS = [".icns", ".ico", "svg", ".png"]
    SIZES = None

    def __init__(self, interface, path=None, for_path=None, template=None):
        self.interface = interface
        self.path = path
        self.for_path = for_path
        self.template = template

        self._native = None

    @property
    def native(self):

        if self._native:
            return self._native

        if self.path:
            self._native = GdkPixbuf.Pixbuf.new_from_file(str(self.path))
            return self._native

        elif self.for_path:
            # always return a new pointer since an old one may be invalidated
            # icons are cached by AppKit anyways
            path = str(self.for_path)
            if osp.exists(path):
                file = Gio.File.new_for_path(path)
                file_info = file.query_info("standard::icon", 0)
                theme = Gtk.IconTheme.get_default()
                icon_info = theme.choose_icon(file_info.get_icon().get_names(), 64, 0)
                if icon_info:
                    return icon_info.load_icon()
                else:
                    raise RuntimeError(f"No icon found for {path}")
            else:
                type_, encoding = mimetypes.guess_type(path)
                if type_:
                    icon = Gio.content_type_get_icon(type_)
                    theme = Gtk.IconTheme.get_default()
                    icon_info = theme.choose_icon(icon.get_names(), 64, 0)
                    if icon_info:
                        return icon_info.load_icon()
                    else:
                        raise RuntimeError(f"No icon found for {path}")

        elif self.template:
            gtk_template = Icon._to_gtk_template[self.template]
            self._native = Gtk.IconTheme.get_default().load_icon(gtk_template, 64, 0)
            return self._native


# ==== labels ============================================================================


class Label(TogaLabel):
    def set_linebreak_mode(self, value):

        if value == TRUNCATE_HEAD:
            self.native.set_ellipsize(Pango.EllipsizeMode.START)
        elif value == TRUNCATE_TAIL:
            self.native.set_ellipsize(Pango.EllipsizeMode.END)
        elif value == TRUNCATE_MIDDLE:
            self.native.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        else:
            self.native.set_ellipsize(Pango.EllipsizeMode.NONE)

        if value == WORD_WRAP:
            self.native.set_line_wrap(True)
            self.native.set_line_wrap_mode(Pango.WrapMode.WORD)
        elif value == CHARACTER_WRAP:
            self.native.set_line_wrap(True)
            self.native.set_line_wrap_mode(Pango.WrapMode.CHAR)
        else:
            self.native.set_line_wrap(False)

    # TODO: rehint


class RichLabel(Label):
    """A multiline text view with html support."""

    def set_html(self, value):
        self.native.set_markup(value)


class RichMultilineTextInput(TogaMultilineTextInput):
    """A scrollable text view with html support."""

    def set_html(self, value):
        # TODO
        self.interface.factory.not_implemented("RichMultilineTextInput.set_html()")


# ==== buttons ===========================================================================


class FreestandingIconButton(TogaButton):
    """A styled button with an icon."""

    def create(self):
        super().create()
        self.native.set_relief(Gtk.ReliefStyle.NONE)
        self.native.props.always_show_image = True

    def set_icon(self, icon_iface):
        factory = get_platform_factory()
        icon = icon_iface.bind(factory)
        self.native.set_image(icon)


class Switch(Widget):
    """Reimplements toga_cocoa.Switch but allows *programmatic* setting of
    an intermediate state."""

    _to_gtk = {OFF: 0, MIXED: -1, ON: 1}
    _to_toga = {0: OFF, -1: MIXED, 1: ON}

    def create(self):
        self.native = Gtk.CheckButton()
        self.native.interface = self.interface
        self._handler_id = self.native.connect("toggled", self.gtk_on_toggle)

    def gtk_on_toggle(self, widget):
        if self.interface.on_toggle:
            self.interface.on_toggle(self.interface)

    def set_on_toggle(self, handler):
        pass

    def set_label(self, label):
        self.native.set_label(self.interface.label)

    def get_is_on(self):
        return self.native.get_active()

    def set_is_on(self, value):
        self.native.set_active(value)

    def set_state(self, value):

        with self.native.handler_block(self._handler_id):  # ignore programmatic changes
            if value == MIXED:
                self.native.set_inconsistent(True)
            elif value == ON:
                self.set_is_on(True)
            else:
                self.set_is_on(False)

    def get_state(self):
        if self.native.get_inconsistent():
            return MIXED
        elif self.get_is_on():
            return ON
        else:
            return OFF

    def rehint(self):
        width = self.native.get_preferred_width()
        height = self.native.get_preferred_height()

        self.interface.intrinsic.width = at_least(width[0])
        self.interface.intrinsic.height = height[1]


class FileSelectionButton(Widget):
    def create(self):
        self.native = Gtk.FileChooserButton()
        self.native.interface = self.interface
        self.native.set_create_folders(True)
        self.native.connect("file-set", self.gtk_on_select)

    def gtk_on_select(self, widget):
        if self.interface.on_select:
            self.interface.on_select(self.interface)

    def get_current_selection(self):
        uri = self.native.get_uri()
        return uri.strip("file://") if uri else None

    def set_current_selection(self, path):
        self.native.select_uri(f"file://{path}")

    def set_on_select(self, handler):
        pass

    def set_select_files(self, value):
        if value:
            self.native.set_action(Gtk.FileChooserAction.OPEN)

    def set_select_folders(self, value):
        if value:
            self.native.set_action(Gtk.FileChooserAction.SELECT_FOLDER)

    def set_dialog_title(self, value):
        self.native.set_title(value)

    def set_dialog_message(self, value):
        pass

    def rehint(self):
        height = self.native.get_preferred_height()

        self.interface.intrinsic.width = at_least(self.interface.MIN_WIDTH)
        self.interface.intrinsic.height = height[1]


# ==== layout widgets ====================================================================


class VibrantBox(TogaBox):
    """A box with vibrancy. Since this is not supported in Gtk, we just
    create a regular box"""

    def set_material(self, material):
        pass


# ==== menus and status bar ==============================================================


class MenuItem:
    def __init__(self, interface):
        self.interface = interface
        self.native = Gtk.MenuItem()
        self.native.connect("activate", self.gtk_on_press)

    def set_enabled(self, enabled):
        self.native.enabled = enabled

    def set_icon(self, icon):
        self.interface.factory.not_implemented("MenuItem.set_icon()")

    def set_label(self, label):
        self.native.set_label(label)

    def set_submenu(self, menu_impl):
        if menu_impl:
            self.native.set_submenu(menu_impl.native)
        else:
            self.native.set_submenu(None)

    def set_action(self, action):
        pass

    def set_checked(self, yes):
        # TODO: implement
        self.interface.factory.not_implemented("MenuItem.set_checked()")

    def gtk_on_press(self, event):
        if self.interface.action:
            self.interface.action(self.interface)


class MenuItemSeparator:
    def __init__(self, interface):
        self.interface = interface
        self.native = Gtk.SeparatorMenuItem()


class Menu:
    def __init__(self, interface):
        self.interface = interface
        self._visible = False

        self.native = Gtk.Menu()

    def add_item(self, item_impl):
        self.native.add(item_impl.native)

    def insert_item(self, index, item_impl):
        self.native.insert(item_impl.native, index)

    def remove_item(self, item_impl):
        self.native.remove(item_impl.native)

    @property
    def visible(self):
        return self._visible


# ==== StatusBarItem =====================================================================


# this will require a dbus interface
class StatusBarItem:
    def __init__(self, interface):
        pass

    def set_icon(self, icon):
        pass

    def set_menu(self, menu_impl):
        pass


# ==== Application =======================================================================


class SystemTrayApp(TogaApp):

    _MAIN_WINDOW_CLASS = None

    def gtk_startup(self, data=None):
        # skip the setup of menu bar items
        self.interface.startup()
        # Now that we have menus, make the app take responsibility for
        # showing the menubar.
        settings = Gtk.Settings.get_default()
        settings.set_property("gtk-shell-shows-menubar", False)

    def open_document(self, path):
        pass

    async def alert_async(
        self,
        title,
        message,
        details,
        details_title,
        button_labels,
        checkbox_text,
        level,
        icon,
    ):
        self.interface.factory.not_implemented("SystemTrayApp.alert_async()")

    def alert(
        self,
        title,
        message,
        details,
        details_title,
        button_labels,
        checkbox_text,
        level,
        icon,
    ):
        self.interface.factory.not_implemented("SystemTrayApp.alert()")


class Window(TogaWindow):
    def is_visible(self):
        return bool(self.native.isVisible)

    def center(self):
        self.native.set_position(Gtk.WindowPosition.CENTER)

    def force_to_front(self):
        self.show()
        self.native.present()

    def show_as_sheet(self, window):
        self.native.set_transient_for(window._impl.native)
        self.show()

    def hide(self):
        self.native.hide()

    def close(self):
        self.native.set_transient_for(None)
        super().close()

    def set_release_on_close(self, value):
        pass

    def set_dialog(self, value):
        pass

    # dialogs

    async def save_file_sheet(self, title, message, suggested_filename, file_types):
        self.interface.factory.not_implemented("Window.save_file_sheet()")

    async def open_file_sheet(
        self, title, message, initial_directory, file_types, multiselect
    ):
        self.interface.factory.not_implemented("Window.open_file_sheet()")

    async def select_folder_sheet(self, title, message, initial_directory, multiselect):
        self.interface.factory.not_implemented("Window.select_folder_sheet()")

    async def alert_sheet(
        self,
        title,
        message,
        details,
        details_title,
        button_labels,
        checkbox_text,
        level,
        icon,
    ):
        self.interface.factory.not_implemented("Window.alert_sheet()")


# ==== helpers ===========================================================================


def apply_round_clipping(image_view_impl):
    """Clips an image in a given toga_gtk.ImageView to a circular mask."""
    pass
