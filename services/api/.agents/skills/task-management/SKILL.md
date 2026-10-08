---
name: task-management
description: Manage Nexa household tasks through MCP. Use this skill when the user wants to create a task, complete an existing task, review open tasks, or refer to a task conversationally.
---

# Task Management

Manage household tasks using Nexa's MCP tools.

## Available tools

- `get_open_tasks`
- `create_task`
- `complete_task`

## Reading tasks

Use `get_open_tasks` when the user asks about incomplete or outstanding household tasks.

## Creating tasks

Use `create_task` when the user explicitly asks to add or create a household task.

First call:

`create_task(confirm=false)`

If Nexa returns:

`requires_confirmation=true`

ask the user to confirm.

Only after explicit confirmation call:

`create_task(confirm=true)`

Never skip the confirmation step.

## Completing tasks

Use `complete_task` when the user asks to mark an existing task as done or completed.

First call:

`complete_task(confirm=false)`

If confirmation is required, present Nexa's proposed action to the user.

Only after explicit confirmation call:

`complete_task(confirm=true)`

## Matching

Nexa performs exact matching first and controlled fuzzy matching second.

If Nexa reports that a task cannot be uniquely identified, do not guess.

Ask the user to identify the intended task more clearly.

## Safety

Never claim a task was created or completed unless the MCP response returns:

`action_executed=true`