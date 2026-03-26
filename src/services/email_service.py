import imaplib
import email as email_lib
import json
import logging
from datetime import datetime, timedelta
from src.config.config import Config

logger = logging.getLogger('EmailService')

# Keywords that trigger task extraction
TASK_KEYWORDS = [
    'meeting', 'assignment', 'deadline', 'due', 'task', 'submit',
    'exam', 'project', 'review', 'presentation', 'interview', 'call',
    'urgent', 'reminder', 'action required', 'please complete'
]

IGNORE_KEYWORDS = [
    'snapchat', 'instagram', 'facebook', 'tiktok', 'twitter', 'x.com',
    'promotion', 'sale', 'offer', 'discount', 'newsletter', 'unsubscribe',
    'marketing', 'spam', 'deal'
]

PRIORITY_DOMAINS = [
    '.edu', 'classroom.google.com', 'linkedin.com', 'calendar.google.com'
]

class EmailService:
    @staticmethod
    def fetch_emails(user, max_emails=20):
        """Connect to user's personalized mail server."""
        if not user or not user.email_user or not user.email_pass_encrypted:
            logger.warning(f"No email credentials for user {user.id if user else 'Unknown'}")
            return []

        try:
            # Basic Decryption (Base64 for this 'basic' requirement)
            import base64
            password = base64.b64decode(user.email_pass_encrypted).decode()
            
            host = user.imap_server or 'imap.gmail.com'
            mail = imaplib.IMAP4_SSL(host)
            mail.login(user.email_user, password)
            mail.select('inbox')

            # Search for recent emails (last 3 days)
            since_date = (datetime.now() - timedelta(days=3)).strftime("%d-%b-%Y")
            _, ids = mail.search(None, f'(SINCE {since_date})')
            
            email_ids = ids[0].split()[-max_emails:]  # Latest N emails
            emails = []

            for eid in email_ids:
                _, msg_data = mail.fetch(eid, '(RFC822)')
                msg = email_lib.message_from_bytes(msg_data[0][1])
                
                subject = msg.get('Subject', '')
                sender = msg.get('From', '')
                body = ''

                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == 'text/plain':
                            try:
                                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')[:500]
                            except:
                                pass
                            break
                else:
                    try:
                        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')[:500]
                    except:
                        pass

                emails.append({
                    'subject': subject,
                    'sender': sender,
                    'body': body,
                    'id': eid.decode()
                })

            mail.logout()
            return emails

        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            return []

    @staticmethod
    def filter_task_emails(emails):
        """Filter emails containing task-related keywords or from priority sources."""
        task_emails = []
        for e in emails:
            text = (e['subject'] + ' ' + e['body']).lower()
            sender = e['sender'].lower()
            
            # Explicitly Ignore low-value emails
            if any(kw in text or kw in sender for kw in IGNORE_KEYWORDS):
                continue

            is_priority_source = any(domain in sender for domain in PRIORITY_DOMAINS)
            has_urgent_keyword = any(kw in text for kw in TASK_KEYWORDS)
            
            if is_priority_source or has_urgent_keyword:
                task_emails.append(e)
                
        return task_emails

    @staticmethod
    def extract_task_from_email(email_data):
        """Use Groq LLaMA 3 to extract a structured task from an email."""
        if not Config.GROQ_API_KEY:
            return None
        try:
            from groq import Groq
            client = Groq(api_key=Config.GROQ_API_KEY)
            
            prompt = f"""Extract a task from this email. Return ONLY a JSON object with these exact keys:
{{
  "title": "short task title (max 60 chars)",
  "deadline": "ISO datetime string or null",
  "category": "work|study|personal|general",
  "priority": "critical|high|medium|low or null"
}}

Email Subject: {email_data['subject']}
Email Body: {email_data['body'][:300]}

Rules:
- If no deadline is mentioned, return null for deadline.
- ONLY create task if deadline exists, event is scheduled, or action is required. If not, return {{"title": ""}}.
- URGENCY DETECTION: If the deadline is within 1 to 5 days, strictly mark priority as "high" or "critical".
- Return ONLY the JSON, nothing else."""

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.1,
            )
            
            raw = response.choices[0].message.content.strip()
            # Clean up markdown code blocks if present
            raw = raw.replace('```json', '').replace('```', '').strip()
            return json.loads(raw)
        except Exception as e:
            logger.error(f"Task extraction from email failed: {e}")
            return None

    @staticmethod
    def fetch_and_parse_emails(user_id):
        """Main entry: fetch, filter, extract, and return tasks from user's mail."""
        from src.models.all_models import User
        user = User.query.get(user_id)
        if not user: return []
        
        tasks_created = []
        emails = EmailService.fetch_emails(user)
        logger.info(f"User {user_id}: Fetched {len(emails)} emails. Filtering...")

        task_emails = EmailService.filter_task_emails(emails)
        logger.info(f"Found {len(task_emails)} task-related emails.")

        for e in task_emails:
            extracted = EmailService.extract_task_from_email(e)
            if extracted and extracted.get('title'):
                extracted['user_id'] = user_id
                extracted['source'] = 'email'
                tasks_created.append(extracted)

        return tasks_created
