
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
LEADS_FILE = "leads.json"

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
# SIMPLE LEAD MANAGEMENT
# ============================================================

def load_leads():
    """Load saved leads from local JSON storage."""
    data = load_json(LEADS_FILE, [])
    return data if isinstance(data, list) else []


def save_leads(leads):
    save_json(LEADS_FILE, leads)


def looks_like_lead_request(text):
    lower = text.lower().strip()
    commands = (
        "add lead", "capture lead", "save lead", "new lead",
        "list leads", "show leads", "view leads", "search leads",
        "email lead", "contact lead", "lead list",
        "follow up lead", "follow-up lead", "followup lead",
        "sales dashboard", "follow-up queue", "follow up queue", "lead dashboard",
        "sales automation", "run sales automation", "automation run",
        "update lead status", "set follow-up", "set follow up", "mark lead",
    )
    return any(lower == command or lower.startswith(command + " ") for command in commands)


def lead_priority(lead):
    """Return a transparent heuristic priority; this is not a prediction of sales."""
    notes = " ".join(str(lead.get(key, "")) for key in ("notes", "source")).lower()
    score = 0
    if is_valid_email(lead.get("email", "")):
        score += 1
    if str(lead.get("company", "")).strip():
        score += 1
    high_intent_terms = (
        "demo", "pricing", "budget", "ready to buy", "purchase", "urgent",
        "interested", "implementation", "timeline", "proposal", "meeting",
    )
    if any(term in notes for term in high_intent_terms):
        score += 2
    if any(term in notes for term in ("urgent", "ready to buy", "purchase", "budget approved")):
        score += 1
    if score >= 4:
        return "High"
    if score >= 2:
        return "Medium"
    return "Low"


def lead_status(lead):
    return lead.get("status") or "New"


def lead_due_date(lead):
    return lead.get("follow_up_due") or "Not set"


def parse_iso_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def find_lead_by_id(leads, lead_id):
    return next((item for item in leads if str(item.get("id")) == str(lead_id)), None)


def sales_dashboard():
    """Summarise pipeline and highlight follow-ups due today or overdue."""
    leads = load_leads()
    if not leads:
        print("\nSales Agent: No leads yet. Add a lead to start your sales pipeline.")
        return

    today = datetime.now(INDIA_TIMEZONE).date()
    status_counts = {}
    due = []
    high_priority = []
    for lead in leads:
        status = lead_status(lead)
        status_counts[status] = status_counts.get(status, 0) + 1
        parsed_due = parse_iso_date(lead.get("follow_up_due"))
        if parsed_due and parsed_due <= today and status.lower() not in {"won", "lost", "closed"}:
            due.append((lead, parsed_due))
        if lead_priority(lead) == "High" and status.lower() not in {"won", "lost", "closed"}:
            high_priority.append(lead)

    print("\n" + "=" * 72)
    print("AI SALES WORKFLOW COPILOT — SALES OPERATIONS DASHBOARD")
    print("=" * 72)
    print(f"Total leads: {len(leads)}")
    print("Pipeline by status: " + (", ".join(f"{k}: {v}" for k, v in sorted(status_counts.items())) or "None"))
    print(f"High-priority open leads: {len(high_priority)}")
    print(f"Follow-ups due / overdue: {len(due)}")

    if due:
        print("\nFOLLOW-UPS NEEDING ATTENTION")
        for lead, due_date in sorted(due, key=lambda pair: pair[1]):
            timing = "OVERDUE" if due_date < today else "DUE TODAY"
            print(
                f"- ID {lead.get('id')} | {lead.get('name', 'Unnamed')} | "
                f"{timing}: {due_date.isoformat()} | Priority: {lead_priority(lead)}"
            )
    else:
        print("\nNo follow-ups are due today or overdue.")

    if high_priority:
        print("\nSUGGESTED NEXT ACTIONS")
        for lead in high_priority[:5]:
            action = "Prepare a personalised email" if is_valid_email(lead.get("email", "")) else "Find/record a valid email address"
            print(f"- ID {lead.get('id')} | {lead.get('name', 'Unnamed')}: {action}")
    print("=" * 72)


def follow_up_queue():
    """List open leads due for follow-up, ordered by due date and priority."""
    today = datetime.now(INDIA_TIMEZONE).date()
    leads = []
    for lead in load_leads():
        if lead_status(lead).lower() in {"won", "lost", "closed"}:
            continue
        due = parse_iso_date(lead.get("follow_up_due"))
        if due and due <= today:
            leads.append((lead, due))

    if not leads:
        print("\nSales Agent: No due follow-ups. Use 'sales dashboard' to review your pipeline.")
        return

    leads.sort(key=lambda pair: (pair[1], {"High": 0, "Medium": 1, "Low": 2}[lead_priority(pair[0])]))
    print("\nFOLLOW-UP QUEUE — oldest due first")
    for lead, due in leads:
        timing = "OVERDUE" if due < today else "DUE TODAY"
        print(
            f"ID {lead.get('id')} | {lead.get('name')} | {lead.get('company') or 'No company'} | "
            f"{timing} {due.isoformat()} | Priority {lead_priority(lead)} | Status {lead_status(lead)}"
        )


