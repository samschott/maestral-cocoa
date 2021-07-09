# Python writes all console output to stdout/stderr. However, in production,
# iOS devices don't record stdout/stderr; only the Apple System Log is preserved.
#
# This handler redirects sys.stdout and sys.stderr to the Apple System Log
# by creating a wrapper around NSLog, and monkeypatching that wrapper over
# sys.stdout and sys.stderr
#
# It also installs a custom exception hook. This is done because there's
# no nice C API to generate the familiar Python traceback. The custom
# hook uses the Python API to generate a traceback, clean it up a little
# to remove details that aren't helpful, and annotate the resulting string
# onto the `sys` module as `sys._traceback`; this can be retrieved by the
# C API and used.

import io
import re
import sys
import traceback


# Install a custom exception hook.
def custom_exception_hook(exc_type, value, tb):
    # Drop the top two stack frames; these are internal
    # wrapper logic, and not in the control of the user.
    clean_tb = tb.tb_next.tb_next

    # Print the trimmed stack trace to a string buffer
    buffer = io.StringIO()
    traceback.print_exception(exc_type, value, clean_tb, file=buffer)

    # Also take the opportunity to clean up the source path,
    # so paths only refer to the "app local" path
    clean_traceback = re.sub(
        r'^  File \"/.*/(.*?).app/Contents/Resources/',
        r'  File "\1.app/Contents/Resources/',
        buffer.getvalue(),
        flags=re.MULTILINE,
    )

    # Annotate the clean traceback onto the sys module.
    sys._traceback = clean_traceback

    # Perform the default exception hook behavior
    # with the full original stack trace.
    sys.__excepthook__(exc_type, value, tb)

sys.excepthook = custom_exception_hook
