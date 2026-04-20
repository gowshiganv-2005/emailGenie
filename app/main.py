from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
import os
import json
import re
from app.ai_service import ai_service
from app.email_service import email_service

app = FastAPI(title="Email Genie")

# Setup paths - serverless safe detection
from pathlib import Path
import os

# Try multiple possible locations for static/templates
POSSIBLE_ROOTS = [
    Path(__file__).resolve().parent,           # /app/
    Path(__file__).resolve().parent.parent,    # /root/
    Path(__file__).resolve().parent.parent / "api", # /root/api/ (for Vercel bundling)
    Path.cwd(),                                # current working dir
    Path.cwd() / "api"                         # /api/ in CWD
]

static_path = None
templates_path = None

for root in POSSIBLE_ROOTS:
    s = root / "static"
    t = root / "templates"
    if s.is_dir() and (s / "style.css").exists(): # Verify it's the right static folder
        static_path = str(s)
    if t.is_dir() and (t / "index.html").exists():
        templates_path = str(t)
    if static_path and templates_path:
        break

# Initialize components with safety checks
if static_path:
    app.mount("/static", StaticFiles(directory=static_path), name="static")

templates = None
if templates_path:
    try:
        from fastapi.templating import Jinja2Templates
        templates = Jinja2Templates(directory=templates_path)
    except Exception:
        templates = None

# --- Models ---
class GenerateRequest(BaseModel):
    prompt: str
    tone: str = "Professional"

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if templates:
        try:
            return templates.TemplateResponse("index.html", {"request": request})
        except Exception:
            pass
    
    # Diagnostic info for debugging
    diag = []
    try:
        diag.append(f"CWD: {os.getcwd()}")
        diag.append(f"File: {__file__}")
        diag.append(f"Roots searched: {[str(r) for r in POSSIBLE_ROOTS]}")
        # List items in root_dir
        root_dir = Path(__file__).resolve().parent.parent
        diag.append(f"Root dir content: {os.listdir(str(root_dir)) if root_dir.exists() else 'N/A'}")
        if (root_dir / "api").exists():
            diag.append(f"API dir content: {os.listdir(str(root_dir / 'api'))}")
    except Exception as e:
        diag.append(f"Error listing: {e}")

    diag_html = "".join([f"<li>{d}</li>" for d in diag])

    # Fallback if templates are missing in serverless environment
    return f"""
    <html>
        <head><title>Email Genie | Serverless Fallback</title></head>
        <body style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>Email Genie AI</h1>
            <p>The application is running, but UI templates could not be located.</p>
            <p>Please check your deployment structure.</p>
            <hr>
            <div style="text-align: left; background: #eee; padding: 15px; display: inline-block; border-radius: 8px;">
                <h3>Diagnostics:</h3>
                <ul>{diag_html}</ul>
            </div>
            <hr>
            <p><small>Backend Status: OK</small></p>
        </body>
    </html>
    """

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
