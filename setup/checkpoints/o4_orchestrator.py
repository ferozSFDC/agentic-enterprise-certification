"""
CP4 — ai-orchestrator Local Setup

What this checkpoint establishes:
- Pre-built ai-orchestrator JAR downloaded to setup/jars/
- .properties file written with correct secrets
- ai-orchestrator process running on port 8082
- GET /health returns 200

Idempotency check: GET http://localhost:8082/health → 200.
"""

from __future__ import annotations

import os
import subprocess
import time
import urllib.request

import requests

from .base import BaseCheckpoint

APP_NAME = "ai-orchestrator"
PORT = 8082
HEALTH_URL = f"http://localhost:{PORT}/health"


class OrchestratorCheckpoint(BaseCheckpoint):
    number = 4
    name = "ai-orchestrator Local Setup"

    def check(self, creds: dict) -> bool:
        try:
            resp = requests.get(HEALTH_URL, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def run(self, creds: dict) -> dict:
        jar_path = self._ensure_jar(creds, APP_NAME)
        props_path = self._write_props(creds, APP_NAME, jar_path)
        self._start_mule(jar_path, props_path, PORT)
        self._wait_healthy(HEALTH_URL)
        return {}

    def _ensure_jar(self, creds: dict, app_name: str) -> str:
        course = creds["stable"]["course"]
        jars_dir = os.path.join(os.path.dirname(__file__), "..", "jars")
        jar_path = os.path.join(jars_dir, f"{app_name}.jar")

        if os.path.exists(jar_path):
            return jar_path

        tag = course["jarReleaseTag"]
        base_url = course["jarReleaseBaseUrl"]
        url = f"{base_url}/{tag}/{app_name}.jar"
        print(f"    Downloading {app_name}.jar from GitHub Release...")
        urllib.request.urlretrieve(url, jar_path)
        print(f"    Downloaded: {jar_path}")
        return jar_path

    def _write_props(self, creds: dict, app_name: str, jar_path: str) -> str:
        props_dir = os.path.join(os.path.dirname(__file__), "..", "jars")
        props_path = os.path.join(props_dir, f"{app_name}.properties")

        aws = creds["stable"]["aws"]
        sf_sc = creds["stable"]["salesforce"]["serviceCloud"]
        gw = creds["stable"]["aiGateway"]
        bedrock = aws["bedrock"]

        lines = [
            f"sfdc.username={creds['variable']['anypoint']['username']}",
            f"sfdc.password={creds['variable']['anypoint']['password']}",
            f"sfdc.token=",
            f"sfdc.clientId={sf_sc['clientId']}",
            f"sfdc.clientSecret={sf_sc['clientSecret']}",
            f"sfdc.tokenEndpoint={sf_sc['tokenEndpoint']}",
            f"ai-gateway.clientId={gw['clientId']}",
            f"ai-gateway.clientSecret={gw['clientSecret']}",
            f"ai-gateway.host={gw['host']}",
            f"aws.accessKeyId={aws['accessKeyId']}",
            f"aws.secretAccessKey={aws['secretAccessKey']}",
            f"aws.region={aws['region']}",
            f"bedrock.agentId={bedrock['agentId']}",
            f"bedrock.agentAliasId={bedrock['agentAliasId']}",
            f"http.port={PORT}",
        ]

        with open(props_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"    Wrote properties: {props_path}")
        return props_path

    def _start_mule(self, jar_path: str, props_path: str, port: int) -> None:
        cmd = [
            "java", "-jar", jar_path,
            f"-Dhttp.port={port}",
            f"-Dmule.config.properties={props_path}",
            "-Dmule.env=local",
        ]
        log_path = jar_path.replace(".jar", ".log")
        with open(log_path, "w") as log_file:
            subprocess.Popen(cmd, stdout=log_file, stderr=log_file, start_new_session=True)
        print(f"    Started {APP_NAME} (logs: {log_path})")

    def _wait_healthy(self, url: str, max_wait: int = 120) -> None:
        print(f"    Waiting for {url}...", end="", flush=True)
        for _ in range(max_wait // 5):
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    print(" ready.")
                    return
            except Exception:
                pass
            time.sleep(5)
            print(".", end="", flush=True)
        raise TimeoutError(f"{url} did not become healthy after {max_wait}s")

    def verify(self, creds: dict) -> list[str]:
        return [
            f"GET {HEALTH_URL} → 200",
            "POST /api/orchestrate returns structured JSON with decision, riskLevel, caseId",
        ]
