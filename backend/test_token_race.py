import sys
import os
import multiprocessing
import time
from datetime import datetime

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from kis_api import KisApi

def attempt_issue(idx):
    print(f"[{idx}] Worker starting...")
    api = KisApi()
    # Force issue (bypass file check for test, or delete file before?)
    # We call _issue_token directly to test locking
    token = api._issue_token()
    if token:
        print(f"[{idx}] ✅ Got Token: {token[:10]}...")
    else:
        print(f"[{idx}] ❌ Failed to get token")

def run_race_test():
    print("--- STARTING TOKEN RACE TEST ---")
    
    # 1. Backup existing token
    if os.path.exists("kis_token.json"):
        os.rename("kis_token.json", "kis_token.json.bak")
        print("Backed up existing token.")
        
    processes = []
    for i in range(3): # Spawn 3 workers
        p = multiprocessing.Process(target=attempt_issue, args=(i,))
        processes.append(p)
        p.start()
        
    for p in processes:
        p.join()
        
    print("--- RACE TEST COMPLETE ---")
    
    # Check if file exists
    if os.path.exists("kis_token.json"):
        with open("kis_token.json") as f:
            print("Final Token File:", f.read()[:50] + "...")
        
        # Restore backup
        # os.remove("kis_token.json")
        # os.rename("kis_token.json.bak", "kis_token.json")
    else:
        print("❌ Token file NOT created!")

    if os.path.exists("kis_token.json.bak"):
        os.rename("kis_token.json.bak", "kis_token.json")
        print("Restored original token.")

if __name__ == "__main__":
    run_race_test()
