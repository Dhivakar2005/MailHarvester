import base64
import email
import os
from datetime import datetime
from email.message import EmailMessage
from typing import Dict, List, Optional

import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gemini
import google.generativeai as genai
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load .env for GEMINI_API_KEY
load_dotenv()

# --- Settings ---
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]

st.set_page_config(page_title="📧 Gmail + Gemini Assistant", page_icon="📨", layout="wide")
st.title("📨 Gmail + Gemini Assistant")
st.caption("Browse your Gmail or compose new emails with the help of Gemini AI.")

# --- Gemini Setup ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- Utils ---
def parse_date(date_str: str) -> datetime:
    try:
        dt_tuple = email.utils.parsedate_tz(date_str)
        if dt_tuple:
            return datetime.fromtimestamp(email.utils.mktime_tz(dt_tuple))
    except Exception:
        pass
    return datetime.min

def _find_header(headers: List[Dict], name: str) -> Optional[str]:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value")
    return None

def _decode_payload(part) -> str:
    data = part.get("body", {}).get("data")
    if not data:
        return ""
    decoded_bytes = base64.urlsafe_b64decode(data.encode("utf-8"))
    return decoded_bytes.decode(errors="ignore")

def extract_clean_email_text(detail: Dict) -> str:
    if detail.get("text"):
        return detail["text"]
    if detail.get("html"):
        soup = BeautifulSoup(detail["html"], "html.parser")
        return soup.get_text(separator="\n")
    return detail.get("snippet", "")

def generate_auto_reply(detail: Dict) -> str:
    if not GEMINI_API_KEY:
        return "(Gemini API key missing. Set GEMINI_API_KEY in .env)"
    email_text = extract_clean_email_text(detail)
    if not email_text.strip():
        return "(No content to generate reply from.)"
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""
        You are a professional email assistant.
        Read the email below and write a polite, clear, and concise reply.

        Email content:
        {email_text}
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"(Gemini error: {e})"

