"""
FastAPI Server for DDR Generator
Exposes the generation pipeline as a REST API.
"""
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import existing pipeline
from ddr_generator.main import DDRPipeline
from ddr_generator.config import config

app = FastAPI(title="DDR Generator API", version="1.0.0")

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Enable CORS (allow all for now, or restrict to own domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve Frontend Static Files (Production)
# Mount assets likely at /assets or root? 
# Vite builds to /assets usually.
# However, we want root / to serve index.html
# And /assets/ to serve js/css

# Check if frontend build exists
frontend_dist = Path("frontend/dist")
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    # Serve index.html for root and any non-api routes (SPA support)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        
        # Check if file exists in dist (e.g. vite.svg)
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
            
        # Fallback to index.html for React Router
        return FileResponse(frontend_dist / "index.html")
else:
    print("WARNING: Frontend build not found. Run 'npm run build' in /frontend")

# Temporary directory for uploads
UPLOAD_DIR = Path("temp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = Path("ddr_generator/output")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

class AnalysisResponse(BaseModel):
    success: bool
    report_md: str
    report_json: Dict[str, Any]
    filename: str

@app.get("/api/status")
async def get_status():
    """Health check endpoint"""
    return {
        "status": "online",
        "llm_provider": config.api.llm_provider,
        "model": config.api.groq_model if config.api.llm_provider == "groq" else "unknown"
    }

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_report(
    inspection_file: UploadFile = File(...),
):
    """
    Process uploaded PDF and generate DDR report
    """
    if not inspection_file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Save uploaded file temporarily
    temp_path = UPLOAD_DIR / inspection_file.filename
    try:
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(inspection_file.file, buffer)
            
        # Run pipeline
        try:
            print(f"Starting analysis for: {temp_path}")
            pipeline = DDRPipeline(llm_provider=config.api.llm_provider)
            
            # The pipeline returns the generated report object
            # We need to capture the file paths it created
            print(f"DEBUG: Calling pipeline.process method on {pipeline}")
            print(f"DEBUG: Has process? {hasattr(pipeline, 'process')}")
            print(f"DEBUG: Has process_files? {hasattr(pipeline, 'process_files')}")
            
            report = pipeline.process(
                inspection_pdf_path=str(temp_path),
                thermal_pdf_path=None,  # Thermal optional for now
                output_dir=str(OUTPUT_DIR)
            )
            
            # Read the generated markdown content
            # Pipeline saves to output folder with timestamp
            # We need to find the latest file or return the content directly
            # Since pipeline method doesn't return path, let's find the latest file
            # Or better, modify pipeline to return paths?
            # For now, let's just find the latest created file matching the input name
            
            # Actually, let's read the object returned 'report' and format it immediately?
            # No, the 'pipeline.process_files' returns the populated DDRReport object.
            # We can re-generate the markdown string here to send back to frontend!
            
            # Find the generated report file
            # Pipeline saves as {filename}_DDR_{timestamp}.md
            # We'll look for the most recent .md file in output folder
            
            import glob
            import os
            
            # Pattern: OUTPUT_DIR / specific_filename_pattern
            # Note: filename without extension
            base_name = Path(inspection_file.filename).stem
            search_pattern = str(OUTPUT_DIR / f"{base_name}_DDR_*.md")
            
            files = glob.glob(search_pattern)
            if not files:
                 raise Exception("Report file not found after generation")
                 
            # Get latest file
            md_path = max(files, key=os.path.getctime)
            json_path = md_path.replace('.md', '.json')
            
            print(f"DEBUG: Found generated report at {md_path}")
            
            with open(md_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
                
            import json
            with open(json_path, 'r', encoding='utf-8') as f:
                json_content = json.load(f)
                
            return AnalysisResponse(
                success=True,
                report_md=md_content,
                report_json=json_content,
                filename=Path(md_path).name
            )
            
        except Exception as e:
            print(f"Pipeline error: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
            
    finally:
        # Cleanup upload
        if temp_path.exists():
            try:
                os.remove(temp_path)
            except:
                pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
