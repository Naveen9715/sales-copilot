
import os
import re
import json
import base64
import requests
from datetime import datetime, timedelta, timezone

from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# ============================================================
# CONFIGURATION
# ============================================================

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2:3b"

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"
MEMORY_FILE = "memory.json"
STATE_FILE = "agent_state.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
]
INDIA_TIMEZONE = timezone(timedelta(hours=5, minutes=30))
CALENDAR_TIMEZONE_NAME = "Asia/Kolkata"

PRODUCT_KNOWLEDGE = """
Our product is an AI Automation Platform.

It helps businesses with:
- Customer support automation
- Lead generation
- Email automation
- Appointment scheduling
- Reducing repetitive manual work
"""

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)


# ============================================================
# JSON STORAGE
# ============================================================

def load_json(filename, default):
    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


conversation = load_json(MEMORY_FILE, [])

state = load_json(
    STATE_FILE,
    {
        "last_recipient": None,
        "last_subject": None,
        "last_message": None,
    },
)


def save_conversation():
    save_json(MEMORY_FILE, conversation)


def save_state():
    save_json(STATE_FILE, state)


def remember(role, content):
    conversation.append(
        {
            "role": role,
            "content": content,
        }
    )

    # Keep the most recent messages to limit prompt size.
    while len(conversation) > 20:
        conversation.pop(0)

    save_conversation()


def conversation_context():
    if not conversation:
        return "No previous conversation."

    recent = conversation[-10:]

    return "\n".join(
        f"{item['role'].upper()}: {item['content']}"
        for item in recent
    )


# ============================================================
# OLLAMA / LOCAL AI
# ============================================================

def ask_ollama(messages, temperature=0.2):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=180,
        )
        response.raise_for_status()

        data = response.json()
        answer = data.get("message", {}).get("content", "")

        if not answer.strip():
            raise RuntimeError("Ollama returned an empty response.")

        return answer.strip()

    except requests.exceptions.ConnectionError as error:
        raise RuntimeError(
            "Cannot connect to Ollama. Open another PowerShell window "
            "and run: ollama serve"
        ) from error

    except requests.exceptions.Timeout as error:
        raise RuntimeError(
            "Ollama took too long to respond. Please try again."
        ) from error

    except requests.exceptions.RequestException as error:
        raise RuntimeError(f"Ollama request failed: {error}") from error


# ============================================================
# PRODUCT QUESTION ANSWERING
# ============================================================

def answer_product_question(user_request):
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful sales assistant for a business product.\n\n"
                "Use ONLY the product information supplied below to answer "
                "questions about the product.\n"
                "Do not invent prices, guarantees, customer results, "
                "integrations, certifications, or features.\n"
                "If the requested information is unavailable, say that "
                "you do not have that information.\n"
                "Answer clearly and professionally.\n\n"
                f"PRODUCT INFORMATION:\n{PRODUCT_KNOWLEDGE}"
            ),
        },
        {
            "role": "user",
            "content": user_request,
        },
    ]

    return ask_ollama(messages)




# ============================================================
# CALCULATOR TOOL
# ============================================================

def calculate_total(quantity, unit_price):
    """
    Calculate quantity * unit price after validating the inputs.

    Quantity must be greater than zero.
    Unit price must be zero or greater.
    """
    try:
        quantity = float(quantity)
        unit_price = float(unit_price)
    except (TypeError, ValueError):
        raise ValueError("Quantity and unit price must be valid numbers.")

    if not (quantity == quantity and abs(quantity) != float("inf")):
        raise ValueError("Quantity must be a finite number.")
    if not (unit_price == unit_price and abs(unit_price) != float("inf")):
        raise ValueError("Unit price must be a finite number.")

    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0.")
    if unit_price < 0:
        raise ValueError("Unit price cannot be negative.")

    return quantity * unit_price


