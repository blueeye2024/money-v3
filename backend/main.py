
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from analysis import run_analysis
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For dev, allow all. In prod, lock down.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import asyncio

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/report")
def get_report():
    try:
        # Run analysis in a separate thread to ensure asyncio loop isn't blocked 
        # (though yf is blocking, FastAPI handles def as threaded, async def needs await)
        # Since uvicorn runs 'def' in threadpool, and we defined it as 'async def' but used blocking call...
        # Wait, if we use 'async def', we should NOT block the loop.
        # But 'run_analysis' is blocking. 
        # So we should run it in a threadpool executor or just change to 'def get_report():'
        
        # Let's change to 'def' to let FastAPI handle threading automatically.
        # This is safer for blocking I/O like yfinance.
        data = run_analysis()
        return data
    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
