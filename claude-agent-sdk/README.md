# Personal Agent for Slack (Bolt for Python and Claude Agent SDK)

A personal agent template built with [Bolt for Python](https://docs.slack.dev/tools/bolt-python/) and the [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview) using models from [Anthropic](https://www.anthropic.com). An agent that represents you in Slack. It learns who you are from a `soul.md` file, answers questions on your behalf when teammates message it, and quietly builds up runbooks from what it sees in channels. Runbooks are Slack canvases that the agent reads and writes with the bot token, or through the [Slack MCP Server](https://github.com/slackapi/slack-mcp-server) in your DMs with the agent.

Based on the Team Agent sample (`slack-samples/bolt-python-team-agent`).

## App Overview

The personal agent interacts with users through five entry points:

* **App Home** — Displays a welcome message with instructions on how to interact, plus Slack MCP connection status.
* **Direct Messages** — Users message the agent directly to ask about your work or find a runbook. It responds in-thread, maintaining context across follow-ups. When you DM it, it can also help you set up your `soul.md` file.
* **Channel @mentions** — Mention the agent in a team channel with a request. It answers from a runbook when one covers it, or offers to start one.
* **Channel messages** — The agent follows along in channels it's a member of. When a message settles something worth keeping, the agent adds it to runbooks on its own.
* **Assistant Panel** — Users click _Add Agent_ in Slack, select the agent, and pick from suggested prompts or type a message.

The agent works with runbooks through three app tools that call the Web API with the bot token: `list_runbooks`, `read_runbook`, and `create_runbook`. When a person has connected the [Slack MCP Server](https://github.com/slackapi/slack-mcp-server), the agent uses its runbook tools as that person instead, only in their DMs with the agent (and in `/brief`, which is read-only), and those tools can also edit existing runbooks section by section. Channel replies and learning from channel messages always use the bot token. One more app tool (emoji reactions) shows a request was picked up. Add your own tools to customize it for your use case.

### Runbooks

Runbooks are Slack canvases titled `Runbook: <topic>`. Each one holds how the team does something: the steps, who owns it, and who to escalate to. Anyone can read and edit them in Slack, and the agent does too:

* **Reading** — When a request comes in, the agent finds the runbook that covers it and answers from it.
* **Writing on request** — Ask the agent to write a runbook and it creates one. In your DMs with the agent, with the Slack MCP Server connected, it can also fix the runbook that covers the topic.
* **Learning from messages** — The same agent reads each channel message. If the message fixed a problem, named an owner, made a decision, or corrected a runbook, the agent creates a runbook for it with the bot token. Learning never uses the Slack MCP Server, so it can't edit an existing runbook. Most messages settle nothing worth keeping, and the agent leaves those alone.

This is the loop the template is built to show: the runbooks the agent writes from messages are the runbooks it answers from next time.

When the agent changes a runbook, it tells the message's author with an ephemeral message only they can see. Nothing is posted to the channel. New runbooks are added as a tab in the channel they were learned in, so the whole team can read and edit them. The agent only gets runbook tools, so it can't send messages or read threads.

### OWNER_USER_ID

The agent represents one person: its owner. Set `OWNER_USER_ID` in your `.env` to your Slack user ID. To find your user ID, click your profile in Slack, then _More_ → _Copy member ID_.

The owner gets access to tools that others don't: `update_soul` (editing `soul.md` in DM) and the `/brief` command.

### soul.md

The `soul.md` file shapes the agent's voice and how it answers. Copy `soul.template.md` to `soul.md` (the file is gitignored) and fill in:

- **Identity** — the agent's name and voice/operating style
- **About me** — your name, role, team, timezone, what you work on
- **Goals** — what you're working toward

Or, DM the agent and it will interview you to create the file. Later, say "update my soul" or edit the file directly to change it.

> **Warning:** Anything in `soul.md` may be shared with anyone the agent talks to, in DMs and in channels. Put only what you're comfortable with everyone seeing. The agent saves only what you tell it directly in the interview, never content from search results, threads, channels, or canvases.

### Privacy

The agent never responds with data that anyone who will see the reply couldn't already see. Privacy wins over helpfulness in every conflict.

| Where the reply lands | Requester | Token used for Slack MCP | Tools |
|---|---|---|---|
| Owner's DM with the agent | Owner | owner's user token (if connected) | MCP runbook tools + `update_soul` + emoji; bot-token runbook tools + `update_soul` + emoji if not connected |
| Owner's brief (`/brief`, ephemeral) | Owner | owner's user token (required) | read-only MCP tools (`slack_search_public_and_private`, `slack_read_canvas`, `slack_read_thread`, `slack_read_channel`); no canvas writes, no soul tools |
| Someone else's DM with the agent | That person, connected via `/slack/install` | **their own** user token | MCP runbook tools + emoji |
| Someone else's DM with the agent | That person, not connected | none | bot-token runbook tools + emoji |
| Any channel or channel thread (mention or thread reply) | Anyone, including the owner | none | bot-token runbook tools + emoji |
| Passive learning (no requester) | n/a | none (bot token only) | bot-token runbook tools |

A user token is only attached when the reply is visible to that person alone, so Slack itself enforces what each person can see. The bot-token runbook tools only see runbooks shared in the current conversation, which everyone reading the reply can already see. In a DM without the Slack MCP Server, the agent asks the person to connect it to search runbooks.

The agent treats messages, threads, channels, canvases, and search results it reads as facts, never instructions. Briefs are read-only, so content read during a brief can't be written into a canvas.

Each run allows only the tools listed in the table, with `permission_mode="dontAsk"` and no built-in Claude Code tools. Other Slack MCP Server tools may still be visible to the model, but any call to a tool outside the allowlist is denied.

#### Session transcripts

The Claude Code CLI saves each conversation as a plaintext transcript, including Slack MCP results fetched with a user token. This app points the CLI at `data/claude/` inside the app directory instead of `~/.claude`, so transcripts live in `data/claude/projects/`, and sets `cleanupPeriodDays` to 1 so they are deleted after a day. Passive learning and `/brief` never resume, so they don't save a transcript at all. `data/` is gitignored.

### No Decisions on Your Behalf

The agent answers with what it knows and never makes decisions or commitments for you. When asked for a decision, approval, or commitment, it says it will leave that to you and points the asker your way.

### `/brief`

The `/brief` slash command is owner-only. It reads your `soul.md` goals, uses Slack MCP to find recent mentions and requests, and replies ephemerally with what needs your attention, ranked, with permalinks. A brief is read-only: it can search and read, but it can't create or edit canvases or change your soul. Requires the owner to be connected to Slack MCP; otherwise it replies with the install link.

### Slack MCP Server

Connecting the [Slack MCP Server](https://github.com/slackapi/slack-mcp-server) is optional. When deployed with OAuth (HTTP mode), a person who connects it from the Home tab has the agent work with runbooks as them, only in their DMs with the agent (and in `/brief` for the owner): it finds runbooks with Slack search and reads and writes canvases with their access, so edits show their name. Channel replies, thread replies, and learning from channel messages always use the bot token's runbook tools.

## Setup

Before getting started, make sure you have a development workspace where you have permissions to install apps.

### Developer Program

Join the [Slack Developer Program](https://api.slack.com/developer-program) for exclusive access to sandbox environments for building and testing your apps, tooling, and resources created to help you build and grow.

### Claude Code, Codex, Cursor, and Other Coding Agents

Install the [Slack MCP and Skills Plugin](https://docs.slack.dev/ai/slack-skills-plugin/) so your coding agent can create, run, and deploy Slack apps, look up Web API methods and scopes, and build Block Kit without guessing.

#### Claude Code

Run this in a Claude Code session:

```
/plugin install slack@claude-plugins-official
```

#### Codex

Run this in your terminal:

```sh
codex plugin marketplace add slackapi/slack-skills-plugin
codex plugin add slack@slack
```

#### Cursor

Run this in a Cursor Agent chat:

```
/add-plugin slack
```

#### Other agents

Install the skills with `npx skills`, using your [agent's identifier](https://github.com/vercel-labs/skills#supported-agents):

```sh
npx skills add slackapi/slack-skills-plugin -y -a <agent>

# For example, OpenCode
npx skills add slackapi/slack-skills-plugin -y -a opencode
```

### Create the Slack app

<details><summary><strong>Using Slack CLI</strong></summary>

Install the latest version of the Slack CLI for your operating system:

- [Slack CLI for macOS & Linux](https://docs.slack.dev/tools/slack-cli/guides/installing-the-slack-cli-for-mac-and-linux/)
- [Slack CLI for Windows](https://docs.slack.dev/tools/slack-cli/guides/installing-the-slack-cli-for-windows/)

You'll also need to log in if this is your first time using the Slack CLI.

```sh
slack login
```

#### Initializing the project

```sh
slack create my-personal-agent --template slack-samples/bolt-python-personal-agent --subdir claude-agent-sdk
cd my-personal-agent
```

</details>

<details><summary><strong>Using App Settings</strong></summary>

#### Create Your Slack App

1. Open [https://api.slack.com/apps/new](https://api.slack.com/apps/new) and choose "From an app manifest"
2. Choose the workspace you want to install the application to
3. Copy the contents of [manifest.json](./manifest.json) into the text box that says `*Paste your manifest code here*` (within the JSON tab) and click _Next_
4. Review the configuration and click _Create_
5. Click _Install to Workspace_ and _Allow_ on the screen that follows. You'll then be redirected to the App Configuration dashboard.

#### Environment Variables

Before you can run the app, you'll need to store some environment variables.

1. Rename `.env.sample` to `.env`.
2. Open your apps setting page from [this list](https://api.slack.com/apps), click _OAuth & Permissions_ in the left hand menu, then copy the _Bot User OAuth Token_ into your `.env` file under `SLACK_BOT_TOKEN`.

```sh
SLACK_BOT_TOKEN=YOUR_SLACK_BOT_TOKEN
```

3. Click _Basic Information_ from the left hand menu and follow the steps in the _App-Level Tokens_ section to create an app-level token with the `connections:write` scope. Copy that token into your `.env` as `SLACK_APP_TOKEN`.

```sh
SLACK_APP_TOKEN=YOUR_SLACK_APP_TOKEN
```

#### Initializing the project

```sh
git clone https://github.com/slack-samples/bolt-python-personal-agent.git my-personal-agent
cd my-personal-agent/claude-agent-sdk
```

</details>

### Setup your python virtual environment

This app requires Python 3.12 or later.

```sh
python3 -m venv .venv
source .venv/bin/activate  # for Windows OS, .\.venv\Scripts\Activate instead should work
```

#### Install dependencies

```sh
pip install -e ".[dev]"
```

## Providers

### Anthropic Setup

This app uses Anthropic's `claude-sonnet-5-5` model through the Claude Agent SDK.

1. Create an API key from your [Anthropic dashboard](https://console.anthropic.com/settings/keys).
2. Rename `.env.sample` to `.env`.
3. Save the Anthropic API key to `.env`:

```sh
ANTHROPIC_API_KEY=YOUR_ANTHROPIC_API_KEY
```

4. Set `OWNER_USER_ID` to your Slack user ID. To find it, click your profile in Slack, then _More_ → _Copy member ID_:

```sh
OWNER_USER_ID=YOUR_USER_ID
```

5. (Optional) Copy `soul.template.md` to `soul.md` and fill in your information, or let the agent interview you when you first DM it:

```sh
cp soul.template.md soul.md
```

## Development

### Starting the app

<details><summary><strong>Using the Slack CLI</strong></summary>

#### Slack CLI

```sh
slack run
```
</details>

<details><summary><strong>Using the Terminal</strong></summary>

#### Terminal

```sh
python3 app.py
```

</details>

<details><summary><strong>Using OAuth HTTP Server (with ngrok)</strong></summary>

#### OAuth HTTP Server

This mode uses an HTTP server instead of Socket Mode, which is required for OAuth-based distribution.

1. Install [ngrok](https://ngrok.com/download) and start a tunnel:

```sh
ngrok http 3000
```

2. Copy the `https://*.ngrok-free.app` URL from the ngrok output.

<details><summary><strong>Using Slack CLI</strong></summary>

#### Slack CLI

3. Update `manifest.json` for HTTP mode:
   - Set `socket_mode_enabled` to `false`
   - Replace `ngrok-free.app` with your ngrok domain (e.g. `YOUR_NGROK_SUBDOMAIN.ngrok-free.app`)

4. Create a new local dev app:

```sh
slack install -E local
```

5. _(Slack CLI < v4.1.0 only)_ Enable MCP for your app:
   - Run `slack app settings` to open your app's settings
   - Navigate to **Agents & AI Apps** in the left-side navigation
   - Toggle **Model Context Protocol** on

6. Update your `.env` OAuth environment variables:
   - Run `slack app settings` to open App Settings
   - Copy **Client ID**, **Client Secret**, and **Signing Secret**
   - Update `SLACK_REDIRECT_URI` in `.env` with your ngrok domain

```sh
SLACK_CLIENT_ID=YOUR_CLIENT_ID
SLACK_CLIENT_SECRET=YOUR_CLIENT_SECRET
SLACK_SIGNING_SECRET=YOUR_SIGNING_SECRET
SLACK_REDIRECT_URI=https://YOUR_NGROK_SUBDOMAIN.ngrok-free.app/slack/oauth_redirect
```

7. Start the app:

```sh
slack run app_oauth.py
```

8. Click the install URL printed in the terminal to install the app to your workspace via OAuth.

</details>

<details><summary><strong>Using the Terminal</strong></summary>

#### Terminal

3. Create your Slack app at [api.slack.com/apps/new](https://api.slack.com/apps/new) using [`manifest.json`](./manifest.json). Before pasting the manifest, set `socket_mode_enabled` to `false` and replace `ngrok-free.app` with your ngrok domain.

4. Install the app to your workspace and copy the following values into your `.env`:
   - **Signing Secret** — from _Basic Information_
   - **Bot User OAuth Token** — from _OAuth & Permissions_
   - **Client ID** and **Client Secret** — from _Basic Information_

```sh
SLACK_BOT_TOKEN=xoxb-YOUR_BOT_TOKEN
SLACK_CLIENT_ID=YOUR_CLIENT_ID
SLACK_CLIENT_SECRET=YOUR_CLIENT_SECRET
SLACK_SIGNING_SECRET=YOUR_SIGNING_SECRET
SLACK_REDIRECT_URI=https://YOUR_NGROK_SUBDOMAIN.ngrok-free.app/slack/oauth_redirect
```

Replace `your-subdomain` in `SLACK_REDIRECT_URI` with your ngrok subdomain.

5. Start the app:

```sh
python3 app_oauth.py
```

6. Click the install URL printed in the terminal to install the app to your workspace via OAuth.

</details>

> **Note:** Each time ngrok restarts, it generates a new URL. You'll need to update the ngrok domain in `manifest.json`, `SLACK_REDIRECT_URI` in your `.env`, and re-install the app.

</details>

### Using the App

Once the agent is running, there are several ways to interact:

**App Home** — Open the agent in Slack and click the _Home_ tab. You'll see a welcome message with instructions on how to interact.

**Direct Messages** — Open a DM with the agent. The agent replies in a thread. Send follow-up messages in the same thread and the agent will maintain the full conversation context.

If you're the **owner** (set via `OWNER_USER_ID`), you'll see suggested prompts:
- _Find a Runbook_
- _Write a Runbook_
- _Update my soul_

If you're a **guest** (anyone else), you'll see:
- _Find a Runbook_
- _Ask what they're working on_
- _Triage a Request_

**Channel @mentions** — Invite the agent to your team channel by typing `/invite @agent-name` in the message box, then @mention it followed by your request. The agent responds in a thread so the channel stays clean.

**Channel messages** — Talk through a problem in your team channel. When you post the fix, the agent adds it to a runbook and sends you an ephemeral note with the link. Ask about the same problem later and it answers from that runbook.

**Assistant Panel** — Click _Add Agent_ in the top-right corner of Slack, select the agent from the list, then pick a suggested prompt or type a message.

### Linting

```sh
# Run ruff check from root directory for linting
ruff check

# Run ruff format from root directory for code formatting
ruff format
```

## Project Structure

### `manifest.json`

`manifest.json` is a configuration for Slack apps. With a manifest, you can create an app with a pre-defined configuration, or adjust the configuration of an existing app.

### `app.py`

`app.py` is the entry point for the application and is the file you'll run to start the server. This project aims to keep this file as thin as possible, primarily using it as a way to route inbound requests.

### `app_oauth.py`

`app_oauth.py` is an alternative entry point that runs the app in HTTP mode instead of Socket Mode. This is intended for deployments that use OAuth for app distribution. See the HTTP Mode section under Development for setup instructions.

### `/listeners`

Every incoming request is routed to a "listener". This directory groups each listener based on the Slack Platform feature used.

**`/listeners/events`** — Handles incoming events:

- `app_home_opened.py` — Publishes the App Home view with a welcome message and MCP status.
- `app_mentioned.py` — Responds to @mentions in channels.
- `message.py` — Responds to direct messages and learns from channel messages.
- `reply_deps.py` — Builds `AgentDeps` for replies, selecting tools and tokens based on the requester and audience.

**`/listeners/install_url.py`** — Builds the Slack MCP connect link and message shared by the App Home and `/brief`.

**`/listeners/commands`** — Handles slash commands:

- `brief.py` — Handles the `/brief` command (owner-only).

**`/listeners/actions`** — Handles interactive components:

- `feedback_buttons.py` — Handles thumbs up/down feedback on agent responses.

**`/listeners/views`** — Builds Block Kit views:

- `app_home_builder.py` — Constructs the App Home Block Kit view.
- `feedback_builder.py` — Creates the feedback button block attached to responses.

### `/agent`

The `agent.py` file defines the personal agent with a system prompt shaped by `soul.md`. `run_agent()` gives it the bot token's runbook tools, or the Slack MCP Server's runbook tools in a DM with a person who has connected it, or read-only MCP tools for a brief. The app tools run in an in-process MCP server (`agent-tools`), and the Slack MCP Server is added as `slack-mcp`. Every run passes an explicit `allowed_tools` list with `permission_mode="dontAsk"`, disables Claude Code's built-in tools (`tools=[]`), and ignores local settings and MCP configs (`setting_sources=[]`, `strict_mcp_config=True`), so the agent can only call the tools selected for that run.

The `access.py` file decides who the owner is and only attaches a user token to private replies. Tool selection lives in `agent/agent.py`.

The `soul.py` file reads and writes `soul.md`.

The `deps.py` file defines the `AgentDeps` dataclass passed to the agent at runtime, providing access to the Slack client and conversation context. The `context.py` file holds it in a `ContextVar` so the tools can read it.

The `tools` directory contains the runbook tools (`list_runbooks.py`, `read_runbook.py`, `create_runbook.py`), which call `files.list`, `canvases.getContent`, and `canvases.create` with the bot token; `channel_runbooks.py` limits them to runbooks shared in the current conversation; `soul.py` implements `update_soul` (owner-only); `emoji_reaction.py` shows a request was picked up; and `text_result.py` wraps tool output as an MCP text result.

### `/thread_context`

The `store.py` file implements a thread-safe in-memory session ID store, keyed by channel, thread, and requester. The Claude Agent SDK keeps conversation history in its sessions, so only session IDs are tracked here for resuming conversations. This enables multi-turn conversations where the agent remembers previous context within a thread, and ensures one person's tool outputs never enter another person's run in a shared thread.

### `soul.template.md`

The template for the owner's `soul.md` file, with placeholder sections for Identity, About me, and Goals. Copy it to `soul.md` (gitignored) and fill in, or let the agent create it through an onboarding interview.

## Troubleshooting

### MCP Server connection error: `HTTP error 400 (Bad Request)`

If you see an error like:

```
Failed to connect to MCP server 'streamable_http: https://mcp.slack.com/mcp': HTTP error 400 (Bad Request)
```

This means the Slack MCP feature has not been enabled for your app. There is no manifest property for this yet, so it must be toggled on manually:

1. Run `slack app settings` to open your app's settings page (or visit [api.slack.com/apps](https://api.slack.com/apps) and select your app)
2. Navigate to **Agents & AI Apps** in the left-side navigation
3. Toggle **Slack Model Context Protocol** on
