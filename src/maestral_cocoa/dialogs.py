# -*- coding: utf-8 -*-

from __future__ import annotations

# system imports
from typing import Callable, Iterable

# external imports
import toga
from toga.style import Pack
from toga.constants import COLUMN, ROW, BOLD, CENTER, TRANSPARENT
import markdown2
from maestral import __version__
from maestral.daemon import MaestralProxy

# local imports
from . import __url__
from .private.widgets import (
    Window,
    DialogButtons,
    Label,
    FollowLinkButton,
    Icon,
)
from .private.constants import WORD_WRAP
from .utils import call_async_maestral
from .resources import RELEASE_NOTES_CSS_PATH


# System native dialogs are the preferred way of alerting the user. However, we use our
# own dialogs when those to static / inflexible to achieve our goal.


class Dialog(Window):
    """
    A generic dialog following cocoa's NSAlert style from macOS Catalina and lower.
    """

    WINDOW_WIDTH = 420
    WINDOW_MIN_HEIGHT = 150

    PADDING_TOP = 18
    PADDING_BOTTOM = 18
    PADDING_LEFT = 25
    PADDING_RIGHT = 20
    TITLE_PADDING_BOTTOM = 12

    ICON_SIZE = (60, 60)
    ICON_PADDING_RIGHT = 20

    CONTENT_WIDTH = (
        WINDOW_WIDTH - PADDING_LEFT - PADDING_RIGHT - ICON_PADDING_RIGHT - ICON_SIZE[0]
    )

    def __init__(
        self,
        title: str = "Alert",
        message: str = "",
        button_labels: Iterable[str] = ("Ok",),
        default: str = "Ok",
        accessory_view: toga.Widget = toga.Box(),
        icon: toga.Icon | None = None,
        callback: Callable | None = None,
        app: toga.App | None = None,
    ):
        super().__init__(
            resizeable=False,
            closeable=False,
            minimizable=False,
            title=" ",
            is_dialog=True,
            app=app,
        )

        if not callback:

            def callback(sender):
                self.close()

        self.resizeable = True
        self.size = (self.WINDOW_WIDTH, self.WINDOW_MIN_HEIGHT)

        if not icon:
            if self.app:
                icon = self.app.icon
            else:
                icon = Icon("")

        self.msg_title = Label(
            text=title,
            style=Pack(
                width=self.CONTENT_WIDTH,
                padding_bottom=self.TITLE_PADDING_BOTTOM,
                font_weight=BOLD,
                font_size=13,
                background_color=TRANSPARENT,
            ),
        )
        self.image = toga.ImageView(
            icon,
            style=Pack(
                width=self.ICON_SIZE[0],
                height=self.ICON_SIZE[1],
                padding_right=self.ICON_PADDING_RIGHT,
                background_color=TRANSPARENT,
            ),
        )
        self.msg_content = Label(
            text=message,
            linebreak_mode=WORD_WRAP,
            style=Pack(
                width=self.CONTENT_WIDTH,
                padding_bottom=10,
                font_size=11,
                flex=1,
                background_color=TRANSPARENT,
            ),
        )
        self.spinner = toga.ActivityIndicator(
            style=Pack(width=16, height=16, background_color=TRANSPARENT)
        )
        self.dialog_buttons = DialogButtons(
            labels=button_labels,
            default=default,
            on_press=callback,
            style=Pack(
                width=self.CONTENT_WIDTH,
                padding=0,
                alignment=CENTER,
                background_color=TRANSPARENT,
            ),
        )
        self.dialog_buttons.children.insert(0, self.spinner)

        self.accessory_view = accessory_view

        self.content_box = toga.Box(
            children=[
                self.msg_title,
                self.msg_content,
                self.accessory_view,
                self.dialog_buttons,
            ],
            style=Pack(
                direction=COLUMN,
                background_color=TRANSPARENT,
            ),
        )

        self.outer_box = toga.Box(
            children=[self.image, self.content_box],
            style=Pack(
                direction=ROW,
                padding=(
                    self.PADDING_TOP,
                    self.PADDING_RIGHT,
                    self.PADDING_BOTTOM,
                    self.PADDING_LEFT,
                ),
                background_color=TRANSPARENT,
            ),
        )

        self.content = self.outer_box
        self.center()


