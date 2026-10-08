---
name: delivery-management
description: Manage Nexa household deliveries through MCP. Use this skill when the user asks about pending packages, reports that a delivery has arrived, says a package was collected, or refers to a delivery conversationally.
---

# Delivery Management

Use Nexa's MCP delivery tools to track household packages safely.

## Available tools

- `get_pending_deliveries`
- `mark_delivery_delivered`
- `mark_delivery_collected`

## Pending deliveries

Use `get_pending_deliveries` when the user asks what packages or deliveries are expected.

## Delivered packages

When the user reports that an expected delivery has arrived, call:

`mark_delivery_delivered(confirm=false)`

If Nexa requires confirmation, ask the user before proceeding.

After explicit confirmation call:

`mark_delivery_delivered(confirm=true)`

## Collected packages

When the user says a delivered package has been collected, call:

`mark_delivery_collected(confirm=false)`

If confirmation is required, obtain explicit confirmation first.

Then call:

`mark_delivery_collected(confirm=true)`

## Matching

Nexa uses exact matching first and safe fuzzy matching second.

Do not guess when multiple deliveries match the user's description.

Ask for clarification if Nexa cannot identify a unique delivery.

## Safety

Never report a delivery as delivered or collected unless Nexa returns:

`action_executed=true`