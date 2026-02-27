import imaplib
import email as email_lib
import smtplib
import os
from email.mime.text import MIMEText
from email.header import decode_header
from html.parser import HTMLParser

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from openai import OpenAI

from .models import IncomingEmail, CompanyInfo

# ----------------------------
# ENV CONFIG
# ----------------------------
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
IMAP_SERVER = os.getenv("IMAP_SERVER")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self):
        return "".join(self._parts)


def _strip_html(html):
    s = _HTMLStripper()
    s.feed(html)
    return s.get_text()


def get_system_prompt():
    info = CompanyInfo.objects.first()
    if info:
        return _strip_html(info.content)
    return "Sən professional email köməkçisisən."


# ----------------------------
# AI HELPERS
# ----------------------------
def classify_email(email_body):
    prompt = f"""
                Bu emaili aşağıdakı departamentlərdən birinə böl:
                1. Sales
                2. Support
                3. Accounting
                4. HR
                5. Agriculture

                Sadəcə department adını qaytar. Başqa heç bir cümlə ilə cavab vermə. Sadəcə departament adlarını ver. Tapa bilməsən Support ilə əvəzlə

                Email:
                {email_body}
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": prompt},
        ],
        max_tokens=50,
        temperature=0,
    )
    result = response.choices[0].message.content.strip()
    valid_departments = ['Sales', 'Support', 'Accounting', 'HR', 'Agriculture']
    for dept in valid_departments:
        if dept.lower() in result.lower():
            return dept
    return 'Support'


def generate_reply(email_body, sender_email):
    prompt = f"""
                Bu emailə cavab yaz.
                Göndərənin emaili: {sender_email}
                Göndərənə "Hörmətli {sender_email}" deyə müraciət et.
                İstifadəçinin mesajının dilini müəyyən et. Həmişə istifadəçi hansı dildə yazıbsa, eyni dildə cavab ver.

                Email:
                {email_body}
            """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": prompt},
        ],
        max_tokens=500,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg["Subject"] = "Re: " + subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)


# ----------------------------
# VIEWS
# ----------------------------

def email_list(request):
    emails = IncomingEmail.objects.all()
    return render(request, "inbox/email_list.html", {"emails": emails})


def email_detail(request, pk):
    email_obj = get_object_or_404(IncomingEmail, pk=pk)
    return render(request, "inbox/email_detail.html", {"email": email_obj})


def fetch_emails(request):
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        mail.select("inbox")

#         status, message_nums = mail.search(None, "(UNSEEN)")
#         status, message_nums = mail.search(None, '(UNSEEN FROM "efqanesc@gmail.com")')
        status, message_nums = mail.search(
            None,
#             '(UNSEEN SINCE 26-Feb-2026 FROM "efqanesc@gmail.com")'
            '(UNSEEN SINCE 26-Feb-2026)'
        )
        nums = message_nums[0].split()
        count = 0
        for num in nums:
            status, data = mail.fetch(num, "(RFC822)")
            msg = email_lib.message_from_bytes(data[0][1])
            raw_subject = msg["subject"] or "(No subject)"
            decoded_parts = decode_header(raw_subject)
            subject = "".join(
                part.decode(enc or "utf-8") if isinstance(part, bytes) else part
                for part, enc in decoded_parts
            )
            sender = email_lib.utils.parseaddr(msg["from"])[1]

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            # AI Classification
            department = classify_email(body)
            IncomingEmail.objects.create(
                sender=sender,
                subject=subject,
                body=body,
                department=department,
            )
            mail.store(num, "+FLAGS", "\\Seen")
            count += 1
        mail.logout()
        messages.success(request, f"{count} yeni email gətirildi.")
    except Exception as e:
        messages.error(request, f"Xəta: {e}")

    return redirect("email_list")


def reply_email(request, pk):
    email_obj = get_object_or_404(IncomingEmail, pk=pk)

    if request.method == "POST":
        try:
            reply_text = generate_reply(email_obj.body, email_obj.sender)
            send_email(email_obj.sender, email_obj.subject, reply_text)

            email_obj.reply_text = reply_text
            email_obj.is_replied = True
            email_obj.save()

            messages.success(request, "Cavab göndərildi!")
        except Exception as e:
            messages.error(request, f"Xəta: {e}")

    return redirect("email_detail", pk=pk)
