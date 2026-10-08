---
name: presence-management
description: Read and update Nexa household presence states. Use this skill when the user asks who is home or away, or states that a household member is home, leaving, away, or going to sleep.
---

# Presence Management

Manage household presence through Nexa MCP.

## Available tools

- `get_household_presence`
- `update_presence`

## Supported presence states

Nexa supports:

- `home`
- `away`
- `sleeping`

Do not invent additional presence states.

## Reading presence

Use `get_household_presence` when the user asks questions such as:

- "Who is home?"
- "Where is Obumneme?"
- "Is anyone sleeping?"

## Updating presence

Use `update_presence` when the user explicitly communicates a presence change.

Examples:

User: "I'm home."

Use the current speaker identity and propose:

`update_presence(status="home", confirm=false)`

User: "I'm leaving."

Propose:

`update_presence(status="away", confirm=false)`

User: "I'm going to sleep."

Propose:

`update_presence(status="sleeping", confirm=false)`

If Nexa returns `requires_confirmation=true`, ask the user to confirm.

Only after explicit confirmation call the same operation with:

`confirm=true`

## Identity

Preserve the identified household member's name.

Do not invent another occupant identity.

If the speaker's identity is unknown and the requested action requires an occupant name, ask who the update applies to.

## Safety

Only report that presence changed when:

`action_executed=true`

If Nexa rejects an unsupported presence state, explain that the supported states are home, away, and sleeping.