def handle_calculation_request(user_request):
    """
    Handle common calculator request formats, for example:
    - calculate 5 x 200
    - calculate 5 items at 200 each
    - calculate quantity 5 price 200
    - calculate -5 x 200 (rejected by validation)
    """
    text = user_request.lower().replace(",", "").strip()

    # Explicit quantity/price labels.
    labeled_match = re.search(
        r"\bquantity\s*[:=]?\s*(-?\d+(?:\.\d+)?)"
        r".{0,40}?\b(?:unit\s*)?price\s*[:=]?\s*(-?\d+(?:\.\d+)?)\b",
        text,
    )

    # Natural language: "5 items at 200 each".
    items_match = re.search(
        r"(?<!\w)(-?\d+(?:\.\d+)?)\s+(?:items?|units?|products?)\s+"
        r"(?:at|for|cost(?:ing)?)\s+\$?\s*(-?\d+(?:\.\d+)?)"
        r"(?:\s+each)?\b",
        text,
    )

    # Arithmetic-style request: "calculate 5 x 200" or "5 * 200".
    multiplication_match = re.search(
        r"(?<!\w)(?:calculate|total|multiply|what\s+is|how\s+much\s+is)?\s*"
        r"(-?\d+(?:\.\d+)?)\s*(?:x|\*|×|times)\s*"
        r"\$?\s*(-?\d+(?:\.\d+)?)\b",
        text,
    )

    # Only take over the request if it looks like a calculation.
    looks_calculation_related = any(
        word in text
        for word in ("calculate", "calculation", "total", "quantity", "unit price")
    ) or bool(re.search(r"\b(?:items?|units?|products?)\b", text)) \
      or bool(re.search(r"\d\s*(?:x|\*|×|times)\s*-?\d", text))

    if not looks_calculation_related:
        return False

    match = labeled_match or items_match or multiplication_match
    if not match:
        print(
            "\nSales Agent: I couldn't read that calculation. "
            "Try 'calculate 5 x 200' or 'calculate quantity 5 price 200'."
        )
        return True

    quantity, unit_price = match.groups()

    try:
        total = calculate_total(quantity, unit_price)
    except ValueError as error:
        print(f"\nSales Agent: Invalid calculation: {error}")
        return True

    if total.is_integer():
        total_text = str(int(total))
    else:
        total_text = f"{total:.2f}".rstrip("0").rstrip(".")

    print(f"\nSales Agent: Total = {total_text}")
    remember("assistant", f"Calculated total: {quantity} × {unit_price} = {total_text}")
    return True


# ============================================================
# EMAIL UTILITIES
# ============================================================

def extract_email(text):
    match = EMAIL_PATTERN.search(text or "")
    return match.group(0) if match else None


def is_valid_email(address):
    if not isinstance(address, str):
        return False

    return EMAIL_PATTERN.fullmatch(address.strip()) is not None


def is_email_followup(text):
    text = text.lower().strip()

    phrases = [
        "that email",
        "this email",
        "the email",
        "make it shorter",
        "make that shorter",
        "make it professional",
        "more professional",
        "shorter and more professional",
        "rewrite it",
        "rewrite the email",
        "edit the email",
        "change the email",
        "improve the email",
        "change the subject",
        "make it concise",
        "make it formal",
        "make it simpler",
        "make it polite",
        "use a professional tone",
        "send it",
        "send that",
        "send the email",
    ]

    return any(phrase in text for phrase in phrases)


def looks_like_email_request(text):
    text_lower = text.lower()

    # An explicit address strongly indicates an email task.
    if extract_email(text):
        return True

    email_action_words = [
        "send an email",
        "send email",
        "send that information",
        "send this information",
        "email this",
        "email that",
        "write an email",
        "draft an email",
        "compose an email",
        "create an email",
        "prepare an email",
        "write a mail",
        "send a mail",
        "draft a mail",
    ]

    if any(phrase in text_lower for phrase in email_action_words):
        return True

    # Follow-ups are treated as email tasks when we have a draft.
    has_previous_draft = bool(
        state.get("last_subject") and state.get("last_message")
    )

    if has_previous_draft and is_email_followup(text):
        return True

    return False


# ============================================================
# EMAIL DRAFT GENERATION AND PARSING
# ============================================================

def parse_email_draft(result):
    """
    Parse the model's SUBJECT and MESSAGE sections.

    The message may contain multiple paragraphs and blank lines.
    Everything after MESSAGE: is treated as the email body.
    """

    subject_match = re.search(
        r"(?im)^[ \t]*\**SUBJECT:\**[ \t]*(.+?)[ \t]*$",
        result,
    )

    message_match = re.search(
        r"(?ims)^[ \t]*\**MESSAGE:\**[ \t]*(.*)$",
        result,
    )

    if not subject_match or not message_match:
        return None, None

    subject = subject_match.group(1).strip()
    message = message_match.group(1).strip()

    # Remove an accidental code fence around the body.
    message = re.sub(r"^\s*```(?:text)?\s*", "", message)
    message = re.sub(r"\s*```\s*$", "", message).strip()

    if not subject or not message:
        return None, None

    # Do not send a body that is only a placeholder.
    if message.lower() in {
        "[your message]",
        "[email body]",
        "your message here",
    }:
        return None, None

    return subject, message


