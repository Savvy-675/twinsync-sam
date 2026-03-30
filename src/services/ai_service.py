from groq import Groq
from src.config.config import Config
import logging
import json

logger = logging.getLogger('AIService')

class AIService:
    @staticmethod
    def generate_simulated_response(context, error_msg="AI Configuration Required"):
        acc = context.get('acc', 0)
        samps = context.get('samps', 0)
        return f"""### ⚠️ AI Configuration Required

Your Digital Twin is currently in **Local Safe Mode** because the AI keys are missing from your hosting environment.

**How to Fix:**
1. Go to your hosting provider settings (e.g., Render, Heroku).
2. Find the **Environment Variables** or **Secrets** section.
3. Add `GROQ_API_KEY` (highly recommended) or `GEMINI_API_KEY`.
4. Restart your service.

**System Data:**
- Accuracy: {acc}%
- Samples: {samps}
"""

    @staticmethod
    def detect_task_intent(prompt):
        """
        Use LLaMA 3 to detect if the user wants to create a task.
        Returns a task dict if intent detected, else None.
        """
        if not Config.GROQ_API_KEY or len(Config.GROQ_API_KEY) < 10:
            return None
        try:
            client = Groq(api_key=Config.GROQ_API_KEY)
            detection_prompt = f"""Analyze if this message is asking to add/create a task or reminder.

Message: "{prompt}"

If YES, extract and return ONLY this JSON:
{{"is_task": true, "title": "task title", "deadline": "natural language deadline or null", "category": "work|study|personal|general", "priority": null}}

If NO (just a question or conversation), return ONLY:
{{"is_task": false}}

Return ONLY the JSON. Nothing else."""

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": detection_prompt}],
                max_tokens=100,
                temperature=0.1
            )
            raw = response.choices[0].message.content.strip()
            raw = raw.replace('```json', '').replace('```', '').strip()
            result = json.loads(raw)
            return result if result.get('is_task') else None
        except Exception as e:
            logger.error(f"Task intent detection failed: {e}")
            return None

    @staticmethod
    def generate_chat_response(prompt, context):
        pending_tasks_str = context.get('pending_tasks', 'No pending tasks')
        system_instruction = f"""You are a Digital Twin productivity assistant — a smart, aware, and supportive AI coach.

User's Current State:
- ML Samples: {context.get('samps')}
- ML Accuracy: {context.get('acc')}%
- Peak Focus Factor: {context.get('top_f')}
- Active Pending Tasks: {pending_tasks_str}

Strict Rules:
1. ONLY suggest tasks from the "Active Pending Tasks" list above. NEVER invent or suggest tasks not on this list.
2. If the user asks what to do next, recommend the highest priority task from the pending list.
3. If a task has already been completed, it will NOT appear in the pending list — do not reference it.
4. If the pending list is empty, tell the user they have no active tasks and encourage them to add new ones.
5. Be concise, supportive and data-driven. Use Markdown for formatting.
6. If the user is creating a task, confirm it naturally (e.g. \"Got it! I've added X to your task list.\")"""

        last_error = "Environment keys (GROQ_API_KEY / GEMINI_API_KEY) are missing or too short."
        
        # 🥇 PRIMARY: Groq (LLaMA 3)
        if Config.GROQ_API_KEY and len(Config.GROQ_API_KEY) > 5:
            try:
                client = Groq(api_key=Config.GROQ_API_KEY)
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=512,
                    temperature=0.7,
                )
                return response.choices[0].message.content
            except Exception as e:
                last_error = f"Groq Error: {str(e)}"
                logger.error(last_error)

        # 🥈 FALLBACK: Gemini
        if Config.GEMINI_API_KEY and len(Config.GEMINI_API_KEY) > 5:
            try:
                from google import genai
                client = genai.Client(api_key=Config.GEMINI_API_KEY)
                response = client.models.generate_content(
                    model='gemini-1.5-flash',
                    config={'system_instruction': system_instruction},
                    contents=prompt
                )
                return response.text
            except Exception as e:
                last_error = f"Gemini Error: {str(e)}"
                logger.error(last_error)

        # 🛑 FINAL: Local simulation (with debug info)
        return AIService.generate_simulated_response(context, error_msg=last_error)
