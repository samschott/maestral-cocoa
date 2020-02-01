# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 31 16:23:13 2018

@author: samschott
"""

import toga
from toga.style import Pack
from toga.constants import COLUMN, ROW, BOLD

from . import __url__
from .private_widgets import (
    Window, DialogButtons, VibrantBox,
    Label, RichMultilineTextInput, FollowLinkButton
)
from .private_constants import VisualEffectMaterial, WORD_WRAP
from .utils import clear_background, async_call, run_async, alert_sheet


# NSAlert's are the preferred way of alerting the user. However, we use our own dialogs
# in the following cases:
#
#  - NSAlert is to static / inflexible to achieve our goal (see RelinkDialog, Unlink).
#  - We want to show a dilaog from a async widget callback: this currently causes trouble
#    with Toga's handling of the event loop.
#  - We want to keep the event loop running while showing the dialog *and* we cannot
#    use an NSAlert as sheet.

class Dialog(Window):
    """A generic dialog following cocoa's NSAlert style."""

    WINDOW_WIDTH = 420
    WINDOW_MIN_HEIGHT = 150

    PADDING_TOP = 18
    PADDING_BOTTOM = 18
    PADDING_LEFT = 25
    PADDING_RIGHT = 20
    TITLE_PADDING_BOTTOM = 12

    ICON_SIZE = (60, 60)
    ICON_PADDING_RIGHT = 20

    CONTENT_WIDTH = (WINDOW_WIDTH - PADDING_LEFT - PADDING_RIGHT
                     - ICON_PADDING_RIGHT - ICON_SIZE[0])

    def __init__(self, title='Alert', message='', button_labels=('Ok',), default='Ok',
                 accessory_view=None, icon=None, callback=None, app=None):
        super().__init__(
            resizeable=False, closeable=False, minimizable=False, title=' ', app=app
        )
        self.is_dialog = True

        if not callback:
            def callback(sender):
                self.close()

        self.resizeable = True
        self.size = (self.WINDOW_WIDTH, self.WINDOW_MIN_HEIGHT)

        if not icon:
            if self.app:
                icon = self.app.icon
            else:
                icon = toga.Icon('')

        self.msg_title = Label(
            text=title,
            style=Pack(
                width=self.CONTENT_WIDTH,
                padding_bottom=self.TITLE_PADDING_BOTTOM,
                font_weight=BOLD,
                font_size=13
            ),
        )
        self.image = toga.ImageView(
            icon,
            style=Pack(
                width=self.ICON_SIZE[0],
                height=self.ICON_SIZE[1],
                padding_right=self.ICON_PADDING_RIGHT
            )
        )
        self.msg_content = Label(
            text=message,
            linebreak_mode=WORD_WRAP,
            style=Pack(width=self.CONTENT_WIDTH, padding_bottom=10, font_size=11, flex=1)
        )
        self.spinner = toga.ActivityIndicator(style=Pack(width=16, height=16))
        self.dialog_buttons = DialogButtons(
            labels=button_labels,
            default=default,
            on_press=callback,
            style=Pack(width=self.CONTENT_WIDTH, padding=0)
        )
        self.dialog_buttons.children.insert(0, self.spinner)

        self.accessory_view = accessory_view or toga.Box()

        self.content_box = toga.Box(
            children=[
                self.msg_title,
                self.msg_content,
                self.accessory_view,
                self.dialog_buttons,
            ],
            style=Pack(direction=COLUMN)
        )

        self.outer_box = toga.Box(
            children=[self.image, self.content_box],
            style=Pack(
                direction=ROW,
                padding=(
                    self.PADDING_TOP, self.PADDING_RIGHT,
                    self.PADDING_BOTTOM, self.PADDING_LEFT
                )
            )
        )

        clear_background(self.outer_box)

        self.content = VibrantBox(
            children=[self.outer_box],
            material=VisualEffectMaterial.WindowBackground
        )
        self.center()

    def show_as_sheet(self, window):
        # change the background material to translucent sheet
        self.content.material = VisualEffectMaterial.Sheet
        super().show_as_sheet(window)

    def show(self):
        # change the background material to opaque window background
        self.content.material = VisualEffectMaterial.WindowBackground
        super().show()


