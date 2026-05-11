import imaplib
import os
from dotenv import load_dotenv

load_dotenv()

def test_imap():
    email_user = os.getenv('SMTP_USER', 'samarthshete576@gmail.com')
    email_pass = os.getenv('SMTP_PASS', 'pzba dutp xsqr zprz')
    host = 'imap.gmail.com'

    print(f"Attempting to connect to {host} as {email_user}...")
    try:
        mail = imaplib.IMAP4_SSL(host)
        print("Connected to IMAP server.")
        
        mail.login(email_user, email_pass)
        print("Login successful!")
        
        status, folders = mail.list()
        print(f"Folders found: {len(folders)}")
        
        mail.select('inbox')
        print("Selected INBOX.")
        
        from datetime import datetime, timedelta
        since_date = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")
        print(f"Searching for emails since {since_date}...")
        
        status, ids = mail.search(None, f'(SINCE {since_date})')
        if status == 'OK':
            email_ids = ids[0].split()
            print(f"Found {len(email_ids)} emails in the last 30 days.")
            if email_ids:
                print(f"Latest email ID: {email_ids[-1].decode()}")
        else:
            print(f"Search failed with status: {status}")

        mail.logout()
        print("Logged out.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_imap()
