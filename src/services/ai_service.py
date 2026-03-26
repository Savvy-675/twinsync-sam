from groq import Groq
from src.config.config import Config
import logging
import json

logger = logging.getLogger('AIService')

class AIService:
    @staticmethod
    def generate_simulated_response(context):
        acc = context.get('acc', 0)
        samps = context.get('samps', 0)
        return f"""**Your Digital Twin is responding in local mode!** 🧠✨

Based on your current ML Synchrony:
 - **Accuracy:** {acc}%
 - **History:** {samps} Samples
 - **Status:** Local Processing Active

You are currently performing as a **'High-Efficiency Architect'**. 
I recommend focusing on your next high-priority task. Is there anything else I can help you with?"""

    @staticmethod
    def detect_task_intent(prompt):
        """
        Use LLaMA 3 to detect if the user wants to create a task.
        Returns a task dict if intent detected, else None.
        """
        if not Config.GROQ_API_KEY:
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

        # 🥇 PRIMARY: Groq (LLaMA 3)
        if Config.GROQ_API_KEY:
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
                logger.info("Groq LLaMA 3 response generated.")
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"Groq API failure: {e}")

        # 🥈 FALLBACK: Gemini
        if Config.GEMINI_API_KEY:
            try:
                from google import genai
                client = genai.Client(api_key=Config.GEMINI_API_KEY)
                for model_id in ['gemini-1.5-flash', 'gemini-2.0-flash']:
                    try:
                        response = client.models.generate_content(
                            model=model_id,
                            config={'system_instruction': system_instruction},
                            contents=prompt
                        )
                        return response.text
                    except Exception as e:
                        if "404" in str(e) or "not found" in str(e).lower():
                            continue
                        break
            except Exception as e:
                logger.error(f"Gemini fallback failure: {e}")

        # 🛑 FINAL: Local simulation
        return AIService.generate_simulated_response(context)