class ProgressDialog(Dialog):
    """A dialog to relink Maestral."""

    def __init__(self, msg_title='Progress', icon=None, callback=None, app=None):

        self.progress_bar = toga.ProgressBar(
            running=False, max=0,
            style=Pack(width=self.CONTENT_WIDTH, padding=(0, 0, 10, 0))
        )
        self.progress_bar.start()

        super().__init__(
            title=msg_title, button_labels=('Cancel',), icon=icon,
            callback=callback, accessory_view=self.progress_bar, app=app
        )

        self.msg_content.style.height = 0
        self.outer_box.refresh()


class DetailedDialog(Dialog):
    """A generic dialog following cocoa NSAlert style, inlcuding a scroll view to
    display detailed text."""

    WINDOW_WIDTH = 650
    WINDOW_MIN_HEIGHT = 400

    CONTENT_WIDTH = (WINDOW_WIDTH - Dialog.PADDING_LEFT - Dialog.PADDING_RIGHT
                     - Dialog.ICON_PADDING_RIGHT - Dialog.ICON_SIZE[0])

    def __init__(self, title='Alert', message='', button_labels=('Ok',), default='Ok',
                 icon=None, callback=None, details_title='Traceback', details='', app=None):

        label = Label(
            details_title,
            style=Pack(
                width=self.CONTENT_WIDTH,
                padding_bottom=10,
                font_size=12, font_weight=BOLD
            )
        )
        clear_background(label)

        text_view_height = self.WINDOW_MIN_HEIGHT - Dialog.WINDOW_MIN_HEIGHT - 15
        text_view = RichMultilineTextInput(
            details,
            readonly=True,
            style=Pack(width=self.CONTENT_WIDTH, height=text_view_height, padding_bottom=15)
        )
        accessory_view = toga.Box(
            children=[label, text_view],
            style=Pack(direction=COLUMN)
        )

        super().__init__(
            title=title, message=message, button_labels=button_labels,
            default=default, icon=icon, callback=callback, accessory_view=accessory_view,
            app=app
        )


class UpdateDialog(Dialog):

    WINDOW_WIDTH = 700
    WINDOW_MIN_HEIGHT = 400

    CONTENT_WIDTH = (WINDOW_WIDTH - Dialog.PADDING_LEFT - Dialog.PADDING_RIGHT
                     - Dialog.ICON_PADDING_RIGHT - Dialog.ICON_SIZE[0])

    def __init__(self, message='', release_notes='', icon=None, app=None):

        link_button = FollowLinkButton(
            label='GitHub Releases',
            url=__url__ + '/releases',
            style=Pack(padding_bottom=10),
        )

        label = Label(
            'Realese Notes',
            style=Pack(width=self.CONTENT_WIDTH, padding_bottom=10, font_size=12, font_weight=BOLD)
        )
        clear_background(label)

        text_view_height = self.WINDOW_MIN_HEIGHT - Dialog.WINDOW_MIN_HEIGHT - 15
        text_view = RichMultilineTextInput(
            html=release_notes,
            readonly=True,
            style=Pack(width=self.CONTENT_WIDTH, height=text_view_height, padding_bottom=15)
        )
        accessory_view = toga.Box(
            children=[link_button, label, text_view],
            style=Pack(direction=COLUMN)
        )

        super().__init__(
            title='Update available', message=message, button_labels=('Ok',),
            icon=icon, accessory_view=accessory_view, app=app
        )
        self.msg_content.style.padding_bottom = 0


