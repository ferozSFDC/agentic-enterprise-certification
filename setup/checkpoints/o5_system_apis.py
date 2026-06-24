"""
CP5 — data-cloud-sapi + service-cloud-mcp Local Setup

What this checkpoint establishes:
- data-cloud-sapi JAR running on port 8083, GET /health → 200
- service-cloud-mcp JAR running on port 8084, GET /health → 200

Idempotency check: both health endpoints return 200.
"""

from __future__ import annotations

import os
import subprocess
import time
import urllib.request

import requests

from .base import BaseCheckpoint


class SystemApisCheckpoint(BaseCheckpoint):
    number = 5
    name = "System APIs Local Setup"

    APPS = [
        {
            "name": "data-cloud-sapi",
            "port": 8083,
        },
        {
            "name": "service-cloud-mcp",
            "port": 8084,
        },
    ]

    def check(self, creds: dict) -> bool:
        for app in self.APPS:
            url = f"http://localhost:{app['port']}/health"
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code != 200:
                    return False
            except Exception:
                return False
        return True

    def run(self, creds: dict) -> dict:
        for app in self.APPS:
            jar_path = self._ensure_jar(creds, app["name"])
            props_path = self._write_props(creds, app["name"], jar_path, app["port"])
            self._start_mule(app["name"], jar_path, props_path, app["port"])

        for app in self.APPS:
            url = f"http://localhost:{app['port']}/health"
            self._wait_healthy(app["name"], url)

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
        print(f"    Downloading {app_name}.jar...")
        urllib.request.urlretrieve(url, jar_path)
        return jar_path

    def _write_props(self, creds: dict, app_name: str, jar_path: str, port: int) -> str:
        props_dir = os.path.join(os.path.dirname(__file__), "..", "jars")
        props_path = os.path.join(props_dir, f"{app_name}.properties")

        slack = creds["stable"]["slack"]

        if app_name == "data-cloud-sapi":
            dc = creds["stable"]["salesforce"]["dataCloud"]
            lines = [
                f"sfdc.clientId={dc['clientId']}",
                f"sfdc.clientSecret={dc['clientSecret']}",
                f"sfdc.tokenEndpoint={dc['tokenEndpoint']}",
                f"slack.botToken={slack['botToken']}",
                f"http.port={port}",
            ]
        else:  # service-cloud-mcp
            sc = creds["stable"]["salesforce"]["serviceCloud"]
            lines = [
                f"sfdc.clientId={sc['clientId']}",
                f"sfdc.clientSecret={sc['clientSecret']}",
                f"sfdc.tokenEndpoint={sc['tokenEndpoint']}",
                f"http.port={port}",
            ]

        with open(props_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"    Wrote properties: {props_path}")
        return props_path

    def _start_mule(self, app_name: str, jar_path: str, props_path: str, port: int) -> None:
        cmd = [
            "java", "-jar", jar_path,
            f"-Dhttp.port={port}",
            f"-Dmule.config.properties={props_path}",
            "-Dmule.env=local",
        ]
        log_path = jar_path.replace(".jar", ".log")
        with open(log_path, "w") as log_file:
            subprocess.Popen(cmd, stdout=log_file, stderr=log_file, start_new_session=True)
        print(f"    Started {app_name} on :{port}")

    def _wait_healthy(self, app_name: str, url: str, max_wait: int = 120) -> None:
        print(f"    Waiting for {app_name}...", end="", flush=True)
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
        raise TimeoutError(f"{app_name} did not become healthy after {max_wait}s")

    def verify(self, creds: dict) -> list[str]:
        return [
            "GET http://localhost:8083/health → 200 (data-cloud-sapi)",
            "GET http://localhost:8084/health → 200 (service-cloud-mcp)",
            "MCP tools list includes get_customer_profile and issue_credit",
        ]
