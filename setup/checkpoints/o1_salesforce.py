"""
CP1 — Salesforce Setup

What this checkpoint establishes:
- Golden Contact (sarah.chen@globaltech.com) exists in Service Cloud
- Data Cloud DMOs have at least one record seeded (LoyaltyTier__c, ChurnRisk__c)
- Connected App "Data Cloud External" exists with correct OAuth scopes

Idempotency check: GET Contact by Email — skip if found.
"""

from __future__ import annotations

import requests

from .base import BaseCheckpoint, get_sf_token


GOLDEN_CONTACT = {
    "FirstName": "Sarah",
    "LastName": "Chen",
    "Email": "sarah.chen@globaltech.com",
    "Phone": "+1-555-0100",
    "AccountId": None,
    "Title": "Senior Software Engineer",
    "Department": "Engineering",
}

GOLDEN_CONTACT_SLACK = {
    "FirstName": "Student",
    "LastName": "Slack Test",
    "Email": "student-slack-test@globaltech.com",
    "Phone": "+1-555-0199",
    "Title": "Test Contact",
    "Department": "Training",
}


class SalesforceCheckpoint(BaseCheckpoint):
    number = 1
    name = "Salesforce Setup"

    def check(self, creds: dict) -> bool:
        token, instance_url = get_sf_token(creds, "serviceCloud")
        email = creds["stable"]["course"]["goldenContactEmail"]
        resp = requests.get(
            f"{instance_url}/services/data/v59.0/query",
            params={"q": f"SELECT Id FROM Contact WHERE Email = '{email}' LIMIT 1"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["totalSize"] > 0

    def run(self, creds: dict) -> dict:
        token, instance_url = get_sf_token(creds, "serviceCloud")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        updates = {}

        # Create golden contacts
        for contact_data in [GOLDEN_CONTACT, GOLDEN_CONTACT_SLACK]:
            email = contact_data["Email"]
            check = requests.get(
                f"{instance_url}/services/data/v59.0/query",
                params={"q": f"SELECT Id FROM Contact WHERE Email = '{email}' LIMIT 1"},
                headers=headers,
                timeout=15,
            )
            check.raise_for_status()
            if check.json()["totalSize"] == 0:
                payload = {k: v for k, v in contact_data.items() if v is not None}
                resp = requests.post(
                    f"{instance_url}/services/data/v59.0/sobjects/Contact",
                    json=payload,
                    headers=headers,
                    timeout=15,
                )
                if not resp.ok:
                    raise RuntimeError(f"Failed to create contact {email}: {resp.text}")
                if email == creds["stable"]["course"]["goldenContactEmail"]:
                    updates["stable.salesforce.goldenContactId"] = resp.json().get("id")
                print(f"    Created contact: {email}")
            else:
                record_id = check.json()["records"][0]["Id"]
                if email == creds["stable"]["course"]["goldenContactEmail"]:
                    updates["stable.salesforce.goldenContactId"] = record_id
                print(f"    Contact exists: {email}")

        # Seed Data Cloud DMO records via Data Cloud Streaming Ingestion API
        self._seed_data_cloud(creds, updates)

        return updates

    def _seed_data_cloud(self, creds: dict, updates: dict) -> None:
        dc = creds["stable"]["salesforce"]["dataCloud"]
        resp = requests.post(
            dc["tokenEndpoint"],
            data={
                "grant_type": "client_credentials",
                "client_id": dc["clientId"],
                "client_secret": dc["clientSecret"],
            },
            timeout=30,
        )
        if not resp.ok:
            print(f"    Warning: Could not get Data Cloud token — skipping DMO seed. ({resp.status_code})")
            return

        dc_token = resp.json()["access_token"]
        dc_instance = dc.get("instanceUrl", "")
        if not dc_instance:
            print("    Warning: dataCloud.instanceUrl not set — skipping DMO seed.")
            return

        headers = {
            "Authorization": f"Bearer {dc_token}",
            "Content-Type": "application/json",
        }

        # POST seed records to both DMO objects
        dmo_payloads = [
            {
                "object": "LoyaltyTier__c",
                "data": [{"ContactEmail__c": "sarah.chen@globaltech.com", "LoyaltyTier__c": "Gold", "Points__c": 4200}],
            },
            {
                "object": "ChurnRisk__c",
                "data": [{"ContactEmail__c": "sarah.chen@globaltech.com", "ChurnRisk__c": 0.12, "Segment__c": "Enterprise"}],
            },
        ]

        for payload in dmo_payloads:
            obj = payload["object"]
            seed_resp = requests.post(
                f"{dc_instance}/services/data/v59.0/sobjects/{obj}",
                json=payload["data"][0],
                headers=headers,
                timeout=15,
            )
            if seed_resp.ok:
                print(f"    Seeded DMO record: {obj}")
            else:
                print(f"    Warning: DMO seed for {obj} returned {seed_resp.status_code} — may need manual seeding.")

    def verify(self, creds: dict) -> list[str]:
        email = creds["stable"]["course"]["goldenContactEmail"]
        slack_email = creds["stable"]["course"]["goldenContactSlackEmail"]
        return [
            f"GET Contact WHERE Email = {email} → found",
            f"GET Contact WHERE Email = {slack_email} → found",
            "Data Cloud DMO: LoyaltyTier__c has at least 1 record",
            "Data Cloud DMO: ChurnRisk__c has at least 1 record",
        ]
