import sys
import os
import json
import asyncio
sys.path.append(os.getcwd())
from routers.lab import calculate_score

async def main():
    print("Verifying Fix...")
    try:
        res = await calculate_score(period="30m", ticker="SOXL", offset=0, limit=20, only_missing=False)
        print("Result:", res)
        # Ensure it works with json dump
        dumped = json.dumps(res)
        print("JSON Dump Success:", dumped)
    except Exception as e:
        print("ERROR:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
