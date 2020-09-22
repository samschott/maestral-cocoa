# -*- coding: utf-8 -*-

# system imports
import os.path as osp

# external imports
from travertino.size import at_least
from rubicon.objc import NSMakeSize
import toga
from toga.sources.accessors import to_accessor
from toga.constants import LEFT, TRANSPARENT
from toga.platform import get_platform_factory
from toga_cocoa.libs import (
    ObjCClass,
    objc_method,
    SEL,
    at,
    NSColor,
    NSString,
    NSTextView,
    NSRecessedBezelStyle,
    NSTextAlignment,
    NSViewMaxYMargin,
    NSMenuItem,
    NSKeyDown,
    NSMenu,
    NSApplication,
    send_super,
    NSObject,
    NSApplicationActivationPolicyAccessory,
    NSBundle,
    NSImage,
    NSImageInterpolationHigh,
    NSGraphicsContext,
    NSRect,
    NSPoint,
    NSBezierPath,
    NSTextField,
    NSPopUpButton,
    NSOpenPanel,
    NSFileHandlingPanelOKButton,
    NSTableView,
    NSOutlineView,
    NSScrollView,
    NSBezelBorder,
    NSTableViewColumnAutoresizingStyle,
    NSIndexSet,
    NSTableViewAnimation,
    NSRange,
    NSTableColumn,
)
from toga_cocoa.colors import native_color
from toga_cocoa.keys import toga_key, Key
from toga_cocoa.app import App as TogaApp
from toga_cocoa.widgets.base import Widget
from toga_cocoa.widgets.switch import Switch as TogaSwitch
from toga_cocoa.widgets.button import Button as TogaButton
from toga_cocoa.window import Window as TogaWindow
from toga_cocoa.widgets.multilinetextinput import (
    MultilineTextInput as TogaMultilineTextInput,
)
from toga_cocoa.widgets.internal.cells import TogaIconTextView
from toga_cocoa.widgets.internal.data import TogaData
from toga_cocoa.factory import *  # noqa: F401,F406

# local imports
from . import dialogs
from .constants import (
    NSButtonTypeMomentaryPushIn,
    NSFocusRingTypeNone,
    NSControlState,
    NSSquareStatusItemLength,
    NSWindowAnimationBehaviorDefault,
    NSWindowAnimationBehaviorAlertPanel,
    NSUTF8StringEncoding,
    NSImageLeading,
    NSVisualEffectStateActive,
    NSVisualEffectBlendingModeBehindWindow,
    NSCompositeSourceOver,
    NSImageNameFollowLinkFreestandingTemplate,
    NSImageNameInvalidDataFreestandingTemplate,
    NSImageNameRefreshFreestandingTemplate,
    NSImageNameRevealFreestandingTemplate,
    NSImageNameStopProgressFreestandingTemplate,
)
from ...constants import (
    WORD_WRAP,
    CHARACTER_WRAP,
    CLIP,
    TRUNCATE_HEAD,
    TRUNCATE_MIDDLE,
    TRUNCATE_TAIL,
    ON,
    OFF,
    MIXED,
    ImageTemplate,
)
from ...renderers import RendererText, RendererIconText


NSWorkspace = ObjCClass("NSWorkspace")
NSVisualEffectView = ObjCClass("NSVisualEffectView")
NSMutableAttributedString = ObjCClass("NSMutableAttributedString")
NSStatusBar = ObjCClass("NSStatusBar")
NSColorSpace = ObjCClass("NSColorSpace")
NSAutoreleasePool = ObjCClass("NSAutoreleasePool")


# ==== icons =============================================================================


class Icon:
    """Reimplements toga.Icon but provides the icon for the file / folder type
    instead of loading an icon from the file content."""

    _to_cocoa_template = {
        None: None,
        ImageTemplate.Refresh: NSImageNameRefreshFreestandingTemplate,
        ImageTemplate.FollowLink: NSImageNameFollowLinkFreestandingTemplate,
        ImageTemplate.Reveal: NSImageNameRevealFreestandingTemplate,
        ImageTemplate.InvalidData: NSImageNameInvalidDataFreestandingTemplate,
        ImageTemplate.StopProgress: NSImageNameStopProgressFreestandingTemplate,
    }

    EXTENSIONS = ['.pdf', '.icns', '.png']
    SIZES = None

    def __init__(self, interface, path=None, for_path=None, template=None):
        self.interface = interface
        self.interface._impl = self
        self.path = path
        self.for_path = for_path
        self.template = template

        self._native = None

    @property
    def native(self):

        if self._native:
            return self._native

        if self.path:
            self._native = NSImage.alloc().initWithContentsOfFile(str(self.path))
            return self._native

        elif self.for_path:
            # always return a new pointer since an old one may be invalidated
            # icons are cached by AppKit anyways
            if osp.exists(self.for_path):
                return NSWorkspace.sharedWorkspace.iconForFile(str(self.for_path))
            else:
                _, extension = osp.splitext(self.for_path)
                return NSWorkspace.sharedWorkspace.iconForFileType(extension)

        elif self.template:
            cocoa_template = Icon._to_cocoa_template[self.template]
            self._native = NSImage.imageNamed(cocoa_template)
            return self._native