def generate_email_draft(user_request, old_subject=None, old_message=None):
    context = conversation_context()

    if old_subject and old_message:
        task_instruction = f"""
The user wants to edit an existing email.

EXISTING SUBJECT:
{old_subject}

EXISTING EMAIL BODY:
{old_message}

EDIT REQUEST:
{user_request}

Edit the existing email according to the user's request.
Keep the original meaning and relevant facts.
Do not add unsupported product claims or invented details.
Preserve useful information unless the user asks to remove it.
"""
    else:
        task_instruction = f"""
Create a professional email based on the user's request.

USER REQUEST:
{user_request}

Use the product information and conversation history when relevant.
If the user asks to send previously discussed product information,
include the relevant supported features concisely.
Do not invent prices, results, guarantees, customer names, integrations,
or product features.
Do not promise a demo or meeting unless the user requests it.
Do not include placeholders such as [Your Name].
Keep the email reasonably concise.
"""

    prompt = f"""
You are a professional business email writer.

PRODUCT INFORMATION:
{PRODUCT_KNOWLEDGE}

RECENT CONVERSATION:
{context}

{task_instruction}

Return ONLY this format:

SUBJECT: A short, relevant subject

MESSAGE:
The complete email body goes here.

Important:
- Use exactly one SUBJECT: line.
- Use exactly one MESSAGE: line.
- Put the entire email body after MESSAGE:.
- The email body may contain multiple paragraphs.
- Do not add explanations before or after the email.
- Do not use Markdown code fences.
"""

    result = ask_ollama(
        [
            {
                "role": "user",
                "content": prompt,
            }
        ]
    )

    subject, message = parse_email_draft(result)

    if not subject or not message:
        print("\nCould not parse the email draft.")
        print("Raw response from the model:\n")
        print(result)
        return None, None

    # Save the latest draft so later requests can edit it.
    state["last_subject"] = subject
    state["last_message"] = message
    save_state()

    return subject, message


# ============================================================
# GMAIL AUTHENTICATION
# ============================================================

def get_gmail_service():
    credentials = None

    if os.path.exists(TOKEN_FILE):
        try:
            credentials = Credentials.from_authorized_user_file(
                TOKEN_FILE,
                SCOPES,
            )
        except (ValueError, OSError):
            credentials = None

    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except Exception as error:
            raise RuntimeError(
                "Could not refresh Gmail authorization. If the saved token "
                "has the wrong permissions, delete token.json and run the "
                "program again to authorize Gmail."
            ) from error

    if not credentials or not credentials.valid:
        if not os.path.exists(CREDENTIALS_FILE):
            raise FileNotFoundError(
                f"{CREDENTIALS_FILE} was not found. Put your Google OAuth "
                "credentials JSON file in the project folder."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE,
            SCOPES,
        )

        credentials = flow.run_local_server(port=0)

    with open(TOKEN_FILE, "w", encoding="utf-8") as token_file:
        token_file.write(credentials.to_json())

    return build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )


# ============================================================
# GOOGLE CALENDAR AUTHENTICATION AND APPOINTMENT BOOKING
# ============================================================

def get_calendar_service():
    """Return an authenticated Google Calendar API service."""
    credentials = None

    if os.path.exists(TOKEN_FILE):
        try:
            credentials = Credentials.from_authorized_user_file(
                TOKEN_FILE,
                SCOPES,
            )
        except (ValueError, OSError):
            credentials = None

    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except Exception as error:
            raise RuntimeError(
                "Google authorization could not be refreshed. Run "
                "calendar_auth_test.py again to authorize Gmail and Calendar "
                "with the combined scopes, then restart this app."
            ) from error

    if not credentials or not credentials.valid:
        if not os.path.exists(CREDENTIALS_FILE):
            raise FileNotFoundError(
                f"{CREDENTIALS_FILE} was not found in the project folder."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE,
            SCOPES,
        )
        credentials = flow.run_local_server(port=0)

    with open(TOKEN_FILE, "w", encoding="utf-8") as token_file:
        token_file.write(credentials.to_json())

    return build(
        "calendar",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )


