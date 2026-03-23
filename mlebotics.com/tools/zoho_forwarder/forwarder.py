"""
Zoho Mail Forwarder
Connects to Zoho IMAP, fetches unseen messages, and forwards them via SMTP.
Reads ZOHO_USER, ZOHO_APP_PASSWORD, and FORWARD_TO from environment variables.
"""

import imaplib
import smtplib
import os
import sys
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

IMAP_HOST = "imap.zoho.com"
IMAP_PORT = 993
SMTP_HOST = "smtp.zoho.com"
SMTP_PORT = 587

ZOHO_USER = os.environ["ZOHO_USER"]
ZOHO_APP_PASSWORD = os.environ["ZOHO_APP_PASSWORD"]
FORWARD_TO = os.environ["FORWARD_TO"]


def fetch_unseen_messages(imap):
    imap.select("INBOX")
    status, data = imap.search(None, "UNSEEN")
    if status != "OK":
        return []
    ids = data[0].split()
    messages = []
    for msg_id in ids:
        status, msg_data = imap.fetch(msg_id, "(RFC822)")
        if status == "OK":
            messages.append((msg_id, email.message_from_bytes(msg_data[0][1])))
    return messages


def forward_message(smtp, original_msg, from_addr, to_addr):
    fwd = MIMEMultipart()
    fwd["From"] = from_addr
    fwd["To"] = to_addr
    fwd["Subject"] = "Fwd: " + original_msg.get("Subject", "(no subject)")

    # Preserve original headers as a text preamble
    preamble = (
        f"---------- Forwarded message ----------\n"
        f"From: {original_msg.get('From', '')}\n"
        f"Date: {original_msg.get('Date', '')}\n"
        f"Subject: {original_msg.get('Subject', '')}\n"
        f"To: {original_msg.get('To', '')}\n\n"
    )

    if original_msg.is_multipart():
        fwd.attach(MIMEText(preamble, "plain"))
        for part in original_msg.walk():
            content_type = part.get_content_type()
            disposition = part.get("Content-Disposition", "")
            if content_type in ("text/plain", "text/html") and "attachment" not in disposition:
                fwd.attach(MIMEText(part.get_payload(decode=True).decode("utf-8", errors="replace"), content_type.split("/")[1]))
            elif "attachment" in disposition or part.get_filename():
                attachment = MIMEBase(*content_type.split("/"))
                attachment.set_payload(part.get_payload(decode=True))
                encoders.encode_base64(attachment)
                attachment.add_header("Content-Disposition", disposition, filename=part.get_filename())
                fwd.attach(attachment)
    else:
        body = preamble + (original_msg.get_payload(decode=True) or b"").decode("utf-8", errors="replace")
        fwd.attach(MIMEText(body, "plain"))

    smtp.sendmail(from_addr, to_addr, fwd.as_string())


def mark_as_seen(imap, msg_id):
    imap.store(msg_id, "+FLAGS", "\\Seen")


def main():
    with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as imap:
        imap.login(ZOHO_USER, ZOHO_APP_PASSWORD)
        messages = fetch_unseen_messages(imap)

        if not messages:
            print("No new messages.")
            return

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(ZOHO_USER, ZOHO_APP_PASSWORD)

            for msg_id, msg in messages:
                subject = msg.get("Subject", "(no subject)")
                print(f"Forwarding: {subject}")
                forward_message(smtp, msg, ZOHO_USER, FORWARD_TO)
                mark_as_seen(imap, msg_id)

        print(f"Forwarded {len(messages)} message(s) to {FORWARD_TO}.")


if __name__ == "__main__":
    main()
