import sys

from termcolor import colored

UNICODE_MARKERS = {
    "error": "X",
    "success": "OK",
    "info": "i",
    "warning": "!",
    "question": "?",
}

ASCII_MARKERS = {
    "error": "[x]",
    "success": "[ok]",
    "info": "[i]",
    "warning": "[!]",
    "question": "[?]",
}


def _marker(kind: str, show_emoji: bool) -> str:
    if not show_emoji:
        return ""

    marker = UNICODE_MARKERS[kind]
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"

    try:
        marker.encode(encoding)
        return marker
    except (LookupError, UnicodeEncodeError):
        return ASCII_MARKERS[kind]


def error(message: str, show_emoji: bool = True) -> None:
    print(colored(f"{_marker('error', show_emoji)} {message}".strip(), "red"))


def success(message: str, show_emoji: bool = True) -> None:
    print(colored(f"{_marker('success', show_emoji)} {message}".strip(), "green"))


def info(message: str, show_emoji: bool = True) -> None:
    print(colored(f"{_marker('info', show_emoji)} {message}".strip(), "magenta"))


def warning(message: str, show_emoji: bool = True) -> None:
    print(colored(f"{_marker('warning', show_emoji)} {message}".strip(), "yellow"))


def question(message: str, show_emoji: bool = True) -> str:
    return input(colored(f"{_marker('question', show_emoji)} {message}".strip(), "magenta"))