def looks_like_calendar_request(text):
    """Detect explicit requests to create a Calendar appointment."""
    lower = text.lower()
    phrases = (
        "schedule a meeting", "schedule meeting", "book a meeting",
        "create a calendar event", "add to my calendar", "add it to calendar",
        "schedule an appointment", "book an appointment", "schedule appointment",
        "create an appointment", "put it on my calendar", "book a call",
        "schedule a call", "schedule a demo", "book a demo",
    )
    return any(phrase in lower for phrase in phrases)


def parse_calendar_datetime(date_text, time_text):
    """Parse local India date/time and return an aware datetime."""
    date_value = datetime.strptime(date_text.strip(), "%Y-%m-%d").date()
    time_value = datetime.strptime(time_text.strip(), "%H:%M").time()
    return datetime.combine(date_value, time_value).replace(tzinfo=INDIA_TIMEZONE)


def calendar_datetime_text(value):
    return value.isoformat(timespec="seconds")


def check_calendar_conflicts(service, start, end):
    """Return events that overlap the proposed time window."""
    result = service.events().list(
        calendarId="primary",
        timeMin=calendar_datetime_text(start),
        timeMax=calendar_datetime_text(end),
        singleEvents=True,
        orderBy="startTime",
        maxResults=50,
    ).execute()

    conflicts = []
    for event in result.get("items", []):
        event_start = event.get("start", {}).get("dateTime")
        event_end = event.get("end", {}).get("dateTime")

        # All-day events use date instead of dateTime; treat them as busy.
        if not event_start or not event_end:
            event_date = event.get("start", {}).get("date")
            if event_date:
                conflicts.append(event)
            continue

        try:
            parsed_start = datetime.fromisoformat(event_start.replace("Z", "+00:00"))
            parsed_end = datetime.fromisoformat(event_end.replace("Z", "+00:00"))
            if parsed_start < end and parsed_end > start:
                conflicts.append(event)
        except ValueError:
            # If an event's time format cannot be interpreted, fail safely.
            conflicts.append(event)

    return conflicts


def create_calendar_appointment():
    """Collect details, check conflicts, preview, and require confirmation."""
    print("\nSales Agent: Let's schedule a Google Calendar appointment.")
    title = input("Meeting title: ").strip()
    if not title:
        print("\nSales Agent: Meeting title cannot be empty. Booking cancelled.")
        return

    date_text = input("Date (YYYY-MM-DD, India time): ").strip()
    time_text = input("Start time (24-hour HH:MM, e.g. 15:30): ").strip()
    duration_text = input("Duration in minutes (default 30): ").strip() or "30"
    attendee = input("Attendee email (optional; press Enter to skip): ").strip()
    description = input("Description (optional; press Enter to skip): ").strip()

    if attendee and not is_valid_email(attendee):
        print("\nSales Agent: That attendee email address is invalid. Booking cancelled.")
        return

    try:
        start = parse_calendar_datetime(date_text, time_text)
        duration = int(duration_text)
        if duration < 5 or duration > 480:
            raise ValueError("Duration must be between 5 and 480 minutes.")
        end = start + timedelta(minutes=duration)
    except ValueError as error:
        print(f"\nSales Agent: Invalid date, time, or duration: {error}")
        print("Use date YYYY-MM-DD, time HH:MM (24-hour), and a whole-number duration.")
        return

    if start <= datetime.now(INDIA_TIMEZONE):
        print("\nSales Agent: The meeting start time must be in the future. Booking cancelled.")
        return

    try:
        service = get_calendar_service()
        conflicts = check_calendar_conflicts(service, start, end)
    except HttpError as error:
        print(f"\nSales Agent: Google Calendar API error while checking availability: {error}")
        return
    except Exception as error:
        print(f"\nSales Agent: Could not check Calendar availability: {error}")
        return

    if conflicts:
        print("\nSales Agent: I found an existing event during that time. No booking was created.")
        for event in conflicts[:5]:
            event_title = event.get("summary", "(Untitled event)")
            event_start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date", "time unavailable")
            print(f"- {event_title} — {event_start}")
        print("Please try a different time.")
        return

    event = {
        "summary": title,
        "description": description,
        "start": {
            "dateTime": start.isoformat(),
            "timeZone": CALENDAR_TIMEZONE_NAME,
        },
        "end": {
            "dateTime": end.isoformat(),
            "timeZone": CALENDAR_TIMEZONE_NAME,
        },
    }
    if attendee:
        event["attendees"] = [{"email": attendee}]

    print("\n" + "=" * 55)
    print("CALENDAR EVENT PREVIEW")
    print("=" * 55)
    print(f"Title: {title}")
    print(f"Start: {start.strftime('%Y-%m-%d %H:%M')} (Asia/Kolkata)")
    print(f"End:   {end.strftime('%Y-%m-%d %H:%M')} (Asia/Kolkata)")
    print(f"Attendee: {attendee or 'No attendee added'}")
    print(f"Description: {description or '(none)'}")
    print("=" * 55)
    confirmation = input("Create this event? Type 'yes' to confirm or 'no' to cancel: ").strip().lower()
    if confirmation not in {"yes", "y"}:
        print("\nSales Agent: Booking cancelled. No event was created.")
        return

    try:
        result = service.events().insert(
            calendarId="primary",
            body=event,
            sendUpdates="all" if attendee else "none",
        ).execute()
        print("\nSales Agent: Calendar appointment created successfully!")
        print(f"Event: {result.get('summary', title)}")
        print(f"Event link: {result.get('htmlLink', 'Not available')}")
        remember("assistant", f"Created Calendar event: {title} at {start.isoformat()}")
    except HttpError as error:
        print(f"\nSales Agent: Google Calendar API error while creating event: {error}")
    except Exception as error:
        print(f"\nSales Agent: Could not create the Calendar event: {error}")


