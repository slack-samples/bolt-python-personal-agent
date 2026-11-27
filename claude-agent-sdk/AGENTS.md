# AGENTS.md

This file provides guidance to coding agents when working with code in this repository.

## What This Is

A **Personal Agent** for Slack built with Bolt for Python and the **Claude Agent SDK**. An agent that represents its owner in Slack. It learns who the owner is from a `SOUL.md` file, answers questions on their behalf when teammates message it, and keeps runbooks current. Runbooks are Slack canvases titled `Runbook: <topic>`. With the bot token, the agent lists, reads, and creates them with tools in `agent/tools/` (`files.list`, `canvases.getContent`, `canvases.create`). When a person has connected the Slack MCP Server, it uses the MCP runbook tools instead, which can also edit runbooks. The same agent learns from each channel message it doesn't reply to and that doesn't mention it (`listeners/events/message.py`), adding anything it settles to a runbook. The owner can use `/brief` to get a summary of what needs their attention. Privacy is the top priority: the agent never responds with data that anyone who will see the reply couldn't already see.

## Invariants

- User tokens only attached to replies only that user sees
- Passive learning is bot-token only
- `update_soul` is owner-only in DM
- `/brief` is read-only
- Bot runbook tools only see the current conversation
- Conversation history is keyed per requester

## Slack Plugin

To install the Slack plugin for your coding agent, follow [Claude Code, Codex, Cursor, and Other Coding Agents](./README.md#claude-code-codex-cursor-and-other-coding-agents) in the README.

## Slack Skills

Slack skills are pre-installed in `.agents/skills` (and `.claude/skills` for Claude Code). Use them for Slack work. If the Slack plugin is installed, prefer its `slack:` skills, such as `slack:block-kit`, which may be newer. To update the pre-installed skills, run `npx --yes skills@1 add slackapi/slack-skills-plugin#<tag> --skill '*' --agent universal --agent claude-code --copy --yes` from this folder, with `<tag>` set to the latest release from https://github.com/slackapi/slack-skills-plugin/releases.

## Before you finish

Run `ruff check .`, `ruff format --check .`, and `pytest`. CI runs the same on every PR.

## Code Style

- Snake-case filenames
- No code comments. Make the code explain itself with clear names, tests, or types. Put the reason for a change in the PR description.
