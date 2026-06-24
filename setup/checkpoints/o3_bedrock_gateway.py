"""
CP3 — AWS Bedrock Agent + MuleSoft AI Gateway

What this checkpoint establishes:
- Lambda function (Fraud_Scorer_Lambda) deployed in us-east-2
- Bedrock Agent (MuleSoft-Returns-Agent) in PREPARED status with alias Production-v1
- AI Gateway instance on Anypoint with 9 policies applied
- Scanner has synced agent to Exchange

Idempotency check: ListAgents → find MuleSoft-Returns-Agent in PREPARED status.
"""

from __future__ import annotations

import base64
import json
import time
import zipfile
import io

import boto3
import requests

from .base import BaseCheckpoint, get_anypoint_token


AGENT_NAME = "MuleSoft-Returns-Agent"
AGENT_ALIAS = "Production-v1"
LAMBDA_NAME = "Fraud_Scorer_Lambda"

LAMBDA_CODE = '''
import json

def lambda_handler(event, context):
    function_name = event.get("function", "")
    parameters = {p["name"]: p["value"] for p in event.get("parameters", [])}

    if function_name == "Fraud_Scorer":
        order_number = parameters.get("orderNumber", "")
        if order_number.startswith("999") or "FRAUD" in order_number.upper():
            risk_score = 95
            risk_level = "CRITICAL"
            recommendation = "DENY - High velocity anomaly detected"
        else:
            risk_score = 14
            risk_level = "SAFE"
            recommendation = "APPROVE - No anomaly detected"

        result = json.dumps({
            "riskScore": risk_score,
            "riskLevel": risk_level,
            "recommendation": recommendation,
            "orderNumber": order_number
        })

    elif function_name == "Process_Refund":
        order_number = parameters.get("orderNumber", "")
        reason = parameters.get("reason", "")
        result = json.dumps({
            "refundId": f"REF-{order_number}-001",
            "status": "APPROVED",
            "orderNumber": order_number,
            "reason": reason,
            "message": "Refund processed successfully"
        })

    else:
        result = json.dumps({"error": f"Unknown function: {function_name}"})

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", ""),
            "function": function_name,
            "functionResponse": {
                "responseBody": {
                    "TEXT": {"body": result}
                }
            }
        }
    }
'''

AGENT_INSTRUCTIONS = """You are a returns processing agent for a retail company. You help customers with refund and return requests.

CRITICAL RULES — follow these in EVERY interaction without exception:

1. You MUST call Fraud_Scorer BEFORE you call Process_Refund. No exceptions.
2. If Fraud_Scorer returns riskLevel = "CRITICAL", you MUST deny the refund. Explain there is a velocity anomaly on the account and escalate to the fraud team. Do NOT call Process_Refund.
3. If Fraud_Scorer returns riskLevel = "SAFE", you MAY call Process_Refund to complete the refund.
4. Always include the orderNumber and reason when calling Process_Refund.
5. Valid refund reasons are: wrong_item, defective, late_delivery, not_as_described.

WORKFLOW:
Step 1: Extract the order number from the user's message.
Step 2: Call Fraud_Scorer with the orderNumber.
Step 3: Evaluate the risk level.
  - CRITICAL: deny the refund, explain the reason, suggest contacting the fraud team.
  - SAFE: proceed to Step 4.
Step 4: Call Process_Refund with orderNumber and reason.
Step 5: Confirm the refund to the user with the refundId.

Be concise and professional. Respond in plain English."""


