from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
import os
import json
import re
from .ai_service import ai_service
from .email_service import email_service

app = FastAPI(title="Shuttle One")

# Setup paths - ensure they are absolute
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
static_path = str(BASE_DIR / "static")
templates_path = str(BASE_DIR / "templates")

app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=templates_path)

# --- Models ---
class GenerateRequest(BaseModel):
    prompt: str
    tone: str = "Professional"

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/generate")
async def generate_email_api(request: GenerateRequest):
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    try:
        result = await ai_service.generate_email(request.prompt, request.tone)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/extract-emails")
async def extract_emails_api(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    filename_lower = file.filename.lower()
    if not filename_lower.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="Only Excel (.xlsx, .xls) or CSV (.csv) files are supported")
    
    try:
        import pandas as pd
        import re
        from io import BytesIO
        
        content = await file.read()
        
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        if filename_lower.endswith('.csv'):
            df = pd.read_csv(BytesIO(content))
        else:
            df = pd.read_excel(BytesIO(content))
        
        if df.empty:
            raise HTTPException(status_code=400, detail="The file contains no data")
        
        # Flatten and regex search for emails
        all_text = " ".join(df.astype(str).values.flatten())
        email_regex = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        emails = list(set(re.findall(email_regex, all_text)))
        
        # Filter out obvious non-emails (e.g., "nan@nan.nan")
        emails = [e for e in emails if not e.startswith('nan@')]
        
        return {"emails": emails, "count": len(emails)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

@app.post("/api/send")
async def send_email_api(
    subject: str = Form(...),
    body: str = Form(...),
    recipients: str = Form(...),
    attachments: Optional[List[UploadFile]] = File(None)
):
    # Parse recipients JSON
    try:
        recipient_list = json.loads(recipients)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid recipients format. Expected a JSON array of email addresses.")

    if not isinstance(recipient_list, list) or not recipient_list:
        raise HTTPException(status_code=400, detail="No recipients provided. Add at least one email address.")
    
    # Validate email format
    email_pattern = re.compile(r'^\S+@\S+\.\S+$')
    invalid_emails = [e for e in recipient_list if not email_pattern.match(e)]
    if invalid_emails:
        raise HTTPException(status_code=400, detail=f"Invalid email address(es): {', '.join(invalid_emails[:5])}")
    
    # Prepare attachments and check size
    processed_attachments = []
    total_size = 0
    MAX_SIZE = 20 * 1024 * 1024  # 20MB limit
    
    if attachments:
        for file in attachments:
            if file.filename:  # Skip empty/placeholder file uploads
                file_content = await file.read()
                if file_content:  # Only process non-empty files
                    total_size += len(file_content)
                    if total_size > MAX_SIZE:
                        raise HTTPException(
                            status_code=400, 
                            detail=f"Total attachment size ({total_size / (1024*1024):.1f}MB) exceeds 20MB limit."
                        )
                    processed_attachments.append((
                        file.filename, 
                        file_content, 
                        file.content_type or "application/octet-stream"
                    ))
    
    success, message = email_service.send_to_multiple(
        subject, 
        body, 
        recipient_list,
        attachments=processed_attachments if processed_attachments else None
    )
    
    if success:
        return {"message": message, "sent_to": len(recipient_list)}
    else:
        raise HTTPException(status_code=500, detail=message)

@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "ok",
        "ai_configured": bool(ai_service.api_key),
        "smtp_configured": bool(email_service.username and email_service.password)
    }