# --- Gmail Auth ---
def get_credentials() -> Optional[Credentials]:
    token_path = "token.json"
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            cred_path = "credentials.json"
            if not os.path.exists(cred_path):
                st.error("Missing credentials.json. Upload it in the sidebar.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
            try:
                creds = flow.run_local_server(port=8080)
            except Exception:
                creds = flow.run_console()
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    return creds

def gmail_service():
    creds = get_credentials()
    if not creds:
        return None
    try:
        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        st.error(f"Failed to build Gmail service: {e}")
        return None

def list_messages(service, query: str, max_results: int = 25) -> List[Dict]:
    res = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    return res.get("messages", [])

def get_message_detail(service, msg_id: str) -> Dict:
    raw = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    payload = raw.get("payload", {})
    headers = payload.get("headers", [])
    parts = payload.get("parts")
    body_text, body_html = "", ""

    if parts:
        for p in parts:
            mime = p.get("mimeType", "")
            if mime == "text/plain":
                body_text += _decode_payload(p)
            elif mime == "text/html":
                body_html += _decode_payload(p)
            elif p.get("parts"):
                for sp in p["parts"]:
                    mime2 = sp.get("mimeType", "")
                    if mime2 == "text/plain":
                        body_text += _decode_payload(sp)
                    elif mime2 == "text/html":
                        body_html += _decode_payload(sp)
    else:
        mime = payload.get("mimeType", "")
        if mime == "text/plain":
            body_text = _decode_payload(payload)
        elif mime == "text/html":
            body_html = _decode_payload(payload)

    return {
        "id": raw["id"],
        "threadId": raw.get("threadId"),
        "snippet": raw.get("snippet", ""),
        "labelIds": raw.get("labelIds", []),
        "From": _find_header(headers, "From"),
        "To": _find_header(headers, "To"),
        "Subject": _find_header(headers, "Subject"),
        "Date": _find_header(headers, "Date"),
        "Message-Id": _find_header(headers, "Message-Id"),
        "In-Reply-To": _find_header(headers, "In-Reply-To"),
        "References": _find_header(headers, "References"),
        "text": body_text.strip(),
        "html": body_html.strip(),
    }

def reply_message(service, original: Dict, reply_text: str) -> Dict:
    reply = EmailMessage()
    orig_from = email.utils.parseaddr(original.get("From", ""))[1]
    if not orig_from:
        raise ValueError("Couldn't parse the original sender address.")
    subject = original.get("Subject") or ""
    reply["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    reply["To"] = orig_from
    reply["From"] = "me"
    if original.get("Message-Id"):
        reply["In-Reply-To"] = original["Message-Id"]
        if original.get("References"):
            reply["References"] = f'{original["References"]} {original["Message-Id"]}'
        else:
            reply["References"] = original["Message-Id"]
    reply.set_content(reply_text)
    raw = base64.urlsafe_b64encode(reply.as_bytes()).decode()
    body = {"raw": raw, "threadId": original.get("threadId")}
    return service.users().messages().send(userId="me", body=body).execute()

# --- Sidebar: Credentials + Tab Switch ---
st.sidebar.header("Setup")
st.sidebar.write("Upload your **credentials.json** here.")
cred_file = st.sidebar.file_uploader("credentials.json", type=["json"])
if cred_file:
    with open("credentials.json", "wb") as f:
        f.write(cred_file.read())
    st.sidebar.success("credentials.json saved.")

if st.sidebar.button("Reset token (log out)"):
    if os.path.exists("token.json"):
        os.remove("token.json")
        st.sidebar.success("token.json removed")

# --- Sidebar Tab Selection ---
tab_choice = st.sidebar.radio("Go to:", ["📥 Search Emails", "✉️ Compose New Email"])

# --- Initialize Gmail service ---
service = gmail_service()
if not service:
    st.stop()

# --- Compose New Email ---
if tab_choice == "✉️ Compose New Email":
    st.header("Compose New Email")
    to = st.text_input("To", value=st.session_state.get("new_email_to", ""), key="new_email_to")
    subject = st.text_input("Subject", value=st.session_state.get("new_email_subject", ""), key="new_email_subject")
    body = st.text_area("Body", value=st.session_state.get("new_email_body", ""), height=300, key="new_email_body")
    send_cols = st.columns([1, 1])
    with send_cols[0]:
        if st.button("📤 Send Email", key="send_new_email"):
            try:
                new_mail = EmailMessage()
                new_mail["To"] = to
                new_mail["Subject"] = subject
                new_mail["From"] = "me"
                new_mail.set_content(body)
                raw = base64.urlsafe_b64encode(new_mail.as_bytes()).decode()
                service.users().messages().send(userId="me", body={"raw": raw}).execute()
                st.success("New email sent ✅")
                for k in ["new_email_to", "new_email_subject", "new_email_body"]:
                    st.session_state[k] = ""
            except Exception as e:
                st.error(f"Failed to send new email: {e}")
    with send_cols[1]:
        if st.button("❌ Clear", key="clear_new_email"):
            for k in ["new_email_to", "new_email_subject", "new_email_body"]:
                st.session_state[k] = ""

# --- Search Emails ---
if tab_choice == "📥 Search Emails":
    st.header("Search Gmail")
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Search query (e.g., is:unread newer_than:7d)", value="")
    with col2:
        max_results = st.number_input("Max results", min_value=1, max_value=50, value=10, step=1)

    if "messages_cache" not in st.session_state:
        st.session_state.messages_cache = []

    if st.button("📥 Fetch messages"):
        try:
            st.session_state.messages_cache = list_messages(service, query, int(max_results))
            st.success(f"Fetched {len(st.session_state.messages_cache)} message(s).")
        except HttpError as e:
            st.error(f"Gmail API error: {e}")

    msgs = st.session_state.messages_cache
    if msgs:
        details = []
        for m in msgs:
            try:
                details.append(get_message_detail(service, m["id"]))
            except Exception as e:
                st.warning(f"Failed to load message {m['id']}: {e}")

        details.sort(key=lambda d: parse_date(d.get("Date", "")), reverse=True)

        for detail in details:
            mail_date = parse_date(detail.get("Date", "")).strftime("%Y-%m-%d %H:%M")
            with st.expander(f"📩 {detail.get('Subject', '(no subject)')} — {detail.get('From', '')} [{mail_date}]"):
                st.markdown(f"**From:** {detail.get('From', '')}  ")
                st.markdown(f"**To:** {detail.get('To', '')}  ")
                st.markdown(f"**Date:** {detail.get('Date', '')}  ")

                email_tabs = st.tabs(["📝 Snippet", "📃 Text body", "🌐 HTML preview", "🤖 Gemini Reply"])
                with email_tabs[0]:
                    st.code(detail.get("snippet") or "")
                with email_tabs[1]:
                    st.code(detail.get("text") or "(no text/plain part)")
                with email_tabs[2]:
                    if detail.get("html"):
                        st.components.v1.html(detail["html"], height=400, scrolling=True)
                    else:
                        st.info("No HTML content.")
                with email_tabs[3]:
                    if f"gemini_reply_{detail['id']}" not in st.session_state:
                        with st.spinner("Gemini is generating a reply..."):
                            st.session_state[f"gemini_reply_{detail['id']}"] = generate_auto_reply(detail)

                    st.text_area("Reply draft", value=st.session_state[f"gemini_reply_{detail['id']}"], height=180, key=f"reply_{detail['id']}")

                    send_cols = st.columns([1, 1])
                    with send_cols[0]:
                        if st.button("📤 Send reply", key=f"send_{detail['id']}"):
                            try:
                                result = reply_message(service, detail, st.session_state[f"reply_{detail['id']}"])
                                service.users().messages().modify(
                                    userId="me", id=detail["id"], body={"removeLabelIds": ["UNREAD"]}
                                ).execute()
                                st.success(f"Reply sent ✅ (Message ID: {result.get('id')})")
                            except Exception as e:
                                st.error(f"Failed to send reply: {e}")
    else:
        st.info("Click **Fetch messages** to list your Gmail messages.")
