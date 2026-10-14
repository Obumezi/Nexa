# Nexa

**Nexa** is a household intelligence agent built for the **Alexa+ MCP track** and the **AWS Builder mini challenge**.

It gives a household a conversational interface for understanding and managing presence, visitors, deliveries, and tasks. Nexa exposes these capabilities through a self-hosted **Model Context Protocol (MCP)** server using **Streamable HTTP**, persists household state in **Amazon RDS PostgreSQL**, and uses **Amazon Bedrock with Nova Lite** to generate concise household briefings.

## Highlights

- MCP protocol version **2025-11-25**
- **Streamable HTTP** transport
- **14 MCP tools**
- Alexa+ style web simulator
- Open-standard Agent Skills
- Confirmation-gated write actions
- Amazon Bedrock / Nova Lite household briefings
- Amazon ECS deployment
- Amazon RDS PostgreSQL persistent state
- Amazon ECR container images
- AWS Secrets Manager for production secrets
- Amazon CloudWatch logging
- IAM task role scoped for Bedrock invocation

## Live Demo

### Alexa+ Simulator

https://ne-cc084a3067bf4a9bbe7c0a4bc5e5ffee.ecs.us-east-1.on.aws/simulator

### MCP Streamable HTTP Endpoint

https://ne-cc084a3067bf4a9bbe7c0a4bc5e5ffee.ecs.us-east-1.on.aws/mcp/

---

## What Nexa Does

Nexa maintains structured household state and lets a user interact with it naturally.

Examples:

```text
Who is home?

What tasks are open?

What deliveries are pending?

Is anyone expected to visit today?

Give me a home update.

Create a task to call the electrician tomorrow.

Mark the MacBook Pro as delivered.

Mark Ada Okafor as arrived.


