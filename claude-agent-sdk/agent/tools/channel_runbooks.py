from agent.deps import AgentDeps

RUNBOOK_PREFIX = "Runbook:"


def shared_in(runbook: dict) -> list[str]:
    return (
        (runbook.get("channels") or [])
        + (runbook.get("groups") or [])
        + (runbook.get("ims") or [])
    )


async def channel_runbooks(deps: AgentDeps) -> list[dict]:
    response = await deps.client.files_list(types="canvas", channel=deps.channel_id)
    return [
        file
        for file in response.get("files", [])
        if file.get("title", "").startswith(RUNBOOK_PREFIX)
        and deps.channel_id in shared_in(file)
    ]