# ==== labels ============================================================================


def attributed_str_from_html(raw_html, font=None, color=None):
    """Converts html to a NSAttributed string using the system font family and color."""

    html_value = """
    <span style="font-family: '{0}'; font-size: {1}; color: {2}">
    {3}
    </span>
    """
    font_family = font.fontName if font else "system-ui"
    font_size = font.pointSize if font else 13
    color = color or NSColor.labelColor
    c = color.colorUsingColorSpace(NSColorSpace.deviceRGBColorSpace)
    c_str = (
        f"rgb({c.redComponent * 255},{c.blueComponent * 255},{c.greenComponent * 255})"
    )
    html_value = html_value.format(font_family, font_size, c_str, raw_html)
    nsstring = NSString(at(html_value))
    data = nsstring.dataUsingEncoding(NSUTF8StringEncoding)
    attr_str = NSMutableAttributedString.alloc().initWithHTML(
        data,
        documentAttributes=None,
    )
    return attr_str


class Label(Widget):
    """Reimplements toga_cocoa.Label with text wrapping."""

    _toga_to_cocoa_linebreakmode = {
        WORD_WRAP: 0,
        CHARACTER_WRAP: 1,
        CLIP: 2,
        TRUNCATE_HEAD: 3,
        TRUNCATE_TAIL: 4,
        TRUNCATE_MIDDLE: 5,
    }

    def create(self):
        self.native = NSTextField.labelWithString("")
        self.native.impl = self
        self.native.interface = self.interface

        # Add the layout constraints
        self.add_constraints()

    def set_alignment(self, value):
        self.native.alignment = NSTextAlignment(value)

    def set_color(self, value):
        if value:
            self.native.textColor = native_color(value)

    def set_font(self, font):
        if font:
            self.native.font = font.bind(self.interface.factory).native

    def set_text(self, value):
        self.native.stringValue = value

    def set_linebreak_mode(self, value):
        self.native.cell.lineBreakMode = Label._toga_to_cocoa_linebreakmode[value]

    def set_background_color(self, color):
        if color in (None, TRANSPARENT):
            self.native.backgroundColor = NSColor.clearColor
            self.native.drawsBackground = False
        else:
            self.native.backgroundColor = native_color(color)
            self.native.drawsBackground = True

    def rehint(self):

        if self.interface.style.width:
            self.native.preferredMaxLayoutWidth = self.interface.style.width

        content_size = self.native.intrinsicContentSize()

        if self.interface.style.width:
            self.interface.intrinsic.width = at_least(content_size.width)
            self.interface.intrinsic.height = at_least(content_size.height)
        else:
            self.interface.intrinsic.width = at_least(0)
            self.interface.intrinsic.height = at_least(content_size.height)


class RichLabel(Widget):
    """A multiline text view with html support."""

    def create(self):
        self._color = None
        self.native = NSTextView.alloc().init()
        self.native.impl = self
        self.native.interface = self.interface

        self.native.drawsBackground = False
        self.native.editable = False
        self.native.selectable = True
        self.native.textContainer.lineFragmentPadding = 0

        self.native.bezeled = False

        # Add the layout constraints
        self.add_constraints()

    def set_html(self, value):
        attr_str = attributed_str_from_html(value, color=self._color)
        self.native.textStorage.setAttributedString(attr_str)
        self.rehint()

    def set_font(self, font):
        native_font = font.bind(self.interface.factory).native
        attr_str = attributed_str_from_html(
            self.interface.html, color=self._color, font=native_font
        )
        self.native.textStorage.setAttributedString(attr_str)
        self.rehint()

    def set_color(self, value):
        if value:
            self._color = native_color(value)

        # update html
        self.set_html(self.interface.html)

    def rehint(self):
        # force layout and get layout rect
        self.native.layoutManager.glyphRangeForTextContainer(self.native.textContainer)
        rect = self.native.layoutManager.usedRectForTextContainer(
            self.native.textContainer
        )

        self.interface.intrinsic.width = at_least(rect.size.width)
        self.interface.intrinsic.height = rect.size.height


