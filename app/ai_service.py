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

        system_prompt = (
            f"Write a {tone} email about: {user_prompt}.\n"
            "Output EXACTLY and ONLY a JSON object with these keys: \"subject\" and \"body\".\n"
            "Use DOUBLE QUOTES for keys and string values. No markdown blocks."
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "Email Genie"
        }

        messages = [
            {"role": "system", "content": "You are a professional email assistant. You respond only with valid JSON according to RFC 8259."},
            {"role": "user", "content": system_prompt}
        ]

        async with httpx.AsyncClient(timeout=9.0) as client:
            try:
                response = await client.post(self.api_url, headers=headers, json={
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": 0.5 # Lower temperature for more stable JSON
                })
            except httpx.TimeoutException:
                raise Exception("AI took too long. Try a shorter prompt.")
            
            if response.status_code != 200:
                raise Exception(f"AI Error: {response.status_code}")
                
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            
            # Clean up markdown formatting if AI skipped instructions
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()

            # Extraction
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                # Fallback for single quotes or malformed JSON
                import ast
                try:
                    parsed = ast.literal_eval(content)
                except Exception:
                    raise Exception(f"AI returned invalid JSON: {content[:100]}...")

            return {
                "subject": parsed.get("subject", "No Subject"),
                "body": parsed.get("body", "No Content"),
                "tone": tone
            }

ai_service = AIService()
