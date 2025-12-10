import os
import shutil
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# --- IMPORT YOUR EXISTING PIPELINE ---
# This uses the code you already wrote and verified
from graphs.full_pipeline import build_full_pipeline

app = FastAPI(title="AI Code Auditor API")

# Enable CORS (Allows React to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, change to ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize your graph ONCE when server starts
print("⚙️  Initializing AI Pipeline...")
pipeline = build_full_pipeline()
print("✅ AI Agents Ready.")

@app.get("/")
def health_check():
    return {"status": "System Operational", "mode": "Autonomous Agents Active"}

@app.post("/scan")
async def scan_repository(file: UploadFile = File(...)):
    """
    Receives a ZIP file -> Runs YOUR existing pipeline -> Returns YOUR final JSON.
    """
    # 1. Save the uploaded file temporarily
    temp_filename = f"temp_{file.filename}"
    temp_path = os.path.abspath(temp_filename)
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        print(f"\n📥 New Scan Request: {file.filename}")

        # 2. Run YOUR pipeline
        # We pass the exact input structure your graph expects
        inputs = {
            "repo_input": temp_path
        }
        
        # Invoke the graph (Agents 1-6 will run)
        print("🚀 Agents Dispatched...")
        result = pipeline.invoke(inputs)
        print("✅ Analysis Complete.")

        # 3. Extract the final report from your state
        # (Your aggregator node puts it in 'final_output')
        final_report = result.get("final_output", {})

        return JSONResponse(content=final_report)

    except Exception as e:
        print(f"❌ Error during scan: {str(e)}")
        return HTTPException(status_code=500, detail=str(e))
        
    finally:
        # 4. Cleanup the uploaded zip
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    # Start the server
    uvicorn.run("main_api:app", host="0.0.0.0", port=8000, reload=True)