def update_lead_status(lead_id, status):
    allowed = {"new", "contacted", "qualified", "meeting scheduled", "won", "lost", "closed"}
    cleaned = " ".join(status.strip().lower().split())
    if cleaned not in allowed:
        print("\nSales Agent: Allowed statuses: New, Contacted, Qualified, Meeting Scheduled, Won, Lost, Closed.")
        return
    leads = load_leads()
    lead = find_lead_by_id(leads, lead_id)
    if not lead:
        print(f"\nSales Agent: No lead found with ID {lead_id}.")
        return
    lead["status"] = cleaned.title()
    lead["status_updated_at"] = datetime.now(INDIA_TIMEZONE).isoformat(timespec="seconds")
    save_leads(leads)
    print(f"\nSales Agent: Updated {lead.get('name')} to status '{lead['status']}'.")


def set_lead_follow_up(lead_id, date_text):
    due = parse_iso_date(date_text)
    if not due:
        print("\nSales Agent: Use a valid date in YYYY-MM-DD format, e.g. set follow-up 2 2026-10-20.")
        return
    leads = load_leads()
    lead = find_lead_by_id(leads, lead_id)
    if not lead:
        print(f"\nSales Agent: No lead found with ID {lead_id}.")
        return
    lead["follow_up_due"] = due.isoformat()
    lead["follow_up_updated_at"] = datetime.now(INDIA_TIMEZONE).isoformat(timespec="seconds")
    save_leads(leads)
    print(f"\nSales Agent: Follow-up for {lead.get('name')} set to {due.isoformat()}.")


def add_lead():
    print("\nSales Agent: Let's save a new lead.")
    name = input("Lead name (required): ").strip()
    if not name:
        print("\nSales Agent: Name is required. Lead not saved.")
        return

    company = input("Company (optional): ").strip()
    email = input("Email (optional): ").strip()
    if email and not is_valid_email(email):
        print("\nSales Agent: That email address is invalid. Lead not saved.")
        return

    phone = input("Phone (optional): ").strip()
    source = input("Source (e.g. LinkedIn, website, referral; optional): ").strip()
    notes = input("Notes (optional): ").strip()

    leads = load_leads()
    if email and any((lead.get("email", "").lower() == email.lower()) for lead in leads):
        print("\nSales Agent: A lead with that email already exists. No duplicate was added.")
        return

    lead = {
        "id": max([int(item.get("id", 0)) for item in leads if str(item.get("id", "0")).isdigit()] or [0]) + 1,
        "name": name,
        "company": company,
        "email": email,
        "phone": phone,
        "source": source,
        "notes": notes,
        "status": "New",
        "follow_up_due": (datetime.now(INDIA_TIMEZONE).date() + timedelta(days=1)).isoformat(),
        "created_at": datetime.now(INDIA_TIMEZONE).isoformat(timespec="seconds"),
    }
    leads.append(lead)
    save_leads(leads)
    print(f"\nSales Agent: Lead saved successfully (ID {lead['id']}).")
    print(f"Name: {name}")
    print(f"Company: {company or '(not provided)'}")
    print(f"Email: {email or '(not provided)'}")


def list_leads(leads=None):
    leads = load_leads() if leads is None else leads
    if not leads:
        print("\nSales Agent: No leads saved yet. Type 'add lead' to create one.")
        return []

    print("\n" + "=" * 65)
    print("SAVED LEADS")
    print("=" * 65)
    for lead in leads:
        print(
            f"ID {lead.get('id', '?')} | {lead.get('name', 'Unnamed')} | "
            f"{lead.get('company') or 'No company'} | {lead.get('email') or 'No email'} | "
            f"Status: {lead_status(lead)} | Priority: {lead_priority(lead)} | "
            f"Follow-up: {lead_due_date(lead)}"
        )
    print("=" * 65)
    return leads


def search_leads(query):
    leads = load_leads()
    term = query.strip().lower()
    if not term:
        list_leads(leads)
        return

    matches = [
        lead for lead in leads
        if term in " ".join(str(lead.get(key, "")) for key in
                             ("name", "company", "email", "phone", "source", "notes")).lower()
    ]
    if not matches:
        print(f"\nSales Agent: No leads matched '{query}'.")
        return
    list_leads(matches)


def email_a_lead():
    leads = [lead for lead in load_leads() if is_valid_email(lead.get("email", ""))]
    if not leads:
        print("\nSales Agent: No saved leads have a valid email address. Add a lead with an email first.")
        return

    list_leads(leads)
    selection = input("Enter the lead ID to email, or press Enter to cancel: ").strip()
    if not selection:
        print("\nSales Agent: Email request cancelled.")
        return
    try:
        lead_id = int(selection)
    except ValueError:
        print("\nSales Agent: Please enter a numeric lead ID.")
        return

    lead = next((item for item in leads if item.get("id") == lead_id), None)
    if not lead:
        print("\nSales Agent: No lead found with that ID.")
        return

    state["last_recipient"] = lead["email"]
    save_state()
    purpose = input(f"What should the email to {lead['name']} be about? ").strip()
    if not purpose:
        print("\nSales Agent: Email cancelled because no purpose was provided.")
        return

    request = (
        f"Draft a professional email to {lead['name']}"
        f"{(' at ' + lead['company']) if lead.get('company') else ''}. "
        f"Email purpose: {purpose}. Lead notes: {lead.get('notes') or 'None provided'}. "
        "Do not invent personal details or claims."
    )
    handle_email_request(request)


