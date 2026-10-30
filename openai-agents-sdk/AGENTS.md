# AGENTS.md

This file provides guidance to coding agents when working with code in this repository.

## What This Is

A **Personal Agent** for Slack built with Bolt for Python and the **OpenAI Agents SDK**. An agent that represents its owner in Slack. It learns who the owner is from a `soul.md` file, answers questions on their behalf when teammates message it, and keeps runbooks current. Runbooks are Slack canvases titled `Runbook: <topic>`. With the bot token, the agent lists, reads, and creates them with tools in `agent/tools/` (`files.list`, `canvases.getContent`, `canvases.create`). When a person has connected the Slack MCP Server, it uses the MCP runbook tools instead, which can also edit runbooks. The same agent learns from each channel message (`listeners/events/message.py`), adding anything it settles to a runbook. The owner can use `/brief` to get a summary of what needs their attention. Privacy is the top priority: the agent never responds with data that anyone who will see the reply couldn't already see.

## Slack Plugin

To install the Slack plugin for your coding agent, follow [Claude Code, Codex, Cursor, and Other Coding Agents](./README.md#claude-code-codex-cursor-and-other-coding-agents) in the README.

## Before you finish

Run `ruff check .`, `ruff format --check .`, and `pytest`. CI runs the same on every PR.

## Code Style

- Snake-case filenames
- No code comments. Make the code explain itself with clear names, tests, or types. Put the reason for a change in the PR description.
