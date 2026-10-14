# Nexa

**Nexa** is a household intelligence agent built for the **Alexa+ MCP track** and the **AWS Builder mini challenge**.

It gives a household a conversational interface for understanding and managing presence, visitors, deliveries, and tasks.

Nexa exposes these capabilities through a self-hosted **Model Context Protocol (MCP)** server using **Streamable HTTP**, persists household state in **Amazon RDS PostgreSQL**, and uses **Amazon Bedrock with Amazon Nova Lite** to generate concise household briefings from live household data.

---

## Highlights

- MCP protocol version **2025-11-25**
- **Streamable HTTP** transport
- **14 MCP tools**
- Alexa+ style web simulator
- Open-standard Agent Skills
- Confirmation-gated write actions
- Amazon Bedrock / Nova Lite household briefings
- Amazon ECS production deployment
- Amazon RDS PostgreSQL persistent state
- Amazon ECR container images
- AWS Secrets Manager for production secrets
- Amazon CloudWatch logging
- IAM task role scoped for Bedrock invocation
- **273 automated tests passing**

---

# Live Demo

## Alexa+ Web Simulator

https://ne-cc084a3067bf4a9bbe7c0a4bc5e5ffee.ecs.us-east-1.on.aws/simulator

## MCP Streamable HTTP Endpoint

https://ne-cc084a3067bf4a9bbe7c0a4bc5e5ffee.ecs.us-east-1.on.aws/mcp/

---

# What Nexa Does

Nexa maintains structured household state and lets users interact with it naturally.

Examples:

```text
Who is home?

What tasks are open?

What deliveries are pending?

Is anyone expected to visit today?

Give me a home update.

Create a task to call the electrician tomorrow.

Complete the electrician task.

Mark the MacBook Pro as delivered.

Mark Ada Okafor as arrived.

Set Obumneme to away.


Read operations execute immediately.
State-changing actions use a confirmation-first workflow before household state is modified.
Example:
User:
Create a task to service the generator.

Nexa:
Create the task 'Service the generator'?

User:
Yes, confirm.

Nexa:
Task created: Service the generator.

Alexa+ / MCP Integration
Nexa includes a real, self-hosted MCP server implemented using the MCP Python SDK.
The live public MCP handshake has been verified with:
MCP initialization successful
Server: Nexa
Protocol Version: 2025-11-25
Tools available: 14

This satisfies the Alexa+ requirement for:
- MCP spec 2025-11-25 or later
- Streamable HTTP
- real MCP tool discovery
- real MCP tool execution
- a self-hosted public MCP server
MCP Tools
The Nexa MCP server currently exposes 14 tools:
1. nexa_status
2. get_household_presence
3. get_expected_visitors
4. get_pending_deliveries
5. get_open_tasks
6. get_household_briefing
7. create_task
8. complete_task
9. cancel_visitor
10. mark_visitor_arrived
11. mark_visitor_departed
12. mark_delivery_delivered
13. mark_delivery_collected
14. update_presence
These tools are not mocked.
They execute against the working Nexa backend and persistent household state.
Alexa+ Simulated Experience
Nexa includes a web-based Alexa+ style simulator.
The simulator allows judges and users to interact with Nexa through natural-language household requests.
Example:
Who is home?

Response:
Obumneme is currently at home.

Example:
What tasks are open?

Response:
You have one open task: Call the electrician tomorrow.

Example:
What deliveries are pending?

Response:
You have one pending DHL delivery: MacBook Pro.

Example:
Give me a home update.

Amazon Bedrock response:
Obumneme is home. Ada Okafor is expected for a family visit.
A MacBook Pro delivery from DHL is expected later today.

The simulator source code is included in this repository.
Agent Skills
Nexa includes open-standard Agent Skill definitions.
They are stored under:
.agents/skills/
├── household-status/
├── task-management/
├── visitor-management/
├── delivery-management/
└── presence-management/

The skills provide contextual instructions and help Nexa determine how household requests should be interpreted and executed.
The current skills cover:
- household status
- household tasks
- visitor management
- delivery management
- presence management
Amazon Bedrock Integration
Nexa includes a real Amazon Bedrock integration as part of the AWS Builder mini challenge.
The get_household_briefing MCP tool collects the current household state and sends that structured context to:
Amazon Bedrock
Model: Amazon Nova Lite
Region: us-east-1

The integration uses the Bedrock Runtime Converse API.
The model is instructed to:
- use only supplied household facts
- avoid inventing information
- produce a concise natural-language household summary
- keep the output short and useful
Example request:
Give me a home update.

Example output:
Obumneme is home. Ada Okafor is expected for a family visit.
A MacBook Pro delivery from DHL is expected later today.

This is a live feature in the production Nexa application, not a standalone proof of concept.
AWS Builder Integration
Nexa uses multiple AWS services in the working production system.
Amazon Bedrock
Used for AI-generated household briefings through Amazon Nova Lite.
Amazon ECS
The production Nexa application runs on Amazon ECS.
The ECS deployment hosts:
- FastAPI backend
- Alexa+ simulator
- MCP server
- household APIs
- Bedrock-enabled briefing capability
Amazon ECR
Production Docker container images are stored in Amazon Elastic Container Registry.
Amazon RDS PostgreSQL
Nexa uses Amazon RDS PostgreSQL for persistent household state.
The database stores:
- household presence
- expected visitors
- deliveries
- household tasks
- home events
- conversation state
Persistence was verified by replacing the running ECS task and confirming that the same household records remained available after the replacement task started.
This confirms Nexa does not depend on container-local storage in production.
AWS Secrets Manager
Production secrets are stored outside the source code.
Secrets Manager is used for sensitive runtime configuration such as:
- PostgreSQL database connection details
- external AI API credentials
Secrets are injected into ECS at runtime.
Amazon CloudWatch
CloudWatch is used for ECS and application logs.
It has been used during development to verify:
- application startup
- Alembic migrations
- PostgreSQL connectivity
- MCP runtime behavior
- deployment health
IAM
Nexa uses an ECS task IAM role for Bedrock access.
The task role has permission to invoke:
amazon.nova-lite-v1:0

through:
bedrock:InvokeModel

This keeps Bedrock access scoped to the application task rather than embedding AWS credentials in the application.
Architecture
#chatgpt-mermaid-_r_a5s_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-_r_a5s_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_a5s_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_a5s_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-_r_a5s_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-_r_a5s_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-_r_a5s_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-_r_a5s_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-_r_a5s_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-_r_a5s_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-_r_a5s_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-_r_a5s_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_a5s_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_a5s_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-_r_a5s_ p{margin:0;}#chatgpt-mermaid-_r_a5s_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_a5s_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_a5s_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_a5s_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-_r_a5s_ .label text,#chatgpt-mermaid-_r_a5s_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_a5s_ .node rect,#chatgpt-mermaid-_r_a5s_ .node circle,#chatgpt-mermaid-_r_a5s_ .node ellipse,#chatgpt-mermaid-_r_a5s_ .node polygon,#chatgpt-mermaid-_r_a5s_ .node path{fill:rgb(52, 24, 11);stroke:rgb(172, 79, 35);stroke-width:1px;}#chatgpt-mermaid-_r_a5s_ .rough-node .label text,#chatgpt-mermaid-_r_a5s_ .node .label text,#chatgpt-mermaid-_r_a5s_ .image-shape .label,#chatgpt-mermaid-_r_a5s_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-_r_a5s_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-_r_a5s_ .rough-node .label,#chatgpt-mermaid-_r_a5s_ .node .label,#chatgpt-mermaid-_r_a5s_ .image-shape .label,#chatgpt-mermaid-_r_a5s_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-_r_a5s_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-_r_a5s_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_a5s_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-_r_a5s_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-_r_a5s_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-_r_a5s_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-_r_a5s_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-_r_a5s_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-_r_a5s_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-_r_a5s_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-_r_a5s_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_a5s_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_a5s_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-_r_a5s_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_a5s_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-_r_a5s_ .icon-shape,#chatgpt-mermaid-_r_a5s_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-_r_a5s_ .icon-shape p,#chatgpt-mermaid-_r_a5s_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-_r_a5s_ .icon-shape .label rect,#chatgpt-mermaid-_r_a5s_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-_r_a5s_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-_r_a5s_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-_r_a5s_ .node .neo-node{stroke:rgb(172, 79, 35);}#chatgpt-mermaid-_r_a5s_ [data-look="neo"].node rect,#chatgpt-mermaid-_r_a5s_ [data-look="neo"].cluster rect,#chatgpt-mermaid-_r_a5s_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-_r_a5s_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_a5s_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-_r_a5s_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-_r_a5s_-gradient);stroke-width:1px;}#chatgpt-mermaid-_r_a5s_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_a5s_ [data-look="neo"].node .neo-line path{stroke:rgb(172, 79, 35);filter:none;}#chatgpt-mermaid-_r_a5s_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-_r_a5s_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_a5s_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-_r_a5s_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-_r_a5s_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_a5s_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-_r_a5s_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_a5s_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(255, 183, 144);}#chatgpt-mermaid-_r_a5s_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(255, 183, 144);}#chatgpt-mermaid-_r_a5s_ .node tspan[font-weight="normal"],#chatgpt-mermaid-_r_a5s_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-_r_a5s_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(40, 17, 5);stroke:rgb(92, 56, 31);stroke-width:1px;}#chatgpt-mermaid-_r_a5s_ .node rect,#chatgpt-mermaid-_r_a5s_ .node circle,#chatgpt-mermaid-_r_a5s_ .node ellipse,#chatgpt-mermaid-_r_a5s_ .node polygon,#chatgpt-mermaid-_r_a5s_ .node path{fill:rgb(74, 34, 6);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-_r_a5s_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-_r_a5s_ .node.mermaid-decision .label-container{fill:rgb(40, 17, 5);stroke:rgb(92, 56, 31);stroke-dasharray:2,2;}#chatgpt-mermaid-_r_a5s_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-_r_a5s_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_a5s_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}User / JudgeAlexa+ Web SimulatorNexa FastAPI Application onAmazon ECSMCP ServerSpec 2025-11-25Streamable HTTP14 ToolsAgent SkillsIntent / Orchestration LayerHousehold ToolsTasksVisitorsDeliveriesPresenceOpenAI Intent LayerNatural LanguageUnderstandingAmazon BedrockAmazon Nova LiteHousehold BriefingsAmazon RDS PostgreSQLAmazon ECRContainer ImagesAWS Secrets ManagerRuntime SecretsAmazon CloudWatchLogsIAM Task RoleBedrock Permissions




Safe Write-Action Flow
Nexa separates understanding from execution.
For state-changing actions, the workflow is:
User request
   ↓
Intent resolution
   ↓
MCP tool proposed
   ↓
Confirmation required
   ↓
User confirms
   ↓
Action executes
   ↓
RDS state updates

Example:
User:
Mark the MacBook Pro as delivered.

Nexa:
Mark 'MacBook Pro' as delivered?

User:
Yes, confirm.

Nexa:
Delivery marked as delivered: MacBook Pro.

This prevents accidental execution of state-changing operations.
Technology Stack
Backend
- Python
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- Uvicorn
Agent / AI
- MCP Python SDK
- OpenAI API
- Amazon Bedrock
- Amazon Nova Lite
- Agent Skills
Data
- Amazon RDS PostgreSQL
- SQLite for local development and testing
AWS
- Amazon ECS
- Amazon ECR
- Amazon RDS
- Amazon Bedrock
- AWS Secrets Manager
- Amazon CloudWatch
- IAM
Development
- Docker
- Pytest
- Ruff
- PowerShell
- GitHub
Repository Structure
nexa/
├── .agents/
│   └── skills/
│       ├── household-status/
│       │   └── SKILL.md
│       ├── task-management/
│       │   └── SKILL.md
│       ├── visitor-management/
│       │   └── SKILL.md
│       ├── delivery-management/
│       │   └── SKILL.md
│       └── presence-management/
│           └── SKILL.md
│
├── services/
│   └── api/
│       ├── migrations/
│       ├── src/
│       │   └── nexa_api/
│       │       ├── agent_routes.py
│       │       ├── agent_service.py
│       │       ├── bedrock_service.py
│       │       ├── config.py
│       │       ├── database.py
│       │       ├── delivery_routes.py
│       │       ├── delivery_service.py
│       │       ├── mcp_executor.py
│       │       ├── mcp_orchestrator.py
│       │       ├── mcp_server.py
│       │       ├── models.py
│       │       ├── presence_routes.py
│       │       ├── presence_service.py
│       │       ├── schemas.py
│       │       ├── simulator_routes.py
│       │       ├── simulator_ui.py
│       │       ├── skill_loader.py
│       │       ├── skill_selector.py
│       │       ├── task_routes.py
│       │       ├── task_service.py
│       │       ├── visitor_routes.py
│       │       └── visitor_service.py
│       │
│       ├── tests/
│       ├── Dockerfile
│       ├── alembic.ini
│       ├── pyproject.toml
│       ├── public_mcp_test.py
│       └── test_bedrock.py
│
└── README.md

Local Setup
1. Clone the Repository
git clone https://github.com/Obumezi/nexa.git
cd nexa/services/api

2. Create a Virtual Environment
Windows PowerShell:
python -m venv .venv
.venv\Scripts\Activate.ps1

Linux/macOS:
python3 -m venv .venv
source .venv/bin/activate

3. Install Dependencies
pip install -e .

Install development dependencies:
pip install -e ".[dev]"

If your local AWS credential provider requires AWS CRT:
pip install "botocore[crt]"

Environment Configuration
Nexa uses the NEXA_ prefix for environment variables.
Local development defaults to SQLite.
Example:
NEXA_ENVIRONMENT=development
NEXA_DATABASE_URL=sqlite:///./nexa.db
NEXA_OPENAI_API_KEY=
NEXA_OPENAI_MODEL=
NEXA_BEDROCK_REGION=us-east-1
NEXA_BEDROCK_MODEL_ID=amazon.nova-lite-v1:0

AWS credentials should be configured using the AWS CLI or another supported AWS credential provider.
Do not commit:
- AWS credentials
- OpenAI API keys
- database passwords
- Secrets Manager values
- production .env files
Database Setup
Run migrations:
alembic upgrade head

Local development uses:
SQLite

Production uses:
Amazon RDS PostgreSQL

Run Nexa Locally
Start the FastAPI application:
uvicorn nexa_api.main:app --reload --port 8000

Open the simulator:
http://127.0.0.1:8000/simulator

Local MCP endpoint:
http://127.0.0.1:8000/mcp/

Health endpoint:
http://127.0.0.1:8000/health

Testing
Ruff
ruff check src tests

Pytest
pytest --basetemp=.pytest_tmp

Current verified result:
273 passed

The live MCP tests require the local MCP server to be running.
Public MCP Verification
The repository includes:
services/api/public_mcp_test.py

Run:
python .\public_mcp_test.py

Expected initialization:
MCP initialization successful

Server: Nexa

Protocol Version: 2025-11-25

Tools available: 14

The test verifies:
- MCP initialization
- protocol negotiation
- tool discovery
- household state reads
- task creation
- persistent state retrieval
Amazon Bedrock Verification
A local Bedrock integration test is available at:
services/api/test_bedrock.py

Run:
python .\test_bedrock.py

Example output:
Obumneme is home, and Ada Okafor is visiting for family.
A MacBook Pro delivery from DHL is expected, and an electrician
call is scheduled for tomorrow.

Suggested Demo Flow
A strong judge-facing demo sequence is:
Who is home?

Expected:
Obumneme is currently at home.

Then:
What deliveries are pending?

Expected:
You have one pending DHL delivery: MacBook Pro.

Then:
Give me a home update.

This demonstrates Amazon Bedrock and Nova Lite.
Then:
Create a task to service the generator.

Nexa should ask for confirmation.
Then:
Yes, confirm.

Then:
What tasks are open?

The newly created task should appear.
This single flow demonstrates:
- Alexa+ style conversation
- MCP reads
- Amazon Bedrock
- confirmation-gated MCP writes
- persistent state
- end-to-end production behavior
Security and Safety
Nexa is designed around explicit execution boundaries.
Read Actions
Read operations can execute immediately.
Examples:
- get household presence
- list expected visitors
- list pending deliveries
- list open tasks
- generate household briefing
Write Actions
State-changing operations require confirmation.
Examples:
- create task
- complete task
- cancel visitor
- mark visitor arrived
- mark visitor departed
- mark delivery delivered
- mark delivery collected
- update household presence
Secrets
Production credentials are not stored in source code.
They are injected through AWS Secrets Manager.
Database
Production data is persisted in RDS PostgreSQL.
AWS Access
Bedrock permissions are granted through a dedicated ECS IAM task role.
Persistence Verification
Production persistence was tested directly.
The process was:
1. Seed household data into the production RDS database.
2. Verify the data through the live simulator.
3. Stop the running ECS task.
4. Allow ECS to create a replacement task.
5. Query the simulator again.
The same household data remained available after task replacement.
This confirms that Nexa uses persistent RDS state rather than ephemeral container storage.
Alexa+ Track Compliance
Nexa satisfies the Alexa+ MCP requirements with:
- self-hosted MCP server
- MCP protocol version 2025-11-25
- Streamable HTTP
- real MCP Python SDK integration
- public MCP endpoint
- real MCP tool discovery
- real MCP tool execution
- Agent Skills
- Alexa+ style simulated web experience
- simulator source included in repository
- confirmation-based action flow
- persistent application state
AWS Builder Mini Challenge
Nexa qualifies for the AWS Builder mini challenge through a real Amazon Bedrock integration.
Amazon Bedrock is used by the live:
get_household_briefing

MCP tool.
This capability:
1. reads live household state
2. constructs structured context
3. invokes Amazon Nova Lite through Bedrock
4. returns a natural-language household summary
The production application also uses:
- Amazon ECS
- Amazon ECR
- Amazon RDS PostgreSQL
- AWS Secrets Manager
- Amazon CloudWatch
- IAM
Built During the Hackathon
Nexa was implemented during the hackathon as a working household intelligence platform.
Work completed during the submission period includes:
- household data model
- visitor management
- delivery management
- household presence
- household tasks
- automation services
- conversational intent resolution
- MCP server
- Streamable HTTP transport
- 14 MCP tools
- Agent Skills
- confirmation-gated write actions
- Alexa+ style simulator
- Docker deployment
- Amazon ECS production deployment
- Amazon RDS PostgreSQL persistence
- AWS Secrets Manager integration
- Amazon CloudWatch logging
- IAM task permissions
- Amazon Bedrock / Nova Lite integration
- automated testing
- production MCP validation
Demo Data
A clean demo configuration may include:
Presence:
Obumneme → home

Visitor:
Ada Okafor → expected

Delivery:
DHL MacBook Pro → expected

Task:
Call the electrician tomorrow → open

This makes the simulator easy to demonstrate consistently.
Product Feedback
Detailed product feedback for the technologies used is included in the hackathon submission.
Feedback covers:
- Alexa+ simulated experience
- MCP Python SDK
- Amazon Bedrock
- Amazon ECS
- Amazon RDS
- Amazon ECR
- AWS Secrets Manager
- Amazon CloudWatch
- IAM
- OpenAI API
Friction Log
The submission also documents engineering friction encountered during development, including:
- MCP live tests requiring a running local MCP server
- ECS task role configuration for Bedrock
- AWS credential provider dependency on awscrt
- production RDS configuration
- Secrets Manager injection behavior
- deployment troubleshooting
- persistent-state validation
- ECS task definition revisions
These issues and their workarounds helped shape the final Nexa architecture.
Hackathon Entry
Primary Track
Alexa+
Nexa provides a self-hosted MCP integration and simulated Alexa+ experience.
Mini Challenge
AWS Builder
Nexa uses Amazon Bedrock with Amazon Nova Lite as a real user-facing capability.
License
Before submission, choose one of the following.
Public Repository
Add an approved open-source license such as:
MIT License

or another appropriate open-source license.
Private Repository
If the repository remains private, grant reviewer access according to the hackathon submission instructions.
Required reviewers may include:
chris-trag
knmeiss
giolaq
anishamalde
mosesroth
emersonsklar

Also follow Devpost's required repository-sharing instructions.
Author
Built for the Amazon Developer Hackathon.
Project: Nexa
Track: Alexa+
Mini Challenge: AWS Builder