def handle_lead_request(user_request):
    lower = user_request.lower().strip()
    if lower in {"sales dashboard", "lead dashboard"}:
        sales_dashboard()
    elif lower in {"follow-up queue", "follow up queue"}:
        follow_up_queue()
    elif lower.startswith(("update lead status", "mark lead")):
        parts = user_request.strip().split(maxsplit=3)
        if lower.startswith("update lead status"):
            if len(parts) < 4:
                print("\nSales Agent: Use 'update lead status <ID> <status>', e.g. update lead status 2 Qualified.")
                return
            lead_id, status = parts[3].split(maxsplit=1)[0], parts[3].split(maxsplit=1)[1] if len(parts[3].split(maxsplit=1)) > 1 else ""
            if not status:
                print("\nSales Agent: Add a status after the lead ID.")
                return
        else:
            if len(parts) < 4:
                print("\nSales Agent: Use 'mark lead <ID> <status>'.")
                return
            lead_id, status = parts[2], parts[3]
        update_lead_status(lead_id, status)
    elif lower.startswith(("set follow-up", "set follow up")):
        match = re.match(r"(?i)^set follow[- ]?up\s+(\d+)\s+(\d{4}-\d{2}-\d{2})$", user_request.strip())
        if not match:
            print("\nSales Agent: Use 'set follow-up <ID> YYYY-MM-DD', e.g. set follow-up 2 2026-10-20.")
            return
        set_lead_follow_up(match.group(1), match.group(2))
    elif lower.startswith(("add lead", "capture lead", "save lead", "new lead")):
        add_lead()
    elif lower.startswith(("list leads", "show leads", "view leads", "lead list")):
        list_leads()
    elif lower.startswith("search leads"):
        query = user_request[len("search leads"):].strip()
        search_leads(query)
    elif lower.startswith(("email lead", "contact lead")):
        email_a_lead()
    else:
        print("\nSales Agent: Use 'add lead', 'list leads', 'sales dashboard', 'follow-up queue', or 'search leads <term>'.")


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
    """Handle calculator commands without intercepting ordinary product questions."""
    text = user_request.lower().replace(",", "").strip()

    # Explicit quantity/price labels, e.g. "quantity 5 price 200".
    labeled_match = re.search(
        r"\bquantity\s*[:=]?\s*(-?\d+(?:\.\d+)?)"
        r".{0,40}?\b(?:unit\s*)?price\s*[:=]?\s*(-?\d+(?:\.\d+)?)\b",
        text,
    )

    # Natural language, e.g. "5 items at 200 each".
    items_match = re.search(
        r"(?<!\w)(-?\d+(?:\.\d+)?)\s+(?:items?|units?|products?)\s+"
        r"(?:at|for|cost(?:ing)?)\s+\$?\s*(-?\d+(?:\.\d+)?)"
        r"(?:\s+each)?\b",
        text,
    )

    # Arithmetic, e.g. "calculate 5 x 200" or "5 * 200".
    multiplication_match = re.search(
        r"(?<!\w)(?:calculate|total|multiply|what\s+is|how\s+much\s+is)?\s*"
        r"(-?\d+(?:\.\d+)?)\s*(?:x|\*|×|times)\s*"
        r"\$?\s*(-?\d+(?:\.\d+)?)\b",
        text,
    )

    match = labeled_match or items_match or multiplication_match

    # Explicit calculator wording may deserve a helpful usage message when malformed.
    # Do not intercept a normal product question just because it contains "product(s)".
    explicit_calculation_request = bool(
        re.search(r"\b(?:calculate|calculation|quantity|unit\s+price)\b", text)
    ) or bool(re.match(r"^(?:total|multiply)\b", text))

    if not match and not explicit_calculation_request:
        return False

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
    text_lower = (text or "").lower().strip()

    # An explicit address strongly indicates an email task.
    if extract_email(text_lower):
        return True

    email_action_words = [
        "send an email", "send email", "send that information",
        "send this information", "email this", "email that",
        "write an email", "draft an email", "compose an email",
        "create an email", "prepare an email", "write a mail",
        "send a mail", "draft a mail",
    ]
    if any(phrase in text_lower for phrase in email_action_words):
        return True

    # Accept natural requests such as "Draft a personalized follow-up email";
    # modifiers between the action and the word email should not break routing.
    flexible_email_action = r"\b(?:draft|write|compose|create|prepare|generate)\b.{0,100}\b(?:email|e-mail|mail)\b"
    if re.search(flexible_email_action, text_lower, flags=re.DOTALL):
        return True

    # Follow-ups are treated as email tasks when we have a draft.
    has_previous_draft = bool(
        state.get("last_subject") and state.get("last_message")
    )
    if has_previous_draft and is_email_followup(text_lower):
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