class RichMultilineTextInput(TogaMultilineTextInput):
    """A scrollable text view with html support."""

    def set_html(self, value):
        attr_str = attributed_str_from_html(value, font=self.text.font)
        self.text.textStorage.setAttributedString(attr_str)


# ==== buttons ===========================================================================


class FreestandingIconButton(TogaButton):
    """A styled button with an icon."""

    def create(self):
        super().create()
        self.native.showsBorderOnlyWhileMouseInside = True
        self.native.bordered = False
        self.native.buttonType = NSButtonTypeMomentaryPushIn
        self.native.bezelStyle = NSRecessedBezelStyle
        self.native.imagePosition = NSImageLeading
        self.native.alignment = NSTextAlignment(LEFT)
        self.native.focusRingType = NSFocusRingTypeNone

    def set_label(self, label):
        self.native.title = " {}".format(self.interface.label)

    def set_icon(self, icon_iface):
        factory = get_platform_factory()
        icon = icon_iface.bind(factory)
        self.native.image = icon.native.resizeTo(11)


class Switch(TogaSwitch):
    """Reimplements toga_cocoa.Switch but allows *programmatic* setting of
    an intermediate state."""

    _to_cocoa = {OFF: 0, MIXED: -1, ON: 1}
    _to_toga = {0: OFF, -1: MIXED, 1: ON}

    def create(self):
        super().create()
        self.native.allowsMixedState = True
        self.native.autoresizingMask = NSViewMaxYMargin | NSViewMaxYMargin

    def set_state(self, value):
        self.native.state = self._to_cocoa[value]

    def get_state(self):
        return self._to_toga[self.native.state]

    def set_font(self, font):
        if font:
            self.native.font = font.bind(self.interface.factory).native

    def rehint(self):
        content_size = self.native.intrinsicContentSize()
        self.interface.intrinsic.height = 20
        self.interface.intrinsic.width = at_least(content_size.width)


class FileChooserTarget(NSObject):
    @objc_method
    def onSelect_(self, obj) -> None:
        if self.impl.native.indexOfSelectedItem == 2:

            self.impl.native.selectItemAtIndex(0)

            panel = NSOpenPanel.alloc().init()
            panel.title = self.interface.dialog_title
            panel.message = self.interface.dialog_message
            panel.canChooseFiles = self.interface.select_files
            panel.canChooseDirectories = self.interface.select_folders
            panel.canCreateDirectories = True
            panel.resolvesAliases = True
            panel.allowsMultipleSelection = False

            def completion_handler(r: int) -> None:

                if r == NSFileHandlingPanelOKButton:
                    path = str(panel.URL.path)

                    item = self.impl.native.itemAtIndex(0)
                    item.title = osp.basename(path)
                    item.image = NSWorkspace.sharedWorkspace.iconForFile(path).resizeTo(
                        16
                    )

                    self.impl._current_selection = path

                    if self.interface.on_select:
                        self.interface.on_select(self.interface)

            panel.beginSheetModalForWindow(
                self.interface.window._impl.native, completionHandler=completion_handler
            )


class FileSelectionButton(Widget):
    def create(self):
        self.native = NSPopUpButton.alloc().init()
        self.target = FileChooserTarget.alloc().init()
        self.target.interface = self.interface
        self.target.impl = self
        self.native.target = self.target
        self.native.action = SEL("onSelect:")

        self._current_selection = None
        self.native.addItemWithTitle("None")
        self.native.menu.addItem(NSMenuItem.separatorItem())
        self.native.addItemWithTitle("Choose...")

        self.add_constraints()

    def get_current_selection(self):
        return self._current_selection

    def set_current_selection(self, path):
        item = self.native.itemAtIndex(0)
        item.title = osp.basename(path)
        item.image = NSWorkspace.sharedWorkspace.iconForFile(path).resizeTo(16)
        self._current_selection = path

    def set_on_select(self, handler):
        pass

    def set_select_files(self, value):
        pass

    def set_select_folders(self, value):
        pass

    def set_dialog_title(self, value):
        pass

    def set_dialog_message(self, value):
        pass

    def rehint(self):
        content_size = self.native.intrinsicContentSize()
        self.interface.intrinsic.height = content_size.height + 1
        self.interface.intrinsic.width = at_least(
            max(self.interface.MIN_WIDTH, content_size.width)
        )


# ==== layout widgets ====================================================================


class VibrantBox(Widget):
    """A box with macOS vibrancy."""

    def create(self):
        self.native = NSVisualEffectView.new()
        self.native.state = NSVisualEffectStateActive
        self.native.blendingMode = NSVisualEffectBlendingModeBehindWindow
        self.native.material = self.interface.material
        self.native.wantsLayer = True

        # Add the layout constraints
        self.add_constraints()

    def set_material(self, material):
        self.native.material = material

    def rehint(self):
        content_size = self.native.intrinsicContentSize()
        self.interface.intrinsic.width = at_least(content_size.width)
        self.interface.intrinsic.height = at_least(content_size.height)


