import sys
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# Ensure the root directory is in sys.path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

try:
    from app.main import app
except Exception as e:
    import traceback
    error_details = traceback.format_exc()
    app = FastAPI()
    
    @app.get("/(.*)")
    async def catch_all():
        return HTMLResponse(content=f"""
        <html>
            <body style="font-family: sans-serif; padding: 20px; background: #f8d7da; color: #721c24;">
                <h2>Deployment Error Detected</h2>
                <p>The application failed to start on Vercel. Here is the technical detail:</p>
                <pre style="background: #fff; padding: 10px; border-radius: 5px; overflow: auto;">{error_details}</pre>
                <p><b>Check your Environment Variables</b> (GEMMA_API_KEY, etc.) in the Vercel dashboard.</p>
            </body>
        </html>
        """, status_code=500)