def sanitize_email_body(message):
    """Remove common unresolved placeholders and the unsupported claim seen in testing."""
    cleaned_lines = []

    for line in message.splitlines():
        stripped = line.strip()

        if re.fullmatch(
            r"\[\s*(?:your name|your company(?: name)?|sender name)\s*\]",
            stripped,
            flags=re.IGNORECASE,
        ):
            continue

        if re.search(
            r"recently searched for leads|expressed interest in sending an email to a lead",
            stripped,
            flags=re.IGNORECASE,
        ):
            continue

        cleaned_lines.append(line)

    result = "\n".join(cleaned_lines).strip()
    result = re.sub(r"\n{3,}", "\n\n", result)
    result = re.sub(
        r"(?im)(?:\n\s*)?(?:best regards|kind regards|regards|sincerely),?\s*$",
        "",
        result,
    ).strip()
    return result


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
Do not claim the recipient already uses our product, that we have met before,
or that we know facts about their company unless the user supplied those facts.
Do not imply an existing customer relationship.
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
Do not claim the recipient already uses our product, that we have met before,
or that we know facts about their company unless the user supplied those facts.
Do not imply an existing customer relationship.
Do not promise a demo or meeting unless the user requests it.
Do not include placeholders such as [Your Name], [Company Name], or
[Your Company Name]. If the sender's company name is unknown, omit it.
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

    if message:
        message = sanitize_email_body(message)

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

        # Match the authorization flow used in working versions 3 and 4.
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
                "Google authorization could not be refreshed. Delete or "
                "rename token.json, then restart the app to authorize Gmail "
                "and Calendar with the same scopes used in versions 3 and 4."
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
        # Keep this identical to versions 3 and 4; do not add OAuth parameters.
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
    """Detect natural-language requests to book meetings, demos, or appointments.

    The previous exact-phrase checks missed requests such as
    "Schedule a 30-minute product demonstration meeting ..." because words
    appeared between "schedule" and "meeting". Keep explicit calendar phrases,
    and also recognise an action followed by a meeting-related term.
    """
    lower = (text or "").casefold().strip()
    if not lower:
        return False

    phrases = (
        "create a calendar event", "add to my calendar", "add it to calendar",
        "put it on my calendar", "calendar event", "google calendar",
    )
    if any(phrase in lower for phrase in phrases):
        return True

    # Permit descriptive words between the action and the meeting type, e.g.
    # "schedule a 30-minute product demonstration meeting for tomorrow".
    action = r"\b(?:schedule|book|create|arrange|set up|organise|organize)\b"
    event_type = r"\b(?:meeting|appointment|demo|demonstration|call)\b"
    if re.search(action + r".{0,140}" + event_type, lower, flags=re.DOTALL):
        return True

    # Also catch phrases where the event type comes first, e.g. "meeting with X
    # tomorrow" only when paired with a clear booking action elsewhere.
    return bool(
        re.search(r"\b(?:schedule|book|create|arrange|set up)\b", lower)
        and re.search(event_type, lower)
    )


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


def extract_calendar_request_details(user_request):
    """Extract simple, explicit title/date/time/duration details from a request.

    Supports quoted titles, today/tomorrow, YYYY-MM-DD, and common 12/24-hour
    time ranges. Missing or ambiguous details are still requested interactively.
    """
    details = {}
    text = (user_request or "").strip()
    if not text:
        return details

    title_match = re.search(r'["\u201c]([^"\u201d]{3,120})["\u201d]', text)
    if title_match:
        details["title"] = title_match.group(1).strip()

    today = datetime.now(INDIA_TIMEZONE).date()
    lowered = text.casefold()
    date_value = None
    if re.search(r"\btomorrow\b", lowered):
        date_value = today + timedelta(days=1)
    elif re.search(r"\btoday\b", lowered):
        date_value = today
    else:
        date_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
        if date_match:
            try:
                date_value = datetime.strptime(date_match.group(1), "%Y-%m-%d").date()
            except ValueError:
                date_value = None
    if date_value:
        details["date"] = date_value.isoformat()

    # Examples: 3:00 PM to 3:30 PM, 15:00-15:30, 3 PM to 3:30 PM.
    time_match = re.search(
        r"\bfrom\s+(\d{1,2}(?::\d{2})?\s*(?:AM|PM)?)\s+(?:to|until|-)\s+"
        r"(\d{1,2}(?::\d{2})?\s*(?:AM|PM)?)\b",
        text,
        flags=re.IGNORECASE,
    )
    if not time_match:
        time_match = re.search(
            r"\b(\d{1,2}:\d{2}\s*(?:AM|PM)?)\s*(?:to|until|-)\s*"
            r"(\d{1,2}:\d{2}\s*(?:AM|PM)?)\b",
            text,
            flags=re.IGNORECASE,
        )

    def to_24_hour(value):
        value = re.sub(r"\s+", " ", value.strip().upper())
        formats = ("%I:%M %p", "%I %p", "%H:%M")
        for fmt in formats:
            try:
                parsed = datetime.strptime(value, fmt)
                return parsed.strftime("%H:%M")
            except ValueError:
                continue
        return None

    if time_match:
        start_time = to_24_hour(time_match.group(1))
        end_time = to_24_hour(time_match.group(2))
        if start_time and end_time:
            start_minutes = int(start_time[:2]) * 60 + int(start_time[3:])
            end_minutes = int(end_time[:2]) * 60 + int(end_time[3:])
            if end_minutes > start_minutes:
                details["start_time"] = start_time
                details["duration"] = end_minutes - start_minutes

    details["attendee"] = extract_email(text)
    return details


def get_primary_calendar_details(service=None):
    """Return the authenticated user's primary calendar metadata when allowed."""
    service = service or get_calendar_service()
    calendar = service.calendarList().get(calendarId="primary").execute()
    return {
        "id": calendar.get("id"),
        "summary": calendar.get("summary") or "Primary Google Calendar",
        "timeZone": calendar.get("timeZone") or CALENDAR_TIMEZONE_NAME,
        "primary": calendar.get("primary", True),
    }