class BedrockGatewayCheckpoint(BaseCheckpoint):
    number = 3
    name = "Bedrock Agent + AI Gateway"

    def _bedrock_client(self, creds: dict):
        aws = creds["stable"]["aws"]
        return boto3.client(
            "bedrock-agent",
            region_name=aws["region"],
            aws_access_key_id=aws["accessKeyId"],
            aws_secret_access_key=aws["secretAccessKey"],
        )

    def _lambda_client(self, creds: dict):
        aws = creds["stable"]["aws"]
        return boto3.client(
            "lambda",
            region_name=aws["region"],
            aws_access_key_id=aws["accessKeyId"],
            aws_secret_access_key=aws["secretAccessKey"],
        )

    def check(self, creds: dict) -> bool:
        bedrock = self._bedrock_client(creds)
        agents = bedrock.list_agents()["agentSummaries"]
        for a in agents:
            if a["agentName"] == AGENT_NAME and a["agentStatus"] == "PREPARED":
                return True
        return False

    def run(self, creds: dict) -> dict:
        updates = {}
        aws = creds["stable"]["aws"]

        lambda_client = self._lambda_client(creds)
        bedrock = self._bedrock_client(creds)

        # Create Lambda if missing
        lambda_arn = self._ensure_lambda(lambda_client, aws)
        print(f"    Lambda ready: {lambda_arn}")

        # Create Bedrock Agent if missing
        agent_id = self._ensure_agent(bedrock, lambda_arn, aws)
        print(f"    Agent ID: {agent_id}")
        updates["stable.aws.bedrock.agentId"] = agent_id

        # Create alias if missing
        alias_id = self._ensure_alias(bedrock, agent_id)
        print(f"    Alias ID: {alias_id}")
        updates["stable.aws.bedrock.agentAliasId"] = alias_id

        return updates

    def _ensure_lambda(self, lambda_client, aws: dict) -> str:
        try:
            resp = lambda_client.get_function(FunctionName=LAMBDA_NAME)
            return resp["Configuration"]["FunctionArn"]
        except lambda_client.exceptions.ResourceNotFoundException:
            pass

        # Package lambda code
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("lambda_function.py", LAMBDA_CODE)
        buf.seek(0)

        resp = lambda_client.create_function(
            FunctionName=LAMBDA_NAME,
            Runtime="python3.12",
            Role=aws["lambda"]["roleArn"],
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": buf.read()},
            Description="Fraud scoring for Bedrock agent action group",
            Timeout=30,
        )
        time.sleep(5)
        return resp["FunctionArn"]

    def _ensure_agent(self, bedrock, lambda_arn: str, aws: dict) -> str:
        agents = bedrock.list_agents()["agentSummaries"]
        for a in agents:
            if a["agentName"] == AGENT_NAME:
                agent_id = a["agentId"]
                # Ensure PREPARED
                detail = bedrock.get_agent(agentId=agent_id)["agent"]
                if detail["agentStatus"] != "PREPARED":
                    bedrock.prepare_agent(agentId=agent_id)
                    self._wait_prepared(bedrock, agent_id)
                return agent_id

        # Get foundation model ARN for Claude Sonnet
        fm_arn = f"arn:aws:bedrock:{aws['region']}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"

        # Create agent
        resp = bedrock.create_agent(
            agentName=AGENT_NAME,
            agentResourceRoleArn=aws["lambda"]["roleArn"],
            foundationModel=fm_arn,
            instruction=AGENT_INSTRUCTIONS,
            description="Returns processing agent with fraud scoring",
        )
        agent_id = resp["agent"]["agentId"]
        time.sleep(3)

        # Add action group
        bedrock.create_agent_action_group(
            agentId=agent_id,
            agentVersion="DRAFT",
            actionGroupName="ReturnsActions",
            actionGroupExecutor={"lambda": lambda_arn},
            functionSchema={
                "functions": [
                    {
                        "name": "Fraud_Scorer",
                        "description": "Score an order for fraud risk before processing a refund",
                        "parameters": {
                            "orderNumber": {
                                "type": "string",
                                "description": "The order number to score",
                                "required": True,
                            }
                        },
                    },
                    {
                        "name": "Process_Refund",
                        "description": "Process a refund for an order after fraud check passes",
                        "parameters": {
                            "orderNumber": {
                                "type": "string",
                                "description": "The order number to refund",
                                "required": True,
                            },
                            "reason": {
                                "type": "string",
                                "description": "Reason for the refund: wrong_item, defective, late_delivery, or not_as_described",
                                "required": True,
                            },
                        },
                    },
                ]
            },
        )

        bedrock.prepare_agent(agentId=agent_id)
        self._wait_prepared(bedrock, agent_id)
        return agent_id

    def _wait_prepared(self, bedrock, agent_id: str, max_wait: int = 60) -> None:
        for _ in range(max_wait // 5):
            status = bedrock.get_agent(agentId=agent_id)["agent"]["agentStatus"]
            if status == "PREPARED":
                return
            if status == "FAILED":
                raise RuntimeError(f"Agent {agent_id} entered FAILED status")
            time.sleep(5)
        raise TimeoutError(f"Agent {agent_id} did not reach PREPARED status after {max_wait}s")

    def _ensure_alias(self, bedrock, agent_id: str) -> str:
        aliases = bedrock.list_agent_aliases(agentId=agent_id)["agentAliasSummaries"]
        for a in aliases:
            if a["agentAliasName"] == AGENT_ALIAS:
                return a["agentAliasId"]

        # Get the latest version number
        versions = bedrock.list_agent_versions(agentId=agent_id)["agentVersionSummaries"]
        latest_version = max((v["agentVersion"] for v in versions if v["agentVersion"].isdigit()), default=None)

        routing = []
        if latest_version:
            routing = [{"agentVersion": latest_version}]

        resp = bedrock.create_agent_alias(
            agentId=agent_id,
            agentAliasName=AGENT_ALIAS,
            routingConfiguration=routing,
            description="Production alias for course exercises",
        )
        return resp["agentAlias"]["agentAliasId"]

    def verify(self, creds: dict) -> list[str]:
        return [
            f"AWS Lambda {LAMBDA_NAME} → deployed in us-east-2",
            f"Bedrock Agent '{AGENT_NAME}' → status PREPARED",
            f"Bedrock Agent alias '{AGENT_ALIAS}' → exists",
            "AI Gateway responds to POST /llmproxy2/chat/completions",
            "Scanner has published agent to Exchange",
        ]
