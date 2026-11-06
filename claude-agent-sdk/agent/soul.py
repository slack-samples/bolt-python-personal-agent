from pathlib import Path

TEMPLATE_MARKER = "<!-- soul-template -->"

SOUL_PATH = Path(__file__).resolve().parent.parent / "SOUL.md"
TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "SOUL.template.md"

FALLBACK_TEMPLATE = (
    f"{TEMPLATE_MARKER}\n# Soul\n\n## Identity\n\n## About me\n\n## Goals\n"
)


def load_soul(path: Path = SOUL_PATH) -> str:
    try:
        return path.read_text()
    except OSError:
        pass
    try:
        return TEMPLATE_PATH.read_text()
    except OSError:
        return FALLBACK_TEMPLATE


def save_soul(markdown: str, path: Path = SOUL_PATH) -> None:
    path.write_text(markdown)


def is_template(text: str) -> bool:
    return TEMPLATE_MARKER in text