# ============================================================
# SEND EMAIL USING GMAIL API
# ============================================================

def send_email(recipient, subject, message):
    if not is_valid_email(recipient):
        print("\nInvalid recipient email address.")
        return False

    if not subject.strip() or not message.strip():
        print("\nThe email subject and message cannot be empty.")
        return False

    try:
        service = get_gmail_service()

        mime_message = MIMEText(message, "plain", "utf-8")
        mime_message["to"] = recipient
        mime_message["subject"] = subject

        encoded_message = base64.urlsafe_b64encode(
            mime_message.as_bytes()
        ).decode("utf-8")

        body = {
            "raw": encoded_message,
        }

        result = (
            service.users()
            .messages()
            .send(userId="me", body=body)
            .execute()
        )

        print("\nEmail sent successfully!")
        print(f"To: {recipient}")
        print(f"Subject: {subject}")
        print(f"Gmail message ID: {result.get('id', 'Unavailable')}")

        return True

    except HttpError as error:
        print(f"\nGmail API error: {error}")
        return False

    except Exception as error:
        print(f"\nCould not send the email: {error}")
        return False


# ============================================================
# EMAIL PREVIEW AND CONFIRMATION
# ============================================================

def display_email_preview(recipient, subject, message):
    print("\n" + "=" * 55)
    print("EMAIL PREVIEW")
    print("=" * 55)
    print(f"To: {recipient}")
    print(f"Subject: {subject}")
    print("-" * 55)
    print(message)
    print("=" * 55)


def confirm_or_edit_email(recipient, subject, message):
    """
    The user can confirm, cancel, or enter an edit request.
    Every edited version is previewed before sending.
    """

    while True:
        display_email_preview(recipient, subject, message)

        print(
            "\nEnter 'yes' to send, 'no' to cancel, "
            "or type an edit request."
        )

        choice = input("\nYou: ").strip()
        choice_lower = choice.lower()

        if choice_lower in {"yes", "y", "send", "confirm"}:
            success = send_email(recipient, subject, message)

            if success:
                state["last_recipient"] = recipient
                state["last_subject"] = subject
                state["last_message"] = message
                save_state()

                remember(
                    "assistant",
                    f"Email sent to {recipient}. Subject: {subject}",
                )

            else:
                print(
                    "\nThe email was not confirmed as sent. "
                    "Please check the error above before retrying."
                )

            return

        if choice_lower in {"no", "n", "cancel", "stop"}:
            print("\nEmail cancelled. Nothing was sent.")
            return

        # Treat any other response as an editing instruction.
        remember("user", f"Email edit request: {choice}")

        new_subject, new_message = generate_email_draft(
            choice,
            old_subject=subject,
            old_message=message,
        )

        if not new_subject or not new_message:
            print(
                "\nI couldn't generate the edited email. "
                "The previous draft has not been sent."
            )
            continue

        subject = new_subject
        message = new_message

        state["last_recipient"] = recipient
        state["last_subject"] = subject
        state["last_message"] = message
        save_state()