class ProgressDialog(Dialog):
    """A dialog to show progress."""

    def __init__(
        self,
        msg_title: str = "Progress",
        icon: toga.Icon = None,
        callback: Callable | None = None,
        app: toga.App | None = None,
    ) -> None:
        self.progress_bar = toga.ProgressBar(
            max=0,
            style=Pack(
                width=self.CONTENT_WIDTH,
                padding=(0, 0, 10, 0),
                background_color=TRANSPARENT,
            ),
        )
        self.progress_bar.start()

        super().__init__(
            title=msg_title,
            button_labels=("Cancel",),
            icon=icon,
            callback=callback,
            accessory_view=self.progress_bar,
            app=app,
        )

        # save some space...
        self.content_box.remove(self.msg_content)


class DetailedDialog(Dialog):
    """A generic dialog following cocoa NSAlert style, including a scroll view to
    display detailed text."""

    WINDOW_WIDTH = 650
    WINDOW_MIN_HEIGHT = 400

    CONTENT_WIDTH = (
        WINDOW_WIDTH
        - Dialog.PADDING_LEFT
        - Dialog.PADDING_RIGHT
        - Dialog.ICON_PADDING_RIGHT
        - Dialog.ICON_SIZE[0]
    )

    def __init__(
        self,
        title="Alert",
        message="",
        button_labels=("Ok",),
        default="Ok",
        icon=None,
        callback=None,
        details_title="Traceback",
        details="",
        app=None,
    ):
        label = Label(
            details_title,
            style=Pack(
                width=self.CONTENT_WIDTH,
                padding_bottom=10,
                font_size=12,
                font_weight=BOLD,
                background_color=TRANSPARENT,
            ),
        )

        html_view_height = self.WINDOW_MIN_HEIGHT - Dialog.WINDOW_MIN_HEIGHT - 15
        self.web_view = toga.WebView(
            style=Pack(
                width=self.CONTENT_WIDTH, height=html_view_height, padding_bottom=15
            ),
        )
        self.web_view.set_content("", details)
        accessory_view = toga.Box(
            children=[label, self.web_view], style=Pack(direction=COLUMN)
        )

        super().__init__(
            title=title,
            message=message,
            button_labels=button_labels,
            default=default,
            icon=icon,
            callback=callback,
            accessory_view=accessory_view,
            app=app,
        )


class UpdateDialog(Dialog):
    """A dialog to show available updates with release notes."""

    WINDOW_WIDTH = 700
    WINDOW_MIN_HEIGHT = 400

    CONTENT_WIDTH = (
        WINDOW_WIDTH
        - Dialog.PADDING_LEFT
        - Dialog.PADDING_RIGHT
        - Dialog.ICON_PADDING_RIGHT
        - Dialog.ICON_SIZE[0]
    )

    def __init__(
        self,
        version: str = "",
        release_notes: str = "",
        icon: toga.Icon | None = None,
        app: toga.App | None = None,
    ) -> None:
        link_button = FollowLinkButton(
            text="GitHub Releases",
            url=f"{__url__}/download",
            style=Pack(padding_bottom=10),
        )

        label = Label(
            "Release Notes",
            style=Pack(
                width=self.CONTENT_WIDTH,
                padding_bottom=10,
                font_size=12,
                font_weight=BOLD,
                background_color=TRANSPARENT,
            ),
        )

        html_notes = markdown2.markdown(release_notes)

        with open(RELEASE_NOTES_CSS_PATH) as f:
            release_notes_css = f.read()

        html_notes = f"""
        <html>
        <head>
        <style>{release_notes_css}</style>
        </head>
        <body>{html_notes}</body>
        </html>
        """

        html_view_height = self.WINDOW_MIN_HEIGHT - Dialog.WINDOW_MIN_HEIGHT - 15
        self.web_view = toga.WebView(
            style=Pack(
                width=self.CONTENT_WIDTH,
                height=html_view_height,
                padding_bottom=15,
                font_family="Helvetica Neue",
            ),
        )
        self.web_view.set_content("", html_notes)
        accessory_view = toga.Box(
            children=[link_button, label, self.web_view], style=Pack(direction=COLUMN)
        )

        message = (
            f"Maestral v{version} is available, you have v{__version__}. Please use "
            f"your package manager to update or download the latest binary from GitHub."
        )

        super().__init__(
            title="Update available",
            message=message,
            button_labels=("Ok",),
            icon=icon,
            accessory_view=accessory_view,
            app=app,
        )
        self.msg_content.style.padding_bottom = 0
        self.msg_content.style.font_size = 12
        self.msg_content.style.height = 40


