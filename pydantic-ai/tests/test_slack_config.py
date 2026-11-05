import json
from pathlib import Path

SLACK_CONFIG = Path(__file__).resolve().parent.parent / ".slack" / "config.json"


def test_slack_config_does_not_commit_a_project_id():
    config = json.loads(SLACK_CONFIG.read_text())
    assert config == {"manifest": {"source": "local"}}