# ==== tree and table ====================================================================


class TogaTable(NSTableView):
    # TableDataSource methods
    @objc_method
    def numberOfRowsInTableView_(self, table) -> int:
        return len(self.interface.data) if self.interface.data else 0

    @objc_method
    def tableView_viewForTableColumn_row_(self, table, column, row: int):
        data_row = self.interface.data[row]
        interface_column = self._impl._column_for_identifier[str(column.identifier)]

        # creates a NSTableCellView from interface-builder template (does not exist)
        # or reuses an existing view which is currently not needed for painting
        # returns None (nil) if both fails
        tcv = self.makeViewWithIdentifier(column.identifier, owner=self)

        if not tcv:  # there is no existing view to reuse so create a new one

            if isinstance(interface_column.renderer, (RendererText, RendererIconText)):
                tcv = TogaIconTextView.alloc().init()
                tcv.identifier = column.identifier
            else:
                self.interface.factory.not_implemented(
                    "Unsupported renderer {}".format(interface_column.renderer)
                )
                tcv = TogaIconTextView.alloc().init()
                tcv.identifier = column.identifier

        if type(interface_column.renderer) is RendererText:
            text = interface_column.renderer.text_for_row(data_row)
            tcv.setText(text)
            tcv.setImage(None)
        elif type(interface_column.renderer) is RendererIconText:
            text = interface_column.renderer.text_for_row(data_row)
            icon = interface_column.renderer.icon_for_row(data_row).bind(
                self.interface.factory
            )
            tcv.setText(text)
            tcv.setImage(icon.native)

        # Keep track of last visible view for row
        self._impl._view_for_row[data_row] = tcv

        return tcv

    @objc_method
    def tableView_pasteboardWriterForRow_(self, table, row) -> None:
        # this seems to be required to prevent issue 21562075 in AppKit
        return None

    # TableDelegate methods
    @objc_method
    def selectionShouldChangeInTableView_(self, table) -> bool:
        # Explicitly allow selection on the table.
        # TODO: return False to disable selection.
        return True

    @objc_method
    def tableViewSelectionDidChange_(self, notification) -> None:
        if notification.object.selectedRow == -1:
            selected = None
        else:
            selected = self.interface.data[notification.object.selectedRow]

        if self.interface.on_select:
            self.interface.on_select(self.interface, row=selected)

    @objc_method
    def tableView_heightOfRow_(self, table, row: int) -> float:

        default_row_height = self.rowHeight
        margin = 2

        # get all views in column
        data_row = self.interface.data[row]

        heights = [default_row_height]

        for column in self.tableColumns:
            col_identifier = str(column.identifier)
            value = getattr(data_row, col_identifier, None)
            if isinstance(value, toga.Widget):
                # if the cell value is a widget, use its height
                heights.append(
                    value._impl.native.intrinsicContentSize().height + margin
                )

        return max(heights)

    # target methods
    @objc_method
    def onDoubleClick_(self, sender) -> None:
        if self.clickedRow == -1:
            clicked = None
        else:
            clicked = self.interface.data[self.clickedRow]

        if self.interface.on_double_click:
            self.interface.on_double_click(self.interface, row=clicked)


