from pathlib import Path

SOUL_PATH = Path(__file__).resolve().parent.parent / "SOUL.md"
TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "SOUL.template.md"

FALLBACK_TEMPLATE = "# Soul\n\n## Identity\n\n## About me\n\n## Goals\n"


def load_template() -> str:
    try:
        return TEMPLATE_PATH.read_text()
    except OSError:
        return FALLBACK_TEMPLATE


def load_soul(path: Path = SOUL_PATH) -> str:
    try:
        return path.read_text()
    except OSError:
        return load_template()


def save_soul(markdown: str, path: Path = SOUL_PATH) -> None:
    path.write_text(markdown)


def is_template(text: str) -> bool:
    return text.strip() == load_template().strip()
