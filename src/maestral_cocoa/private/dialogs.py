from .platform import get_platform_factory


def alert(
    title,
    message,
    details=None,
    details_title="Traceback",
    button_labels=("Ok",),
    checkbox_text=None,
    level="info",
    icon=None,
):
    return get_platform_factory().alert(
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
    title,
    message,
    details=None,
    details_title="Traceback",
    button_labels=("Ok",),
    checkbox_text=None,
    level="info",
    icon=None,
):
    return await get_platform_factory().alert_async(
        title,
        message,
        details,
        details_title,
        button_labels,
        checkbox_text,
        level,
        icon,
    )