# ============================================================
# EMAIL REQUEST HANDLER
# ============================================================

def handle_email_request(user_request):
    recipient = extract_email(user_request)

    if recipient:
        # Remember a new recipient for future email follow-ups.
        state["last_recipient"] = recipient
        save_state()
    else:
        recipient = state.get("last_recipient")

    if not recipient or not is_valid_email(recipient):
        print(
            "\nSales Agent: Please provide the recipient's complete "
            "email address."
        )
        return

    user_request_lower = user_request.lower().strip()

    # If the user explicitly asks to send the last draft, reuse it.
    send_existing_phrases = {
        "send it",
        "send that",
        "send the email",
        "send that email",
        "send this email",
    }

    has_existing_draft = bool(
        state.get("last_subject") and state.get("last_message")
    )

    if (
        has_existing_draft
        and user_request_lower in send_existing_phrases
    ):
        confirm_or_edit_email(
            recipient,
            state["last_subject"],
            state["last_message"],
        )
        return

    # Edit the previous draft when the user gives a follow-up instruction.
    if has_existing_draft and is_email_followup(user_request):
        subject, message = generate_email_draft(
            user_request,
            old_subject=state["last_subject"],
            old_message=state["last_message"],
        )
    else:
        subject, message = generate_email_draft(user_request)

    if not subject or not message:
        print(
            "\nSales Agent: I couldn't generate a complete email. "
            "Please try again with a clearer instruction."
        )
        return

    state["last_recipient"] = recipient
    state["last_subject"] = subject
    state["last_message"] = message
    save_state()

    # Never send without displaying a preview and asking for confirmation.
    confirm_or_edit_email(recipient, subject, message)


# ============================================================
# COMMAND ROUTER
# ============================================================

def process_request(user_request):
    text = user_request.strip()

    if not text:
        return

    if text.lower() == "clear memory":
        conversation.clear()
        save_conversation()

        # Keep the saved recipient, but clear the previous draft.
        state["last_subject"] = None
        state["last_message"] = None
        save_state()

        print(
            "\nSales Agent: Conversation memory and the previous draft "
            "have been cleared. The last recipient is still saved."
        )
        return

    if text.lower() == "memory":
        print("\nConversation Memory:")

        if not conversation:
            print("No conversation history.")
        else:
            for item in conversation:
                print(f"{item['role'].upper()}: {item['content']}")

        return

    remember("user", text)

    try:
        # Calendar creation is an explicit, interactive action with confirmation.
        if looks_like_calendar_request(text):
            create_calendar_appointment()
            return

        # Handle calculations with deterministic Python logic rather than the LLM.
        if handle_calculation_request(text):
            return

        if looks_like_email_request(text):
            handle_email_request(text)

        else:
            answer = answer_product_question(text)
            print(f"\nSales Agent: {answer}")
            remember("assistant", answer)

    except RuntimeError as error:
        print(f"\nSales Agent: {error}")

    except Exception as error:
        print(f"\nSales Agent: An unexpected error occurred: {error}")


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():
    print("=" * 55)
    print("AI SALES COPILOT")
    print("=" * 55)
    print(f"Local model: {OLLAMA_MODEL}")
    print("Email provider: Gmail API")
    print("Calendar provider: Google Calendar API")
    print("Payment required for OpenAI API: No")
    print("\nCommands:")
    print("- Ask questions about the product")
    print("- Request an email draft")
    print("- Edit a draft before sending")
    print("- Say 'schedule a meeting' to create a Calendar event")
    print("- Calculate totals, e.g. 'calculate 5 x 200'")
    print("- Type 'memory' to view conversation history")
    print("- Type 'clear memory' to clear conversation history")
    print("- Type 'exit' to quit")
    print("=" * 55)

    while True:
        try:
            user_request = input("\nYou: ").strip()

            if user_request.lower() in {"exit", "quit"}:
                print("\nSales Agent: Goodbye!")
                break

            process_request(user_request)

        except KeyboardInterrupt:
            print("\n\nSales Agent: Goodbye!")
            break

        except EOFError:
            print("\nSales Agent: Goodbye!")
            break


if __name__ == "__main__":
    main()
