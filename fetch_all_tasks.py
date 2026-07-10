#!/usr/bin/env python3
"""Fetch all tasks from 6 Zentao executions via API."""
import requests
import json
import os
import sys

BASE = "https://ztpm.gree.com:8888"
ACCOUNT = "260298"
PASSWORD = "Lss@530720"

# Executions to fetch
EXECUTIONS = [4519, 4651, 4697, 4665, 4672, 4671]

def login():
    """Login and return token."""
    r = requests.post(
        f"{BASE}/api.php/v2/users/login",
        json={"account": ACCOUNT, "password": PASSWORD},
        # Disable SSL verification for self-signed cert
    )
    resp = r.json()
    token = resp.get("token", "")
    if not token:
        print(f"Login failed: {resp}")
        sys.exit(1)
    return token

def fetch_tasks(token, exec_id):
    """Fetch all tasks for an execution, handle pagination."""
    all_tasks = []
    page = 1
    while True:
        r = requests.get(
            f"{BASE}/api.php/v2/executions/{exec_id}/tasks",
            headers={"token": token},
            params={"status": "all", "recPerPage": 100, "pageID": page, "orderBy": "id_desc"},
        )
        data = r.json()
        tasks = data.get("tasks", [])
        if not tasks:
            break
        all_tasks.extend(tasks)
        if len(tasks) < 100:
            break
        page += 1
    
    return all_tasks

def main():
    token = login()
    print(f"Logged in, token: {token[:20]}...")
    
    for exec_id in EXECUTIONS:
        print(f"Fetching execution {exec_id}...")
        tasks = fetch_tasks(token, exec_id)
        data = {"tasks": tasks, "total": len(tasks)}
        fp = f"/tmp/tasks_{exec_id}.json"
        with open(fp, "w") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"  Saved {len(tasks)} tasks to {fp}")

    print("Done!")

if __name__ == "__main__":
    main()