def looks_like_calendar_account_question(text):
    """Detect questions about which Google account/calendar owns an event."""
    lower = (text or "").casefold()
    asks_calendar = any(term in lower for term in (
        "calendar", "meeting", "event", "appointment",
    ))
    asks_owner = any(term in lower for term in (
        "whose", "which account", "my gmail", "my google", "my calendar",
        "santhiya calendar", "santhiya's calendar", "santhiya calender",
        "santhiya's calender", "her calendar", "their calendar", "owner",
        "created on", "created in",
    ))
    return asks_calendar and asks_owner


def calendar_request_requires_attendee(user_request):
    """Require an email when the request asks for an invitee or names a person."""
    text = user_request or ""
    explicitly_requested = re.search(
        r"\b(?:attendee|attendees|invite|invitation|participant|participants)\b",
        text,
        re.IGNORECASE,
    )
    named_meeting_guest = re.search(
        r"\b(?:meeting|appointment|demo|demonstration|call)\b.{0,100}\bwith\s+[A-Z][a-z]+",
        text,
    )
    return bool(explicitly_requested or named_meeting_guest)


def answer_calendar_account_question():
    """Answer using Google Calendar metadata, not the language model's guess."""
    try:
        details = get_primary_calendar_details()
        calendar_id = details.get("id") or "not exposed by Google Calendar"
        summary = details.get("summary") or "Primary Google Calendar"
        timezone_name = details.get("timeZone") or CALENDAR_TIMEZONE_NAME
        print("\nSales Agent: Calendar events created by this app are added to the primary calendar of the Google account authorized through OAuth.")
        print(f"Primary calendar name: {summary}")
        print(f"Calendar ID/account: {calendar_id}")
        print(f"Calendar time zone: {timezone_name}")
        print("An event is not added to Santhiya's calendar automatically. To invite her, add her email address as an attendee; Google Calendar can send the invitation. The attendee's calendar is not directly edited by this app.")
    except Exception as error:
        print("\nSales Agent: I could not verify the authenticated calendar account from Google Calendar metadata.")
        print("Events created with calendarId='primary' are intended for the primary calendar of the Google account authorized through OAuth, not automatically Santhiya's calendar.")
        print(f"Calendar metadata error: {error}")


def default_calendar_title(user_request):
    """Create a sensible title when a booking request omits one."""
    text = (user_request or "").strip()
    if not text:
        return "Meeting"

    lowered = text.casefold()
    person_match = re.search(
        r"\bwith\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})",
        text,
    )
    person = person_match.group(1).strip() if person_match else None

    if "demonstration" in lowered or re.search(r"\bdemo\b", lowered):
        base = "Product Demonstration"
    elif "appointment" in lowered:
        base = "Appointment"
    elif "interview" in lowered:
        base = "Interview"
    else:
        base = "Meeting"

    return f"{base} with {person}" if person else base


def create_calendar_appointment(title_default=None, attendee_default=None, user_request=None):
    """Collect details, check conflicts, preview, and require confirmation."""
    print("\nSales Agent: Let's schedule a Google Calendar appointment.")
    extracted = extract_calendar_request_details(user_request)
    title_default = extracted.get("title") or title_default or default_calendar_title(user_request)
    attendee_default = extracted.get("attendee") or attendee_default
    attendee_required = calendar_request_requires_attendee(user_request)

    if title_default:
        title = input(f"Meeting title [{title_default}]: ").strip() or title_default
    else:
        title = input("Meeting title: ").strip()
    if not title:
        print("\nSales Agent: Meeting title cannot be empty. Booking cancelled.")
        return

    # Retry invalid/past date-time input instead of cancelling the workflow immediately.
    start = None
    date_default = extracted.get("date", "")
    time_default = extracted.get("start_time", "")
    for attempt in range(3):
        date_prompt = f"Date (YYYY-MM-DD, India time) [{date_default}]: " if date_default else "Date (YYYY-MM-DD, India time): "
        time_prompt = f"Start time (24-hour HH:MM) [{time_default}]: " if time_default else "Start time (24-hour HH:MM, e.g. 15:30): "
        date_text = input(date_prompt).strip() or date_default
        time_text = input(time_prompt).strip() or time_default
        try:
            candidate = parse_calendar_datetime(date_text, time_text)
        except ValueError as error:
            print(f"\nSales Agent: Invalid date or time: {error}")
            print("Use date YYYY-MM-DD and time HH:MM in 24-hour format.")
            continue

        if candidate > datetime.now(INDIA_TIMEZONE):
            start = candidate
            break

        print(
            "\nSales Agent: That start time is in the past. "
            "Please enter a future date and time."
        )

    if start is None:
        print("\nSales Agent: Booking cancelled after three invalid or past time attempts.")
        return

    duration_default = str(extracted.get("duration", 30))
    duration_text = input(f"Duration in minutes (default {duration_default}): ").strip() or duration_default
    if attendee_default:
        attendee = input(f"Attendee email [{attendee_default}]: ").strip() or attendee_default
    elif attendee_required:
        attendee = input("Attendee email (required by your request): ").strip()
    else:
        attendee = input("Attendee email (optional; press Enter to skip): ").strip()

    if attendee_required and not attendee:
        print("\nSales Agent: Your request specified an attendee, but no email was provided. No event was created.")
        return
    if attendee and not is_valid_email(attendee):
        print("\nSales Agent: That attendee email address is invalid. Booking cancelled.")
        return

    description = input("Description (optional; press Enter to skip): ").strip()

    try:
        duration = int(duration_text)
        if duration < 5 or duration > 480:
            raise ValueError("Duration must be between 5 and 480 minutes.")
        end = start + timedelta(minutes=duration)
    except ValueError as error:
        print(f"\nSales Agent: Invalid duration: {error}")
        print("Use a whole-number duration between 5 and 480 minutes.")
        return

    try:
        service = get_calendar_service()
        try:
            calendar_details = get_primary_calendar_details(service)
        except Exception:
            calendar_details = {
                "summary": "Primary Google Calendar (account not verified)",
                "id": "Unavailable",
                "timeZone": CALENDAR_TIMEZONE_NAME,
            }
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
            event_start = (
                event.get("start", {}).get("dateTime")
                or event.get("start", {}).get("date", "time unavailable")
            )
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
    print(f"Calendar: {calendar_details.get('summary', 'Primary Google Calendar')}")
    print(f"Calendar account/ID: {calendar_details.get('id', 'Unavailable')}")
    print(f"Attendee: {attendee or 'No attendee added'}")
    print(f"Description: {description or '(none)'}")

    requested_time = extracted.get("start_time")
    if requested_time and start.strftime("%H:%M") != requested_time:
        print("\nWARNING: The start time differs from the time parsed from your original request.")
        print(f"Requested start: {requested_time}; current start: {start.strftime('%H:%M')}.")
        use_changed_time = input("Type 'yes' to keep this changed time, or anything else to cancel: ").strip().lower()
        if use_changed_time not in {"yes", "y"}:
            print("\nSales Agent: Booking cancelled. No event was created.")
            return
    print("=" * 55)
    confirmation = input(
        "Create this event? Type 'yes' to confirm or 'no' to cancel: "
    ).strip().lower()
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