class Table(Widget):
    def create(self):

        self._view_for_row = dict()

        # Create a table view, and put it in a scroll view.
        # The scroll view is the native, because it's the outer container.
        self.native = NSScrollView.alloc().init()
        self.native.hasVerticalScroller = True
        self.native.hasHorizontalScroller = False
        self.native.autohidesScrollers = False
        self.native.borderType = NSBezelBorder

        self.table = TogaTable.alloc().init()
        self.table.interface = self.interface
        self.table._impl = self
        self.table.columnAutoresizingStyle = NSTableViewColumnAutoresizingStyle.Uniform
        self.table.usesAlternatingRowBackgroundColors = True
        self.table.allowsMultipleSelection = self.interface.multiple_select

        # Cocoa identifies columns by an identifier; create a mapping here
        self._column_for_identifier = {}
        for column in self.interface._columns:
            self._add_column(column)

        self.table.delegate = self.table
        self.table.dataSource = self.table
        self.table.target = self.table
        self.table.doubleAction = SEL("onDoubleClick:")

        # Embed the table view in the scroll view
        self.native.documentView = self.table

        # Add the layout constraints
        self.add_constraints()

    def change_source(self, source):
        self.table.reloadData()

    def insert(self, index, item):
        # set parent = None if inserting to the root item
        index_set = NSIndexSet.indexSetWithIndex(index)

        self.table.insertRowsAtIndexes(
            index_set, withAnimation=NSTableViewAnimation.EffectNone
        )

    def change(self, item):
        row_index = self.table.rowForView(self._view_for_row[item])
        row_indexes = NSIndexSet.indexSetWithIndex(row_index)
        column_indexes = NSIndexSet.indexSetWithIndexesInRange(
            NSRange(0, len(self.interface.columns))
        )
        self.table.reloadDataForRowIndexes(row_indexes, columnIndexes=column_indexes)

    def remove(self, index, item):
        indexes = NSIndexSet.indexSetWithIndex(index)
        self.table.removeRowsAtIndexes(
            indexes, withAnimation=NSTableViewAnimation.EffectNone
        )

    def clear(self):
        self._view_for_row.clear()
        self.table.reloadData()

    def get_selection(self):
        if self.interface.multiple_select:
            selection = []

            current_index = self.table.selectedRowIndexes.firstIndex
            for i in range(self.table.selectedRowIndexes.count):
                selection.append(self.interface.data[current_index])
                current_index = self.table.selectedRowIndexes.indexGreaterThanIndex(
                    current_index
                )

            return selection
        else:
            index = self.table.selectedRow
            if index != -1:
                return self.interface.data[index]
            else:
                return None

    def set_on_select(self, handler):
        pass

    def set_on_double_click(self, handler):
        pass

    def scroll_to_row(self, row):
        self.table.scrollRowToVisible(row)

    def rehint(self):
        self.interface.intrinsic.width = at_least(self.interface.MIN_WIDTH)
        self.interface.intrinsic.height = at_least(self.interface.MIN_HEIGHT)

    def _add_column(self, column):
        column._identifier = to_accessor(column.title)
        self._column_for_identifier[column._identifier] = column

        native_column = NSTableColumn.alloc().initWithIdentifier(at(column._identifier))
        native_column.minWidth = column.min_width
        native_column.maxWidth = column.max_width
        native_column.headerCell.stringValue = column.title

        self.table.addTableColumn(native_column)

    def add_column(self, column):
        self._add_column(column)
        self.table.sizeToFit()

    def remove_column(self, column):
        if hasattr(column, "_identifier"):
            native_column = self.table.tableColumnWithIdentifier(at(column._identifier))
            self.table.removeTableColumn(native_column)

            # delete column and identifier
            del self._column_for_identifier[column._identifier]

            self.table.sizeToFit()


class TogaTree(NSOutlineView):
    # OutlineViewDataSource methods
    @objc_method
    def outlineView_child_ofItem_(self, tree, child: int, item):
        # Get the object representing the row
        if item is None:
            node = self.interface.data[child]
        else:
            node = item.attrs["node"][child]

        # Get the Cocoa implementation for the row. If an _impl
        # doesn't exist, create a data object for it, and
        # populate it with initial values for each column.
        try:
            node_impl = node._impl
        except AttributeError:
            node_impl = TogaData.alloc().init()
            node_impl.attrs = {"node": node}
            node._impl = node_impl

        return node_impl

    @objc_method
    def outlineView_isItemExpandable_(self, tree, item) -> bool:
        try:
            return item.attrs["node"].can_have_children()
        except AttributeError:
            return False

    @objc_method
    def outlineView_numberOfChildrenOfItem_(self, tree, item) -> int:
        if item is None:
            # How many root elements are there?
            # If we're starting up, the source may not exist yet.
            if self.interface.data is not None:
                return len(self.interface.data)
            else:
                return 0
        else:
            # How many children does this node have?
            return len(item.attrs["node"])

    @objc_method
    def outlineView_viewForTableColumn_item_(self, tree, column, item):

        interface_column = self._impl._column_for_identifier[str(column.identifier)]
        node = item.attrs["node"]

        # creates a NSTableCellView from interface-builder template (does not exist)
        # or reuses an existing view which is currently not needed for painting
        # returns None (nil) if both fails
        tcv = self.makeViewWithIdentifier(column.identifier, owner=self)

        if not tcv:  # there is no existing view to reuse so create a new one

            if isinstance(interface_column.renderer, (RendererText, RendererIconText)):
                tcv = TogaIconTextView.alloc().init()
                tcv.identifier = column.identifier
            else:
                self.interface.factory.not_implemented(
                    "Unsupported renderer {}".format(interface_column.renderer)
                )
                tcv = TogaIconTextView.alloc().init()
                tcv.identifier = column.identifier

        if type(interface_column.renderer) is RendererText:
            text = interface_column.renderer.text_for_row(node)
            tcv.setText(text)
            tcv.setImage(None)
        elif type(interface_column.renderer) is RendererIconText:
            text = interface_column.renderer.text_for_row(node)
            icon = interface_column.renderer.icon_for_row(node).bind(
                self.interface.factory
            )
            tcv.setText(text)
            tcv.setImage(icon.native)

        return tcv

    @objc_method
    def outlineView_heightOfRowByItem_(self, tree, item) -> float:
        return self.rowHeight

    @objc_method
    def outlineView_pasteboardWriterForItem_(self, tree, item) -> None:
        # this seems to be required to prevent issue 21562075 in AppKit
        return None

    @objc_method
    def keyDown_(self, event) -> None:
        # any time this table is in focus and a key is pressed, this method will be called
        if toga_key(event) == {"key": Key.A, "modifiers": {Key.MOD_1}}:
            if self.interface.multiple_select:
                self.selectAll(self)
        else:
            # forward call to super
            send_super(__class__, self, "keyDown:", event)

    # OutlineViewDelegate methods
    @objc_method
    def outlineViewSelectionDidChange_(self, notification) -> None:
        if notification.object.selectedRow == -1:
            selected = None
        else:
            selected = self.itemAtRow(notification.object.selectedRow).attrs["node"]

        if self.interface.on_select:
            self.interface.on_select(self.interface, node=selected)

    # target methods
    @objc_method
    def onDoubleClick_(self, sender) -> None:
        if self.clickedRow == -1:
            node = None
        else:
            node = self.itemAtRow(self.clickedRow).attrs["node"]

        if self.interface.on_double_click:
            self.interface.on_double_click(self.interface, node=node)


