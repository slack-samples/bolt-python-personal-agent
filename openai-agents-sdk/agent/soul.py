from pathlib import Path

TEMPLATE_MARKER = "<!-- soul-template -->"

SOUL_PATH = Path(__file__).resolve().parent.parent / "soul.md"
TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "soul.template.md"


def load_soul(path: Path = SOUL_PATH) -> str:
    try:
        return path.read_text()
    except OSError:
        return TEMPLATE_PATH.read_text()


def save_soul(markdown: str, path: Path = SOUL_PATH) -> None:
    path.write_text(markdown)


def is_template(text: str) -> bool:
    return TEMPLATE_MARKER in text
