# Personal Agent for Slack

A sample Slack agent built with [Bolt for Python](https://docs.slack.dev/tools/bolt-python/) that answers as your agent and keeps your runbooks current. Runbooks are Slack canvases titled `Runbook: <topic>`. The agent answers from them, and it learns from the messages in your channels, so the runbooks it writes are the ones it answers from next time.

## Choose Your Framework

This repo contains the app built with one AI agent framework:

| App | Directory | Get Started | Framework |
|-----|-----------|-------------|-----------|
| **OpenAI Agents SDK** | `openai-agents-sdk/` | [View README](./openai-agents-sdk/README.md) | [openai-agents](https://openai.github.io/openai-agents-python/) |

## Claude Code, Codex, Cursor, and Other Coding Agents

Install the [Slack MCP and Skills Plugin](https://docs.slack.dev/ai/slack-skills-plugin/) so your coding agent can create, run, and deploy Slack apps, look up Web API methods and scopes, and build Block Kit without guessing.

### Claude Code

Run this in a Claude Code session:

```
/plugin install slack@claude-plugins-official
```

### Codex

Run this in your terminal:

```sh
codex plugin marketplace add slackapi/slack-skills-plugin
codex plugin add slack@slack
```

### Cursor

Run this in a Cursor Agent chat:

```
/add-plugin slack
```

### Other agents

Install the skills with `npx skills`, using your [agent's identifier](https://github.com/vercel-labs/skills#supported-agents):

```sh
npx skills add slackapi/slack-skills-plugin -y -a <agent>

# For example, OpenCode
npx skills add slackapi/slack-skills-plugin -y -a opencode
```

## What It Can Do

The personal agent interacts with you through five entry points:

* **App Home** — Displays a welcome message with instructions on how to interact.
* **Direct Messages** — Message the agent directly to find a runbook or triage a request. It responds in-thread, maintaining context across follow-ups.
* **Channel @mentions** — Mention the agent in a channel with a request. It answers from a runbook when one covers it, or offers to start one.
* **Channel messages** — The agent follows along in channels it's a member of. When a message settles something worth keeping, the agent adds it to your runbooks on its own.
* **Assistant Panel** — Click _Add Agent_ in Slack, select the agent, and pick from suggested prompts or type a message.

With the bot token, the agent lists, reads, and creates runbooks. When you connect the [Slack MCP Server](https://github.com/slackapi/slack-mcp-server) from the Home tab, the agent works with runbooks as you instead, which can also update existing runbooks. When the agent changes a runbook, it tells you with an ephemeral message only you can see.

For full setup instructions, follow the [README in openai-agents-sdk/](./openai-agents-sdk/README.md).