class Tree(Widget):
    def create(self):
        # Create a tree view, and put it in a scroll view.
        # The scroll view is the _impl, because it's the outer container.
        self.native = NSScrollView.alloc().init()
        self.native.hasVerticalScroller = True
        self.native.hasHorizontalScroller = False
        self.native.autohidesScrollers = False
        self.native.borderType = NSBezelBorder

        # Create the Tree widget
        self.tree = TogaTree.alloc().init()
        self.tree.interface = self.interface
        self.tree._impl = self
        self.tree.columnAutoresizingStyle = NSTableViewColumnAutoresizingStyle.Uniform
        self.tree.usesAlternatingRowBackgroundColors = True
        self.tree.allowsMultipleSelection = self.interface.multiple_select

        # Cocoa identifies columns by an accessor, create them here and save a map
        self._column_for_identifier = {}
        for column in self.interface.columns:
            column_identifier = to_accessor(column.title)
            self._column_for_identifier[column_identifier] = column

            native_column = NSTableColumn.alloc().initWithIdentifier(
                at(column_identifier)
            )
            native_column.minWidth = column.min_width
            native_column.maxWidth = column.max_width
            native_column.headerCell.stringValue = column.title
            self.tree.addTableColumn(native_column)

        # Put the tree arrows in the first column.
        self.tree.outlineTableColumn = self.tree.tableColumns[0]

        self.tree.delegate = self.tree
        self.tree.dataSource = self.tree
        self.tree.target = self.tree
        self.tree.doubleAction = SEL("onDoubleClick:")

        # Embed the tree view in the scroll view
        self.native.documentView = self.tree

        # Add the layout constraints
        self.add_constraints()

    def change_source(self, source):
        self.tree.reloadData()

    def insert(self, parent, index, item):
        # set parent = None if inserting to the root item
        index_set = NSIndexSet.indexSetWithIndex(index)
        if parent is self.interface.data:
            parent = None
        else:
            parent = getattr(parent, "_impl", None)

        self.tree.insertItemsAtIndexes(
            index_set,
            inParent=parent,
            withAnimation=NSTableViewAnimation.SlideDown.value,
        )

    def change(self, item):
        try:
            self.tree.reloadItem(item._impl)
        except AttributeError:
            pass

    def remove(self, parent, index, item):
        try:
            index = self.tree.childIndexForItem(item._impl)
        except AttributeError:
            pass
        else:
            index_set = NSIndexSet.indexSetWithIndex(index)
            parent = self.tree.parentForItem(item._impl)
            self.tree.removeItemsAtIndexes(
                index_set,
                inParent=parent,
                withAnimation=NSTableViewAnimation.SlideUp.value,
            )

    def clear(self):
        self.tree.reloadData()

    def get_selection(self):
        if self.interface.multiple_select:
            selection = []

            current_index = self.tree.selectedRowIndexes.firstIndex
            for i in range(self.tree.selectedRowIndexes.count):
                selection.append(self.tree.itemAtRow(current_index).attrs["node"])
                current_index = self.tree.selectedRowIndexes.indexGreaterThanIndex(
                    current_index
                )

            return selection
        else:
            index = self.tree.selectedRow
            if index != -1:
                return self.tree.itemAtRow(index).attrs["node"]
            else:
                return None

    def set_on_select(self, handler):
        pass

    def set_on_double_click(self, handler):
        pass

    def rehint(self):
        self.interface.intrinsic.width = at_least(self.interface.MIN_WIDTH)
        self.interface.intrinsic.height = at_least(self.interface.MIN_HEIGHT)


