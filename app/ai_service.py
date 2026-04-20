import os
import json
import re
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

class AIService:
    def __init__(self):
        self.api_key = os.getenv("GEMMA_API_KEY")
        self.api_url = os.getenv("GEMMA_API_URL", "https://openrouter.ai/api/v1/chat/completions")
        self.model_name = os.getenv("GEMMA_MODEL", "google/gemma-3-4b-it:free")

    async def generate_email(self, user_prompt: str, tone: str = "Professional") -> dict:
        """Original Shuttle One email generation logic."""
        if not self.api_key:
            raise ValueError("GEMMA_API_KEY is not configured.")

        system_prompt = f"""You are 'Shuttle One', a professional email assistant. 
        Your goal is to write a clear, professional email based on the user's intent.
        
        TONE: {tone}
        FORMAT: Return ONLY a JSON object with 'subject' and 'body' fields.
        
        USER INTENT: {user_prompt}
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "Shuttle One"
        }

        messages = [
            {"role": "system", "content": "You are Shuttle One, a professional email expansion agent. Output valid JSON only."},
            {"role": "user", "content": system_prompt}
        ]

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.api_url, headers=headers, json={
                "model": self.model_name,
                "messages": messages,
                "temperature": 0.7
            })
            
            if response.status_code != 200:
                raise Exception(f"AI Service Error: {response.text}")
                
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            
            # Basic extraction
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
                
            parsed = json.loads(content)
            return {
                "subject": parsed.get("subject", "No Subject"),
                "body": parsed.get("body", "No Content"),
                "tone": tone
            }

ai_service = AIService()
