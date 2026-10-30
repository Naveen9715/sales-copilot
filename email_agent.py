import ollama


# ==============================
# EMAIL TOOL
# ==============================

def send_email(to, subject, message):
    """
    Simulate sending an email.
    """

    print("\n--- EMAIL TOOL ---")
    print("To:", to)
    print("Subject:", subject)
    print("Message:", message)
    print("------------------")

    return "Email sent successfully."


# ==============================
# USER REQUEST
# ==============================

user_request = input("User: ")


# ==============================
# ASK LLAMA TO EXTRACT DETAILS
# ==============================

prompt = f"""
You are an email assistant.

Extract the email information from the user's request.

Return EXACTLY this format:

TO: email@example.com
SUBJECT: short subject
MESSAGE: email message

User request:
{user_request}
"""

response = ollama.chat(
    model="llama3.2:3b",
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ]
)


# ==============================
# GET LLAMA RESPONSE
# ==============================

email_data = response.message.content.strip()

print("\nExtracted information:")
print(email_data)


# ==============================
# PARSE EMAIL DETAILS
# ==============================

to = ""
subject = ""
message = ""

for line in email_data.splitlines():

    if line.startswith("TO:"):
        to = line[3:].strip()

    elif line.startswith("SUBJECT:"):
        subject = line[8:].strip()

    elif line.startswith("MESSAGE:"):
        message = line[8:].strip()


# ==============================
# RUN EMAIL TOOL
# ==============================

if to and subject and message:

    result = send_email(
        to,
        subject,
        message
    )

    print("\nAI Agent:")
    print(result)

else:

    print("\nAI Agent:")
    print("Could not extract the email information.")