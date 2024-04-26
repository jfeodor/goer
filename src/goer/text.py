"""Text output helpers."""


class TextMode:
    """Terminal escape codes for colorizing terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREY = "\033[90m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[95m"


COLORS = [
    TextMode.GREY,
    TextMode.RED,
    TextMode.GREEN,
    TextMode.YELLOW,
    TextMode.BLUE,
    TextMode.PURPLE,
    TextMode.CYAN,
    TextMode.WHITE,
]
"""All `TextMode` values, which are colors."""


def print_header(*args: str) -> None:
    """Prints a pretty header message."""
    msgs = []
    for arg in args:
        msgs.append(arg)
        msgs.append(TextMode.RESET)
        msgs.append(TextMode.BOLD)
    print(TextMode.BOLD, "--- ", *msgs, TextMode.RESET, sep="")


def print_error(*args: str) -> None:
    """Prints a pretty error message."""
    msgs = []
    for arg in args:
        msgs.append(arg)
        msgs.append(TextMode.RED)
    print(TextMode.BOLD, TextMode.RED, "--- ", *msgs, TextMode.RESET, sep="")