class RelinkDialog(Dialog):
    """A dialog to relink Maestral."""

    EXPIRED = 0
    REVOKED = 1

    VALID_MSG = "Verified. Restarting Maestral..."
    INVALID_MSG = "Invalid token"
    CONNECTION_ERR_MSG = "Connection failed"

    LINK_BTN = "Link"
    CANCEL_BTN = "Cancel"
    UNLINK_BTN = "Unlink and Quit"

    CONTENT_WIDTH = 325

    def __init__(self, mdbx: MaestralProxy, app: toga.App, reason: int) -> None:
        self.mdbx = mdbx
        self.reason = reason

        url = self.mdbx.get_auth_url()

        if self.reason == self.EXPIRED:
            reason_str = "expired"
            title = "Dropbox Access Expired"
        elif self.reason == self.REVOKED:
            reason_str = "been revoked"
            title = "Dropbox Access Revoked"
        else:
            raise ValueError(f"Invalid reason {self.reason}")

        msg = (
            "Your Dropbox access has {0}. To continue syncing, please retrieve a new "
            "authorization token from Dropbox and enter it below."
        ).format(reason_str)

        self.website_button = FollowLinkButton(
            text="Retrieve Token", url=url, style=Pack(padding_bottom=10)
        )
        self.token_field = toga.TextInput(
            placeholder="Authorization token",
            on_change=self.token_field_validator,
            style=Pack(
                width=self.CONTENT_WIDTH,
                padding_bottom=20,
                background_color=TRANSPARENT,
            ),
        )

        token_box = toga.Box(
            children=[
                self.website_button,
                self.token_field,
            ],
            style=Pack(
                direction=COLUMN,
            ),
        )

        super().__init__(
            title=title,
            message=msg,
            accessory_view=token_box,
            button_labels=(self.LINK_BTN, self.CANCEL_BTN, self.UNLINK_BTN),
            callback=self.on_dialog_press,
            app=app,
        )

        self.dialog_buttons[self.LINK_BTN].enabled = False

    async def on_dialog_press(self, btn_name: str) -> None:
        self.dialog_buttons.enabled = False
        self.token_field.enabled = False
        self.spinner.start()

        if btn_name == self.CANCEL_BTN:
            await self.app.exit_and_stop_daemon()
        elif btn_name == self.UNLINK_BTN:
            await call_async_maestral(self.mdbx.config_name, "unlink")
            await self.app.exit_and_stop_daemon()
        elif btn_name == self.LINK_BTN:
            await self.do_relink()

    async def do_relink(self) -> None:
        token = self.token_field.value
        res = await call_async_maestral(self.mdbx.config_name, "link", token)

        self.spinner.stop()

        if res == 0:
            await self.info_dialog(
                title="Relink successful!",
                message="Click OK to restart.",
            )
            await self.app.restart()
        elif res == 1:
            await self.error_dialog(
                title="Invalid token",
                message="Please make sure you copy the correct token.",
            )
        elif res == 2:
            await self.error_dialog(
                title="Connection failed",
                message="Please check your internet connection.",
            )

        self.dialog_buttons[self.CANCEL_BTN].enabled = True
        self.dialog_buttons[self.UNLINK_BTN].enabled = True
        self.token_field.enabled = True

    def token_field_validator(self, widget: toga.TextInput) -> None:
        self.dialog_buttons[self.LINK_BTN].enabled = len(widget.value) > 10