# ==== menus and status bar ==============================================================


class TogaMenuItem(NSMenuItem):
    @objc_method
    def onPress_(self, obj) -> None:
        if self.interface.action:
            self.interface.action(self.interface)


class MenuItem:
    def __init__(self, interface):
        self.interface = interface
        self.native = TogaMenuItem.alloc().init()

        self.native._impl = self
        self.native.interface = self.interface
        self.native.target = self.native
        self.native.action = SEL("onPress:")

    def set_enabled(self, enabled):
        self.native.enabled = enabled

    def set_icon(self, icon):
        if icon:
            factory = get_platform_factory()
            icon = icon.bind(factory)
            nsimage = icon.native.resizeTo(16)
            self.native.image = nsimage
        else:
            self.native.image = None

    def set_label(self, label):
        self.native.title = label

    def set_submenu(self, menu_impl):
        if menu_impl:
            self.native.submenu = menu_impl.native
            self.native.enabled = True
        else:
            self.native.submenu = None

    def set_action(self, action):
        pass

    def set_checked(self, yes):
        self.native.state = NSControlState(yes)


class MenuItemSeparator:
    def __init__(self, interface):
        self.interface = interface
        self.native = NSMenuItem.separatorItem()
        self.native.autoenablesItems = False


class TogaMenu(NSMenu):
    @objc_method
    def menuWillOpen_(self, obj) -> None:
        self._impl._visible = True
        if self.interface.on_open:
            self.interface.on_open(self.interface)

    @objc_method
    def menuDidClose_(self, obj) -> None:
        self._impl._visible = False
        if self.interface.on_close:
            self.interface.on_close(self.interface)


class Menu:
    def __init__(self, interface):
        self.interface = interface
        self._visible = False

        self.native = TogaMenu.alloc().init()
        self.native.autoenablesItems = False

        self.native._impl = self
        self.native.interface = self.interface
        self.native.delegate = self.native

    def add_item(self, item_impl):
        self.native.addItem(item_impl.native)

    def insert_item(self, index, item_impl):
        self.native.insertItem(item_impl.native, atIndex=index)

    def remove_item(self, item_impl):
        self.native.removeItem(item_impl.native)

    @property
    def visible(self):
        return self._visible


# ==== StatusBarItem =====================================================================


class StatusBarItem:
    MARGIN = 2

    def __init__(self, interface):
        self.interface = interface
        self.native = NSStatusBar.systemStatusBar.statusItemWithLength(
            NSSquareStatusItemLength
        )
        self.size = NSStatusBar.systemStatusBar.thickness

    def set_icon(self, icon):
        factory = get_platform_factory()
        icon = icon.bind(factory)
        nsimage = icon.native.resizeTo(self.size - 2 * self.MARGIN)
        nsimage.template = True
        self.native.button.image = icon.native

    def set_menu(self, menu_impl):
        self.native.menu = menu_impl.native


# ==== Application =======================================================================


class CocoaSystemTrayApp(NSApplication):
    @objc_method
    def sendEvent_(self, event) -> None:

        if event.type == NSKeyDown:
            toga_event = toga_key(event)
            if toga_event == {"key": Key.X, "modifiers": {Key.MOD_1}}:
                self.sendAction_to_from_(SEL("cut:"), None, self)
            elif toga_event == {"key": Key.C, "modifiers": {Key.MOD_1}}:
                self.sendAction_to_from_(SEL("copy:"), None, self)
            elif toga_event == {"key": Key.V, "modifiers": {Key.MOD_1}}:
                self.sendAction_to_from_(SEL("paste:"), None, self)
            elif toga_event == {"key": Key.Z, "modifiers": {Key.MOD_1}}:
                self.sendAction_to_from_(SEL("undo:"), None, self)
            elif toga_event == {"key": Key.Z, "modifiers": {Key.SHIFT, Key.MOD_1}}:
                self.sendAction_to_from_(SEL("redo:"), None, self)
            elif toga_event == {"key": Key.A, "modifiers": {Key.MOD_1}}:
                self.sendAction_to_from_(SEL("selectAll:"), None, self)
            else:
                send_super(__class__, self, "sendEvent:", event)
        else:
            send_super(__class__, self, "sendEvent:", event)


