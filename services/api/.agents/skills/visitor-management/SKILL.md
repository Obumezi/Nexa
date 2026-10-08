---
name: visitor-management
description: Manage expected household visitors with Nexa. Use this skill when the user asks who is expected, says a visitor has arrived or left, wants to cancel a visit, or refers to an expected or arrived visitor.
---

# Visitor Management

Use Nexa's visitor MCP tools for household visitor workflows.

## Available tools

- `get_expected_visitors`
- `cancel_visitor`
- `mark_visitor_arrived`
- `mark_visitor_departed`

## Expected visitors

Use `get_expected_visitors` for questions about upcoming or expected visitors.

## Cancelling a visit

Call:

`cancel_visitor(confirm=false)`

If confirmation is required, ask the user to confirm.

Only then call:

`cancel_visitor(confirm=true)`

## Visitor arrival

When the user states that an expected visitor has arrived, use:

`mark_visitor_arrived(confirm=false)`

Require confirmation before executing the state change.

## Visitor departure

When an arrived visitor leaves, use:

`mark_visitor_departed(confirm=false)`

Require confirmation before executing the state change.

## Entity matching

Nexa handles exact and safe fuzzy matching.

Never guess when multiple visitors could match a name or reference.

If Nexa cannot find a unique visitor, ask the user for clarification.

## Conversational examples

User: "Has Ada arrived?"

Check visitor information before making any state change.

User: "Chinedu is here."

Propose `mark_visitor_arrived`.

User: "Chinedu has left."

Propose `mark_visitor_departed`.

User: "Cancel Ada's visit."

Propose `cancel_visitor`.

## Safety

A visitor state must never be changed without user confirmation.

Only report success when:

`action_executed=true`