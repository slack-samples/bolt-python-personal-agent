from slack_sdk.errors import SlackApiError

from agent.deps import AgentDeps

RUNBOOK_PREFIX = "Runbook:"


def shared_in(runbook: dict) -> list[str]:
    return (runbook.get("channels") or []) + (runbook.get("groups") or [])


def is_public_channel(deps: AgentDeps, channel_id: str) -> bool:
    try:
        response = deps.client.conversations_info(channel=channel_id)
        return response["channel"]["is_private"] is False
    except (SlackApiError, KeyError, TypeError):
        return False


def visible_runbooks(deps: AgentDeps) -> list[dict]:
    response = deps.client.files_list(types="canvas")

    all_files = response.get("files", [])
    runbooks = [
        file for file in all_files if file.get("title", "").startswith(RUNBOOK_PREFIX)
    ]

    public_cache: dict[str, bool] = {}

    def is_public(channel_id: str) -> bool:
        if channel_id not in public_cache:
            public_cache[channel_id] = is_public_channel(deps, channel_id)
        return public_cache[channel_id]

    visible = set()
    for runbook in runbooks:
        if deps.channel_id in shared_in(runbook) or any(
            is_public(channel_id) for channel_id in runbook.get("channels") or []
        ):
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
                if any(ch_id in user_channel_ids for ch_id in shared_in(runbook)):
                    visible.add(runbook["id"])
        except SlackApiError:
            pass

    return [r for r in runbooks if r["id"] in visible]
