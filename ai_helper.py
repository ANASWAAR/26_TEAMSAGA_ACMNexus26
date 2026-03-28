

from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_ai_response(current):
    try:
        prompt = f"""
        You are a coastal safety expert.

        Current conditions:
        - Wave height: {current['waveHeight']} meters
        - Wind speed: {current['windSpeed']} m/s
        - Risk level: {current['riskLabel']}

        Explain the situation and give advice for fishermen.
        Keep it short and clear.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a coastal safety assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=120
        )

        return response.choices[0].message.content

    except Exception as e:
        return "AI service unavailable"
    