def is_email_send_confirmation(choice):
    """Recognize natural affirmative phrases without regenerating the draft."""
    return (choice or "").strip().casefold() in {
        "yes", "y", "send", "confirm", "ok send it", "okay send it",
        "yes send it", "please send it", "go ahead", "go ahead and send",
        "go ahead and send it", "send it now", "ok, send it", "okay, send it",
    }


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

        if is_email_send_confirmation(choice_lower):
            success = send_email(recipient, subject, message)

            if success:
                state["last_recipient"] = recipient
                state["last_subject"] = subject
                state["last_message"] = message
                save_state()
                update_lead_after_successful_email(
                    state.get("pending_lead_id"), recipient
                )

                remember(
                    "assistant",
                    f"Email sent to {recipient}. Subject: {subject}",
                )

            else:
                print(
                    "\nThe email was not confirmed as sent. "
                    "Please check the error above before retrying."
                )

            return success

        if choice_lower in {"no", "n", "cancel", "stop"}:
            print("\nEmail cancelled. Nothing was sent.")
            return False

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

def find_lead_referenced_in_text(user_request):
    """Return the saved lead explicitly named in a request, if any."""
    text = (user_request or "").casefold()
    leads = load_leads()
    # Prefer the longest name/company match to avoid short-name collisions.
    candidates = []
    for lead in leads:
        for key in ("name", "company"):
            value = str(lead.get(key) or "").strip()
            if len(value) >= 3 and value.casefold() in text:
                candidates.append((len(value), lead))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def update_lead_after_successful_email(lead_id, recipient):
    """Update a linked lead only after Gmail confirms the message was sent."""
    if lead_id is None:
        return
    leads = load_leads()
    lead = find_lead_by_id(leads, lead_id)
    if not lead:
        return
    saved_email = str(lead.get("email") or "").strip().casefold()
    if saved_email and saved_email != str(recipient or "").strip().casefold():
        print(
            "\nSales Agent: Email was sent, but the lead record was not updated "
            "because the recipient differs from the saved lead email."
        )
        return
    now = datetime.now(INDIA_TIMEZONE)
    lead["status"] = "Contacted"
    lead["last_contacted_at"] = now.isoformat(timespec="seconds")
    lead["follow_up_due"] = (now.date() + timedelta(days=3)).isoformat()
    save_leads(leads)
    print(
        f"\nSales Agent: Lead status updated to Contacted. "
        f"Next follow-up: {lead['follow_up_due']}."
    )


