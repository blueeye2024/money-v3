
import sys
import os
import json
import asyncio
sys.path.append(os.getcwd())

from routers.lab import calculate_score

async def main():
    print("Running calculate_score...")
    try:
        # Simulate the call
        result = await calculate_score(period="30m", ticker="SOXL", offset=0, limit=200, only_missing=True)
        print("Result Type:", type(result))
        print("Result:", result)
        
        # Test serialization
        print("Attempting JSON dump...")
        serialized = json.dumps(result)
        print("Serialization Success:", serialized)
        
    except Exception as e:
        print("Caught Exception:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
