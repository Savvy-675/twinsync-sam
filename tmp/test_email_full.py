import imaplib
import os
import json
import email as email_lib
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

# Constants from email_service.py
TASK_KEYWORDS = [
    'meeting', 'assignment', 'deadline', 'due', 'task', 'submit',
    'exam', 'project', 'review', 'presentation', 'interview', 'call',
    'urgent', 'reminder', 'action required', 'please complete', 'invitation'
]

IGNORE_KEYWORDS = [
    'snapchat', 'instagram', 'facebook', 'tiktok', 'twitter', 'x.com',
    'promotion', 'sale', 'offer', 'discount', 'newsletter', 'unsubscribe',
    'marketing', 'spam', 'deal', 'verification code', 'otp', 'security alert',
    'stories', 'friend request', 'followed you'
]

PRIORITY_DOMAINS = [
    '.edu',                             # Academic
    'classroom.google.com',             # Google Classroom
    'linkedin.com',                     # Professional (filtered later in prompt)
    'calendar.google.com',              # Calendar invites
    'teams.microsoft.com',              # Work/Official
    'slack.com'                         # Work/Official
]

def test_extraction():
    email_user = os.getenv('SMTP_USER', 'samarthshete576@gmail.com')
    email_pass = os.getenv('SMTP_PASS', 'pzba dutp xsqr zprz')
    groq_api_key = os.getenv('GROQ_API_KEY')
    host = 'imap.gmail.com'

    print(f"Connecting to {host}...")
    try:
        mail = imaplib.IMAP4_SSL(host)
        mail.login(email_user, email_pass)
        mail.select('inbox')
        
        since_date = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")
        _, ids = mail.search(None, f'(SINCE {since_date})')
        email_ids = ids[0].split()[-20:]  # Last 20
        
        print(f"Checking {len(email_ids)} latest emails...")
        
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
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')[:500]
                        break
            else:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')[:500]
            
            emails.append({'subject': subject, 'sender': sender, 'body': body})

        print("Filtering...")
        task_emails = []
        for e in emails:
            text = (e['subject'] + ' ' + e['body']).lower()
            sender = e['sender'].lower()
            if any(kw in text or kw in sender for kw in IGNORE_KEYWORDS):
                continue
            is_priority_source = any(domain in sender for domain in PRIORITY_DOMAINS)
            has_urgent_keyword = any(kw in text for kw in TASK_KEYWORDS)
            if is_priority_source or has_urgent_keyword:
                task_emails.append(e)

        print(f"Found {len(task_emails)} task-related emails out of {len(emails)} checked.")
        for te in task_emails:
            print(f"- Task Email: {te['subject']} (from {te['sender']})")

        if task_emails and groq_api_key:
            print("\nTesting Groq Extraction on first match...")
            from groq import Groq
            client = Groq(api_key=groq_api_key)
            email_data = task_emails[1]
            prompt = f"""Extract a task from this email. Return ONLY a JSON object with these exact keys:
{{
  "title": "short task title (max 60 chars)",
  "deadline": "ISO datetime string or null",
  "category": "work|study|personal|general",
  "priority": "critical|high|medium|low or null"
}}

Email Subject: {email_data['subject']}
Email Body: {email_data['body'][:300]}
Sender: {email_data['sender']}

Rules:
- If no deadline is mentioned, return null for deadline.
- ONLY create task if deadline exists, event is scheduled, or action is required. If not, return {{"title": ""}}.
- Return ONLY the JSON, nothing else.
"""
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.1,
            )
            raw = response.choices[0].message.content.strip()
            print(f"Groq Response: {raw}")

        mail.logout()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_extraction()