def handle_email_request(user_request):
    explicit_recipient = extract_email(user_request)
    matched_lead = find_lead_referenced_in_text(user_request)

    # If the request names a saved lead, use that lead's address rather than
    # accidentally reusing a stale recipient from a previous email.
    if explicit_recipient:
        recipient = explicit_recipient
        if matched_lead and str(matched_lead.get("email") or "").strip():
            saved_email = matched_lead["email"].strip()
            if saved_email.casefold() != explicit_recipient.casefold():
                print(
                    f"\nSales Agent: The request names {matched_lead.get('name')}, "
                    f"whose saved email is {saved_email}, but the request specifies "
                    f"{explicit_recipient}. I will use the explicitly provided "
                    "address shown in the preview; please verify it before approving."
                )
        state["last_recipient"] = recipient
        state["pending_lead_id"] = matched_lead.get("id") if matched_lead else None
        save_state()
    elif matched_lead:
        recipient = str(matched_lead.get("email") or "").strip()
        state["pending_lead_id"] = matched_lead.get("id")
        if recipient:
            state["last_recipient"] = recipient
        save_state()
    else:
        recipient = state.get("last_recipient")
        state["pending_lead_id"] = None
        save_state()

    if not recipient or not is_valid_email(recipient):
        print(
            "\nSales Agent: Please provide the recipient's complete "
            "email address."
        )
        return False

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
        return confirm_or_edit_email(
            recipient,
            state["last_subject"],
            state["last_message"],
        )

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
        return False

    state["last_recipient"] = recipient
    state["last_subject"] = subject
    state["last_message"] = message
    save_state()

    # Never send without displaying a preview and asking for confirmation.
    return confirm_or_edit_email(recipient, subject, message)


# ============================================================
# LEAD FOLLOW-UP WORKFLOW
# ============================================================

def follow_up_lead():
    """Select a saved lead, send a reviewed email, then optionally book a meeting."""
    leads = [lead for lead in load_leads() if is_valid_email(lead.get("email", ""))]
    if not leads:
        print("\nSales Agent: No saved leads have a valid email address. Use 'add lead' first.")
        return

    list_leads(leads)
    selection = input("Enter the lead ID to follow up with, or press Enter to cancel: ").strip()
    if not selection:
        print("\nSales Agent: Follow-up cancelled.")
        return

    try:
        lead_id = int(selection)
    except ValueError:
        print("\nSales Agent: Please enter a numeric lead ID.")
        return

    lead = next((item for item in leads if item.get("id") == lead_id), None)
    if not lead:
        print("\nSales Agent: No lead found with that ID.")
        return

    purpose = input(f"What should the email to {lead['name']} be about? ").strip()
    if not purpose:
        print("\nSales Agent: Follow-up cancelled because no email purpose was provided.")
        return

    state["last_recipient"] = lead["email"]
    save_state()

    company_context = f" at {lead['company']}" if lead.get("company") else ""
    notes_context = lead.get("notes") or "None provided"
    request = (
        f"Draft a professional email to {lead['name']}{company_context}. "
        f"Email purpose: {purpose}. Lead notes supplied by the user: {notes_context}. "
        "Use only the facts in this request and the supplied product information. "
        "Do not claim the recipient already uses our product or that we have met before. "
        "Do not invent facts about the lead or their company."
    )

    sent = handle_email_request(request)
    if not sent:
        print("\nSales Agent: No meeting workflow started because the email was not sent.")
        return

    # Record the completed action and set a suggested next follow-up in three days.
    refreshed_leads = load_leads()
    refreshed_lead = find_lead_by_id(refreshed_leads, lead_id)
    if refreshed_lead:
        refreshed_lead["status"] = "Contacted"
        refreshed_lead["last_contacted_at"] = datetime.now(INDIA_TIMEZONE).isoformat(timespec="seconds")
        refreshed_lead["follow_up_due"] = (datetime.now(INDIA_TIMEZONE).date() + timedelta(days=3)).isoformat()
        save_leads(refreshed_leads)
        print(f"\nSales Agent: Lead status updated to Contacted. Suggested next follow-up: {refreshed_lead['follow_up_due']}.")

    schedule = input(
        "\nWould you like to schedule a follow-up meeting with this lead? Type 'yes' or 'no': "
    ).strip().lower()
    if schedule not in {"yes", "y"}:
        print("\nSales Agent: Email follow-up completed. No meeting was scheduled.")
        return

    create_calendar_appointment(
        title_default=f"Follow-up with {lead['name']}",
        attendee_default=lead["email"],
    )


# ============================================================
# SALES AUTOMATION WORKFLOW
# ============================================================

def build_follow_up_request(lead):
    """Create a grounded follow-up request from a saved lead's known details."""
    name = str(lead.get("name") or "there").strip()
    company = str(lead.get("company") or "").strip()
    email = str(lead.get("email") or "").strip()
    notes = str(lead.get("notes") or "").strip()
    source = str(lead.get("source") or "").strip()

    context_parts = []
    if notes:
        context_parts.append(f"Lead notes: {notes}.")
    if source:
        context_parts.append(f"Lead source: {source}.")
    context = " ".join(context_parts) or "No additional lead context was recorded."
    company_context = f" at {company}" if company else ""

    return (
        f"Draft a concise, professional follow-up email to {name}{company_context} "
        f"at {email}. Purpose: check whether they would like to discuss their needs "
        f"and agree on a useful next step. {context} "
        "Use only known facts and the supplied product knowledge. Do not invent a prior "
        "conversation, customer relationship, company details, integrations, guarantees, "
        "discounts, or outcomes. Keep the tone helpful and low-pressure."
    )


