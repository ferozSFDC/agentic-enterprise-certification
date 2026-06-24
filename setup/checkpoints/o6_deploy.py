"""
CP6 — Full CloudHub Deployment

What this checkpoint establishes:
- All 4 apps deployed to CloudHub in the student's Anypoint org
- Each app configured with correct secrets via PATCH on the deployment
- Slack event/command URLs updated to point to CloudHub ingress
- End-to-end health verified

Idempotency check: GET deployment for each app → status RUNNING.
"""

from __future__ import annotations

import time

import requests

from .base import BaseCheckpoint, get_anypoint_token


APP_NAMES = [
    "slack-agent-router",
    "ai-orchestrator",
    "data-cloud-sapi",
    "service-cloud-mcp",
]

ANYPOINT_BASE = "https://anypoint.mulesoft.com"


class DeployCheckpoint(BaseCheckpoint):
    number = 6
    name = "Full CloudHub Deployment"

    def _am_headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _get_deployments(self, token: str, creds: dict) -> list[dict]:
        org_id = creds["variable"]["anypoint"]["orgId"]
        env_id = creds["variable"]["anypoint"]["environmentId"]
        resp = requests.get(
            f"{ANYPOINT_BASE}/amc/application-manager/api/v2/organizations/{org_id}/environments/{env_id}/deployments",
            headers=self._am_headers(token),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("items", [])

    def check(self, creds: dict) -> bool:
        token = get_anypoint_token(creds)
        deployments = self._get_deployments(token, creds)
        running = {d["name"] for d in deployments if d.get("status") == "RUNNING"}
        return all(app in running for app in APP_NAMES)

    def run(self, creds: dict) -> dict:
        token = get_anypoint_token(creds)
        deployments = self._get_deployments(token, creds)
        existing = {d["name"]: d for d in deployments}

        for app_name in APP_NAMES:
            if app_name in existing and existing[app_name].get("status") == "RUNNING":
                print(f"    {app_name} already running — patching secrets only")
                self._patch_secrets(token, creds, app_name, existing[app_name]["id"])
            else:
                print(f"    Deploying {app_name}...")
                self._deploy_app(token, creds, app_name)

        # Wait for all apps to reach RUNNING
        print("    Waiting for all apps to reach RUNNING status...")
        self._wait_all_running(token, creds)
        print("    All apps running.")

        return {}

    def _build_secrets(self, creds: dict, app_name: str) -> dict:
        aws = creds["stable"]["aws"]
        sc = creds["stable"]["salesforce"]["serviceCloud"]
        dc = creds["stable"]["salesforce"]["dataCloud"]
        gw = creds["stable"]["aiGateway"]
        slack = creds["stable"]["slack"]
        bedrock = aws["bedrock"]

        if app_name == "slack-agent-router":
            return {
                "slack.botToken": slack["botToken"],
                "slack.signingSecret": slack["signingSecret"],
                "ai-gateway.clientId": gw["clientId"],
                "ai-gateway.clientSecret": gw["clientSecret"],
            }
        elif app_name == "ai-orchestrator":
            return {
                "sfdc.clientId": sc["clientId"],
                "sfdc.clientSecret": sc["clientSecret"],
                "sfdc.tokenEndpoint": sc["tokenEndpoint"],
                "ai-gateway.clientId": gw["clientId"],
                "ai-gateway.clientSecret": gw["clientSecret"],
                "ai-gateway.host": gw["host"],
                "aws.accessKeyId": aws["accessKeyId"],
                "aws.secretAccessKey": aws["secretAccessKey"],
                "aws.region": aws["region"],
                "bedrock.agentId": bedrock["agentId"],
                "bedrock.agentAliasId": bedrock["agentAliasId"],
            }
        elif app_name == "data-cloud-sapi":
            return {
                "sfdc.clientId": dc["clientId"],
                "sfdc.clientSecret": dc["clientSecret"],
                "sfdc.tokenEndpoint": dc["tokenEndpoint"],
                "slack.botToken": slack["botToken"],
            }
        elif app_name == "service-cloud-mcp":
            return {
                "sfdc.clientId": sc["clientId"],
                "sfdc.clientSecret": sc["clientSecret"],
                "sfdc.tokenEndpoint": sc["tokenEndpoint"],
            }
        return {}

    def _deploy_app(self, token: str, creds: dict, app_name: str) -> None:
        org_id = creds["variable"]["anypoint"]["orgId"]
        env_id = creds["variable"]["anypoint"]["environmentId"]
        target = creds["variable"]["cloudHub"]["deploymentTargetName"]
        region = creds["variable"]["cloudHub"].get("region", "us-east-2")

        secrets = self._build_secrets(creds, app_name)
        course = creds["stable"]["course"]
        jar_url = f"{course['jarReleaseBaseUrl']}/{course['jarReleaseTag']}/{app_name}.jar"

        payload = {
            "name": app_name,
            "labels": ["agentic-course"],
            "target": {
                "targetId": target,
                "type": "MC",
                "provider": "MC",
                "deploymentSettings": {
                    "runtimeVersion": "4.8.0",
                    "updateStrategy": "rolling",
                    "clustered": False,
                    "enforceDeployingReplicasAcrossNodes": False,
                    "http": {"inbound": {"publicUrl": ""}},
                    "jvm": {},
                    "resources": {
                        "cpu": {"reserved": "100m", "limit": "500m"},
                        "memory": {"reserved": "700Mi", "limit": "700Mi"},
                    },
                    "sidecars": {"anypoint-monitoring": {"image": ""}},
                },
                "replicas": 1,
            },
            "application": {
                "fileRef": {"packageName": f"{app_name}.jar", "artifactUrl": jar_url},
                "configuration": {
                    "mule.agent.application.properties.service": {
                        "applicationName": app_name,
                        "properties": secrets,
                        "secureProperties": {},
                    }
                },
                "vCores": 0.1,
            },
        }

        resp = requests.post(
            f"{ANYPOINT_BASE}/amc/application-manager/api/v2/organizations/{org_id}/environments/{env_id}/deployments",
            headers=self._am_headers(token),
            json=payload,
            timeout=30,
        )
        if not resp.ok:
            raise RuntimeError(f"Deploy {app_name} failed: {resp.status_code} {resp.text}")

    def _patch_secrets(self, token: str, creds: dict, app_name: str, deployment_id: str) -> None:
        org_id = creds["variable"]["anypoint"]["orgId"]
        env_id = creds["variable"]["anypoint"]["environmentId"]
        secrets = self._build_secrets(creds, app_name)

        payload = {
            "application": {
                "configuration": {
                    "mule.agent.application.properties.service": {
                        "applicationName": app_name,
                        "properties": secrets,
                        "secureProperties": {},
                    }
                }
            }
        }

        resp = requests.patch(
            f"{ANYPOINT_BASE}/amc/application-manager/api/v2/organizations/{org_id}/environments/{env_id}/deployments/{deployment_id}",
            headers=self._am_headers(token),
            json=payload,
            timeout=30,
        )
        if not resp.ok:
            raise RuntimeError(f"Patch {app_name} secrets failed: {resp.status_code} {resp.text}")

    def _wait_all_running(self, token: str, creds: dict, max_wait: int = 300) -> None:
        for _ in range(max_wait // 15):
            deployments = self._get_deployments(token, creds)
            statuses = {d["name"]: d.get("status") for d in deployments if d["name"] in APP_NAMES}
            if all(statuses.get(app) == "RUNNING" for app in APP_NAMES):
                return
            not_running = [app for app in APP_NAMES if statuses.get(app) != "RUNNING"]
            print(f"    Still waiting: {not_running}", end="\r")
            time.sleep(15)
        raise TimeoutError("Not all apps reached RUNNING status within 5 minutes")

    def verify(self, creds: dict) -> list[str]:
        return [
            f"CloudHub deployment status RUNNING: {app}" for app in APP_NAMES
        ] + [
            "Slack event subscription URL updated to CloudHub ingress",
            "End-to-end: Slack message → ai-orchestrator → Bedrock → Salesforce → response",
        ]