class SystemTrayAppDelegate(NSObject):
    @objc_method
    def applicationWillTerminate_(self, sender):
        if self.interface.app.on_exit:
            self.interface.app.on_exit(self.interface.app)

    @objc_method
    def applicationDidFinishLaunching_(self, notification):
        self.native.activateIgnoringOtherApps(True)


class SystemTrayApp(TogaApp):

    _MAIN_WINDOW_CLASS = None

    def create(self):
        self.native = CocoaSystemTrayApp.sharedApplication
        self.native.activationPolicy = NSApplicationActivationPolicyAccessory

        factory = get_platform_factory()
        self.interface.icon.bind(factory)
        self.native.applicationIconImage = self.interface.icon._impl.native

        self.resource_path = osp.dirname(osp.dirname(NSBundle.mainBundle.bundlePath))

        self.appDelegate = SystemTrayAppDelegate.alloc().init()
        self.appDelegate.impl = self
        self.appDelegate.interface = self.interface
        self.appDelegate.native = self.native
        self.native.delegate = self.appDelegate

        # Call user code to populate the main window
        self.interface.startup()

        # Create the lookup table of menu items,
        # then force the creation of the menus.
        self._menu_items = {}
        self.create_menus()

    def select_file(self):
        pass

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

        return await dialogs.alert_async(
            title,
            message,
            details,
            details_title,
            button_labels,
            checkbox_text,
            level,
            icon,
        )

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

        return dialogs.alert(
            title,
            message,
            details,
            details_title,
            button_labels,
            checkbox_text,
            level,
            icon,
        )


class Window(TogaWindow):
    def is_visible(self):
        return bool(self.native.isVisible)

    def center(self):
        self.native.center()

    def force_to_front(self):
        self.native.makeKeyAndOrderFront(None)
        self.native.orderFrontRegardless()
        if self.interface.app:
            self.interface.app._impl.native.activateIgnoringOtherApps(True)

    def show_as_sheet(self, window):
        window._impl.native.beginSheet(self.native, completionHandler=None)

    def hide(self):
        self.native.orderOut(None)

    def close(self):

        if self.native.sheetParent:
            # end sheet session before closing
            self.native.sheetParent.endSheet(self.native)

        self.native.close()

    def set_release_on_close(self, value):
        self.native.releasedWhenClosed = value

    def set_dialog(self, value):

        if value:
            self.native.animationBehavior = NSWindowAnimationBehaviorAlertPanel
        else:
            self.native.animationBehavior = NSWindowAnimationBehaviorDefault

        self.native.level = 3

    # dialogs

    async def save_file_sheet(self, title, message, suggested_filename, file_types):
        return await dialogs.save_file_sheet(
            self.interface, suggested_filename, title, message, file_types
        )

    async def open_file_sheet(
        self, title, message, initial_directory, file_types, multiselect
    ):
        return await dialogs.open_file_sheet(
            self.interface, title, message, file_types, multiselect
        )

    async def select_folder_sheet(self, title, message, initial_directory, multiselect):
        return await dialogs.select_folder_sheet(
            self.interface, title, message, multiselect
        )

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
        return await dialogs.alert_sheet(
            self.interface,
            title,
            message,
            details,
            details_title,
            button_labels,
            checkbox_text,
            level,
            icon,
        )


# ==== helpers ===========================================================================


def apply_round_clipping(image_view_impl: ImageView):
    """Clips an image in a given toga_cocoa.ImageView to a circular mask."""

    pool = NSAutoreleasePool.alloc().init()

    image = image_view_impl.native.image  # get native NSImage

    composed_image = NSImage.alloc().initWithSize(image.size)
    composed_image.lockFocus()

    ctx = NSGraphicsContext.currentContext
    ctx.saveGraphicsState()
    ctx.imageInterpolation = NSImageInterpolationHigh

    image_frame = NSRect(NSPoint(0, 0), image.size)
    clip_path = NSBezierPath.bezierPathWithRoundedRect(
        image_frame, xRadius=image.size.width / 2, yRadius=image.size.height / 2
    )
    clip_path.addClip()

    zero_rect = NSRect(NSPoint(0, 0), NSMakeSize(0, 0))
    image.drawInRect(
        image_frame, fromRect=zero_rect, operation=NSCompositeSourceOver, fraction=1
    )
    composed_image.unlockFocus()
    ctx.restoreGraphicsState()

    image_view_impl.native.image = composed_image

    pool.drain()
    del pool
