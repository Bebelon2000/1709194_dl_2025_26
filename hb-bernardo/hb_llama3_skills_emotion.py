import requests
from transformers import pipeline
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor

# -----------------------------
# CONFIG
# -----------------------------
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3"

# -----------------------------
# SENTIMENT
# -----------------------------
sentiment_pipeline = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    top_k=1
)

# -----------------------------
# SENTIMENT FUNCTION
# -----------------------------
def analyze_sentiment(text):
    translated = GoogleTranslator(source='auto', target='en').translate(text)
    result = sentiment_pipeline(translated)[0][0]

    emotion = result["label"].lower()
    score = result["score"]

    if score < 0.4:
        emotion = "neutral"

    mapping = {
        "joy": "alegria",
        "sadness": "tristeza",
        "anger": "raiva",
        "fear": "medo",
        "surprise": "surpresa",
        "disgust": "nojo",
        "neutral": "neutro"
    }

    return mapping.get(emotion, "neutro")


# -----------------------------
# OLLAMA FUNCTION
# -----------------------------
def query_ollama(user_input, emotion=None):
    if emotion:
        prompt = f"""
Utilizador: {user_input}
Estado emocional: {emotion}
Responde de forma empática.
"""
    else:
        prompt = f"""
Utilizador: {user_input}
Responde normalmente.
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        },
        timeout=60
    )

    return response.json().get("response", "").strip()


# -----------------------------
# NATURAL LANGUAGE
# -----------------------------
def emotion_to_natural(e):
    return {
        "tristeza": "triste",
        "alegria": "feliz",
        "raiva": "zangado",
        "medo": "com medo",
        "surpresa": "surpreendido",
        "nojo": "enojado",
        "neutro": "neutro"
    }.get(e, e)


# -----------------------------
# CHAT LOOP
# -----------------------------
def chat():
    print("Chat iniciado\n")

    with ThreadPoolExecutor(max_workers=2) as executor:
        while True:
            user_input = input("Tu: ").strip()

            if user_input == "exit":
                break

            # correr em paralelo
            future_sentiment = executor.submit(analyze_sentiment, user_input)
            future_llm = executor.submit(query_ollama, user_input)

            # obter resultados
            emotion = future_sentiment.result()
            response = future_llm.result()

            estado = emotion_to_natural(emotion)

            print(f"""
Resposta:
(thinking: o utilizador está {estado}, o modelo sentiu: {emotion})

{response}
""")

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    chat()