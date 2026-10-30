import requests
import ollama


# ==============================
# WEATHER TOOL
# ==============================

def get_weather(city):
    """
    Get current weather information for a city.
    """

    url = f"https://wttr.in/{city}?format=j1"

    response = requests.get(url)

    if response.status_code != 200:
        return "Unable to get weather information."

    data = response.json()

    current = data["current_condition"][0]

    temperature = current["temp_C"]
    description = current["weatherDesc"][0]["value"]
    humidity = current["humidity"]

    return {
        "city": city,
        "temperature": temperature,
        "description": description,
        "humidity": humidity
    }


# ==============================
# CUSTOMER QUESTION
# ==============================

customer_question = input("Customer: ")


# ==============================
# GET CITY
# ==============================

city_prompt = f"""
Extract the city name from this question.

Return ONLY the city name.

Question:
{customer_question}
"""

response = ollama.chat(
    model="llama3.2:3b",
    messages=[
        {
            "role": "user",
            "content": city_prompt
        }
    ]
)

city = response.message.content.strip()

print("\nCity detected:", city)


# ==============================
# CALL WEATHER TOOL
# ==============================

weather = get_weather(city)

print("Weather data:", weather)


# ==============================
# ASK LLAMA FOR FINAL ANSWER
# ==============================

final_prompt = f"""
The customer asked:

{customer_question}

Here is the weather information:

{weather}

Answer the customer naturally and briefly.
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

print("\nAI Agent:")
print(final_response.message.content)