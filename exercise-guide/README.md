# Architecting and Developing Agentic Enterprise — Exercise Guide

## Exercises

| # | Title | Timing | Description |
|---|-------|--------|-------------|
| 1 | [Salesforce Org Setup (Data Cloud + Service Cloud + Connected App)](01-salesforce-org-setup.md) | ~90 min | Provision org, configure Data Cloud (stream, mapping, identity resolution), create Service Cloud case flow, create Connected App with Client Credentials, create Opportunity custom fields |
| 2 | [Slack Workspace, App, and slack-agent-router](02-slack-workspace.md) | ~75 min | Create Slack workspace, configure bot app with scopes, event subscriptions, interactivity; build all 7 Mule XML files for the slack-agent-router Experience Layer app |
| 3 | [AWS Bedrock Agent + MuleSoft AI Gateway](03-aws-bedrock-ai-gateway.md) | ~60 min | Create IAM user, Lambda fraud scorer, Bedrock Agent with enforced tool ordering, Agent and Tool Instance on Omni Gateway, Agent Scanner in Exchange |
| 4 | [The Process Layer — ai-orchestrator](04-process-layer-orchestrator.md) | ~90 min | Build the 6-stage orchestration pipeline: identity validation, Data Cloud enrichment, intent resolution, Bedrock risk assessment, policy enforcement, Service Cloud mutation. Includes circuit breaker, DLQ, five Object Stores, DataWeave library |
| 5 | [System APIs — data-cloud-sapi and service-cloud-mcp](05-system-apis.md) | ~75 min | Build the two System APIs: Data Cloud SAPI (SDC connector, OAuth CC, caching strategy) and Service Cloud MCP (Salesforce connector, OAuth CC, idempotency, risk gate, Case + Opportunity) |
| 6 | [Deployment and End-to-End Validation](06-deployment-end-to-end.md) | ~45 min | Deploy all four apps to CloudHub 2.0 in the correct order, patch secrets via Runtime Manager API, run verification sequence, complete Slack-to-Case end-to-end test |