def run_sales_automation():
    """Triage due leads and run reviewed follow-up workflows one lead at a time.

    This is intentionally human-in-the-loop: it never sends email or books meetings
    without the existing confirmation steps.
    """
    today = datetime.now(INDIA_TIMEZONE).date()
    open_leads = []
    for lead in load_leads():
        if lead_status(lead).strip().lower() in {"won", "lost", "closed"}:
            continue
        due = parse_iso_date(lead.get("follow_up_due"))
        if due and due <= today:
            open_leads.append((lead, due))

    priority_order = {"High": 0, "Medium": 1, "Low": 2}
    open_leads.sort(key=lambda item: (
        item[1], priority_order[lead_priority(item[0])],
        str(item[0].get("name", "")).lower()
    ))

    print("\n" + "=" * 72)
    print("AI SALES AUTOMATION — TRIAGE AND FOLLOW-UP")
    print("=" * 72)
    print("The agent will identify due leads, prioritise them, and prepare follow-ups.")
    print("Email drafts require your review and explicit approval before sending.")
    print("Calendar meetings are created only if you separately confirm them.")

    if not open_leads:
        print("\nNo open leads are due for follow-up today.")
        print("Use 'sales dashboard' to review the pipeline or 'add lead' to capture a lead.")
        print("=" * 72)
        return

    print(f"\nFound {len(open_leads)} open lead(s) due today or overdue:")
    for lead, due in open_leads:
        timing = "OVERDUE" if due < today else "DUE TODAY"
        next_action = (
            "Prepare a personalised follow-up"
            if is_valid_email(lead.get("email", ""))
            else "Add a valid email address before contacting"
        )
        print(
            f"- ID {lead.get('id')} | {lead.get('name', 'Unnamed')} | "
            f"{timing} {due.isoformat()} | Priority {lead_priority(lead)} | {next_action}"
        )

    processed = 0
    sent_count = 0
    for lead, due in open_leads:
        if not is_valid_email(lead.get("email", "")):
            print(
                f"\nSkipping {lead.get('name', 'Unnamed')} (ID {lead.get('id')}): "
                "no valid email address is saved. Update the lead before contacting them."
            )
            continue

        choice = input(
            f"\nPrepare a follow-up for {lead.get('name')} "
            f"(ID {lead.get('id')}, {lead_priority(lead)} priority)? [yes/no/stop]: "
        ).strip().lower()
        if choice in {"stop", "quit", "exit"}:
            print("\nAutomation stopped by user. No further leads were processed.")
            break
        if choice not in {"yes", "y"}:
            print(f"Skipped {lead.get('name')} for now.")
            continue

        processed += 1
        request = build_follow_up_request(lead)
        sent = handle_email_request(request)
        if not sent:
            print(
                f"No email was confirmed as sent for {lead.get('name')}. "
                "The lead's contact status and follow-up date were not changed."
            )
            continue

        sent_count += 1
        refreshed_leads = load_leads()
        refreshed_lead = find_lead_by_id(refreshed_leads, lead.get("id"))
        if refreshed_lead:
            refreshed_lead["status"] = "Contacted"
            refreshed_lead["last_contacted_at"] = datetime.now(INDIA_TIMEZONE).isoformat(timespec="seconds")
            refreshed_lead["follow_up_due"] = (
                datetime.now(INDIA_TIMEZONE).date() + timedelta(days=3)
            ).isoformat()
            save_leads(refreshed_leads)
            print(
                f"Lead updated: {refreshed_lead.get('name')} → Contacted. "
                f"Next follow-up: {refreshed_lead['follow_up_due']}."
            )

        schedule = input(
            f"Schedule a Calendar follow-up with {lead.get('name')}? [yes/no]: "
        ).strip().lower()
        if schedule in {"yes", "y"}:
            create_calendar_appointment(
                title_default=f"Follow-up with {lead.get('name')}",
                attendee_default=lead.get("email"),
            )
        else:
            print("No meeting was scheduled.")

    print("\nAUTOMATION SUMMARY")
    print(f"Leads considered: {len(open_leads)}")
    print(f"Follow-up workflows started: {processed}")
    print(f"Emails confirmed sent: {sent_count}")
    print("No emails were sent without explicit approval.")
    print("=" * 72)


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
        # Multi-lead sales automation: triage due leads and run reviewed follow-ups.
        if text.lower().strip() in {"sales automation", "run sales automation", "automation run"}:
            run_sales_automation()
            return

        # End-to-end follow-up: select lead, review/send email, optionally book a meeting.
        if text.lower().strip() in {"follow up lead", "follow-up lead", "followup lead"}:
            follow_up_lead()
            return

        # Lead commands are handled locally and saved to leads.json.
        if looks_like_lead_request(text):
            handle_lead_request(text)
            return

        # Answer calendar ownership questions from Google Calendar metadata.
        if looks_like_calendar_account_question(text):
            answer_calendar_account_question()
            return

        # Calendar creation is an explicit, interactive action with confirmation.
        if looks_like_calendar_request(text):
            create_calendar_appointment(user_request=text)
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
    print("AI SALES COPILOT — VERSION 7")
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
    print("- Type 'add lead', 'list leads', 'search leads <term>', or 'email lead'")
    print("- Type 'follow up lead' for one lead → reviewed email → optional meeting")
    print("- Type 'sales automation' to triage due leads and prepare reviewed follow-ups")
    print("- Type 'sales dashboard' to see pipeline, priorities, and overdue follow-ups")
    print("- Type 'follow-up queue' to list leads needing attention")
    print("- Type 'update lead status <ID> <status>' to update pipeline status")
    print("- Type 'set follow-up <ID> YYYY-MM-DD' to set a follow-up date")
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
