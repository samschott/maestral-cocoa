from importlib.resources import path


def resource_path(name: str) -> str:
    """Returns the resource path as a string. Extracts the resource if necessary."""
    return str(path("maestral_cocoa.resources", name).__enter__())


APP_ICON_PATH = resource_path("maestral.icns")
FACEHOLDER_PATH = resource_path("faceholder.pdf")
RELEASE_NOTES_CSS_PATH = resource_path("release_notes.css")