class RelinkDialog(Window):
    """A dialog to relink Maestral."""

    EXPIRED = 0
    REVOKED = 1

    VALID_MSG = 'Verified. Restarting Maestral...'
    INVALID_MSG = 'Invalid token'
    CONNECTION_ERR_MSG = 'Connection failed'

    LINK_BTN = 'Link'
    CANCEL_BTN = 'Cancel'
    UNLINK_BTN = 'Unlink and Quit'

    CONTENT_WIDTH = 390

    def __init__(self, mdbx, reason, app):
        super().__init__(title='Relink Maestral', closeable=False, minimizable=False,
                         resizeable=False, app=app)
        self.is_dialog = True

        self.mdbx = mdbx
        self.reason = reason

        from maestral.sync.oauth import OAuth2Session
        self.auth_session = OAuth2Session(self.mdbx.config_name)
        url = self.auth_session.get_auth_url()

        if self.reason == self.EXPIRED:
            reason = 'expired'
            title = 'Dropbox Access Expired'
        elif self.reason == self.REVOKED:
            reason = 'been revoked'
            title = 'Dropbox Access Revoked'
        else:
            raise ValueError(f'Invalid reason {self.reason}')

        msg = ('Your Dropbox access has {0}. To continue syncing, please retrieve a new '
               'authorization token from Dropbox and enter it below.').format(reason, url)

        self.msg_title = Label(
            text=title,
            style=Pack(
                width=self.CONTENT_WIDTH,
                padding_bottom=10,
                font_weight=BOLD, font_size=13
            ),
        )
        self.image = toga.ImageView(
            self.app.icon,
            style=Pack(width=60, height=60, padding_right=20)
        )
        self.info = Label(
            text=msg,
            linebreak_mode=WORD_WRAP,
            style=Pack(width=self.CONTENT_WIDTH, padding_bottom=10, font_size=12, flex=1)
        )
        self.wesbsite_button = FollowLinkButton(
            label='Retrieve Token', url=url, style=Pack(padding_bottom=10)
        )
        self.token_field = toga.TextInput(
            placeholder='Authorization token',
            on_change=self.token_field_validator,
            style=Pack(width=self.CONTENT_WIDTH, padding_bottom=20)
        )
        self.spinner = toga.ActivityIndicator(style=Pack(width=16, height=16))
        self.dialog_buttons = DialogButtons(
            labels=[self.LINK_BTN, self.CANCEL_BTN, self.UNLINK_BTN],
            on_press=self.on_dialog_press,
            style=Pack(width=self.CONTENT_WIDTH)
        )
        self.dialog_buttons[self.LINK_BTN].enabled = False
        self.dialog_buttons.children.insert(0, self.spinner)

        action_box = toga.Box(
            children=[
                self.msg_title,
                self.info,
                self.wesbsite_button,
                self.token_field,
                self.dialog_buttons,
            ],
            style=Pack(direction=COLUMN)
        )

        outer_box = toga.Box(
            children=[self.image, action_box],
            style=Pack(direction=ROW, padding=20)
        )

        self.content = outer_box

    def on_dialog_press(self, btn_name):
        if btn_name == self.CANCEL_BTN:
            self.app.exit()
        elif btn_name == self.UNLINK_BTN:
            self.auth_session.delete_creds()
            self.app.exit()
        elif btn_name == self.LINK_BTN:
            self.do_relink()

    @async_call
    async def do_relink(self):

        from maestral.sync.oauth import OAuth2Session

        self.dialog_buttons[self.LINK_BTN].enabled = False
        self.dialog_buttons[self.CANCEL_BTN].enabled = False
        self.dialog_buttons[self.UNLINK_BTN].enabled = False
        self.token_field.enabled = False

        self.spinner.start()

        token = self.token_field.value
        res = await run_async(self.auth_session.verify_auth_token, token)

        self.spinner.stop()

        if res == OAuth2Session.Success:
            self.auth_session.save_creds()
            alert_sheet(
                window=self,
                title='Relink successfull!',
                message='Click OK to restart.',
                callback=self.app.restart,
                icon=self.app.icon,
            )
        elif res == OAuth2Session.InvalidToken:
            alert_sheet(
                window=self,
                title='Invalid token',
                message='Please make sure you copy the correct token.',
                icon=self.app.icon,
            )
        elif res == OAuth2Session.ConnectionFailed:
            alert_sheet(
                window=self,
                title='Connection failed',
                message='Please check your internet connection.',
                icon=self.app.icon,
            )

        self.token_field.enabled = True

    def token_field_validator(self, widget):
        self.dialog_buttons[self.LINK_BTN].enabled = len(widget.value) > 10
