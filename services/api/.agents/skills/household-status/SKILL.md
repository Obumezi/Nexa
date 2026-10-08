---
name: household-status
description: Check the current state of the Nexa household, including who is home, expected visitors, pending deliveries, and open tasks. Use this skill when the user asks for household status, summaries, pending items, who is present, who is expected, outstanding deliveries, or unfinished tasks.
---

# Household Status

Use Nexa's read-only MCP tools to answer questions about the current household state.

## Available tools

- `get_household_presence`
- `get_expected_visitors`
- `get_pending_deliveries`
- `get_open_tasks`

## Workflow

1. Determine which household information the user is requesting.
2. Call only the MCP tools necessary to answer the request.
3. Use the returned structured data as the source of truth.
4. Do not invent occupants, visitors, deliveries, or tasks.
5. If a tool returns an empty result, clearly state that Nexa currently has no matching records.
6. For a broad household summary, combine relevant results from multiple read-only tools.
7. Keep spoken responses concise and natural unless the user asks for detail.

## Examples

User: "Who is home?"

Use `get_household_presence`.

User: "Who's coming today?"

Use `get_expected_visitors`.

User: "Do I have any packages coming?"

Use `get_pending_deliveries`.

User: "What do I still need to do?"

Use `get_open_tasks`.

User: "Give me a household update."

Use the relevant household read tools and summarize the results.

## Safety

This skill is read-only.

Never use write tools merely because a read result suggests that something should be changed.