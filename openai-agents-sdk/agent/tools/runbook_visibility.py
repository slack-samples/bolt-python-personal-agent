from slack_sdk.errors import SlackApiError

from agent.deps import AgentDeps

RUNBOOK_PREFIX = "Runbook:"


def visible_runbooks(deps: AgentDeps) -> list[dict]:
    response = deps.client.files_list(types="canvas")

    all_files = response.get("files", [])
    runbooks = [
        file for file in all_files if file.get("title", "").startswith(RUNBOOK_PREFIX)
    ]

    visible = set()
    for runbook in runbooks:
        shared_in = runbook.get("channels", []) + runbook.get("groups", [])
        if runbook.get("channels") or deps.channel_id in shared_in:
            visible.add(runbook["id"])

    if deps.is_private_reply:
        try:
            user_channels = []
            cursor = None
            while True:
                kwargs = {
                    "user": deps.user_id,
                    "types": "public_channel,private_channel",
                    "limit": 1000,
                }
                if cursor:
                    kwargs["cursor"] = cursor
                response = deps.client.users_conversations(**kwargs)
                user_channels.extend(response.get("channels", []))
                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break

            user_channel_ids = {ch["id"] for ch in user_channels}
            for runbook in runbooks:
                shared_in = runbook.get("channels", []) + runbook.get("groups", [])
                if any(ch_id in user_channel_ids for ch_id in shared_in):
                    visible.add(runbook["id"])
        except SlackApiError:
            pass

    return [r for r in runbooks if r["id"] in visible]
