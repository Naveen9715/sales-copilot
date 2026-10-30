import ollama


# ==============================
# TOOL
# ==============================

def calculate_total(quantity: int, price: int) -> int:
    return quantity * price


# ==============================
# PRODUCT KNOWLEDGE
# ==============================

product_knowledge = """
Our product is an AI Automation Platform.

It helps businesses with:

- Customer support automation
- Lead generation
- Email automation
- Appointment scheduling
- Reducing repetitive manual work
"""


# ==============================
# CUSTOMER QUESTION
# ==============================

customer_question = input("Customer: ")


# ==============================
# CHECK IF CALCULATION IS NEEDED
# ==============================

question_lower = customer_question.lower()

calculation_words = [
    "calculate",
    "total",
    "cost",
    "price",
    "multiply",
    "how much"
]

needs_calculation = any(
    word in question_lower
    for word in calculation_words
)


# ==============================
# CALCULATION PATH
# ==============================

if needs_calculation:

    print("\nAgent decided: Calculation is needed.")

    # Ask Llama to extract numbers
    extraction_prompt = f"""
Extract the quantity and price from this question.

Return ONLY this format:

quantity,price

Example:
50,200

Question:
{customer_question}
"""

    response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {
                "role": "user",
                "content": extraction_prompt
            }
        ]
    )

    numbers = response.message.content.strip()

    print("Llama extracted:", numbers)

    # Convert extracted values
    quantity, price = numbers.split(",")

    quantity = int(quantity.strip())
    price = int(price.strip())

    # Run tool
    result = calculate_total(quantity, price)

    print("Tool: calculate_total")
    print("Quantity:", quantity)
    print("Price:", price)
    print("Tool result:", result)

    # Ask Llama for final response
    final_prompt = f"""
The customer asked:

{customer_question}

The calculator returned:

{result}

Give the customer a short and clear answer.
"""

    final_response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {
                "role": "user",
                "content": final_prompt
            }
        ]
    )

    print("\nSales Copilot:")
    print(final_response.message.content)


# ==============================
# NORMAL PRODUCT QUESTION
# ==============================

else:

    print("\nAgent decided: No tool needed.")

    prompt = f"""
You are a Sales Copilot.

Answer the customer's question using ONLY the
product information below.

PRODUCT INFORMATION:

{product_knowledge}

CUSTOMER QUESTION:

{customer_question}

Do not invent product features.
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

    print("\nSales Copilot:")
    print(response.message.content)