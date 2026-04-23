import requests
import json
import base64
import os
import asyncio
import edge_tts
import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
import pygame
import re
from PIL import Image
from transformers import pipeline
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor
import trafilatura

# -----------------------------
# CONFIG & MODELS
# -----------------------------
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma4"  # Para visão real, usa-se 'llava' ou 'moondream'

print("🔧 Inicializando sistemas...")
print("🎤 Carregando ouvidos (Whisper)...")
stt_model = whisper.load_model("base")

print("🎭 Carregando análise de emoções...")
sentiment_pipeline = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    top_k=1
)

# Inicializa o Mixer do Pygame para áudio
pygame.mixer.init()

# Executor para rodar tarefas síncronas (IA) sem travar o loop async
executor = ThreadPoolExecutor(max_workers=3)

# -----------------------------
# SKILL: ANÁLISE DE SENTIMENTO
# -----------------------------
def analyze_sentiment(text):
    if not text: return "neutro"
    try:
        # Traduz para inglês pois o modelo de emoção é treinado em inglês
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
    except:
        return "neutro"

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
# SKILL: VOZ (OUVIR E FALAR)
# -----------------------------
def listen_mic():
    fs = 16000
    seconds = 5
    print(f"\n🎤 Ouvindo por {seconds} segundos... (Fale agora)")
    
    recording = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
    sd.wait()
    sf.write("input_audio.wav", recording, fs)
    
    result = stt_model.transcribe("input_audio.wav", fp16=False)
    text = result["text"].strip()
    print(f"🎙️ Você disse: {text}")
    return text

async def speak_text(text):
    try:
        communicate = edge_tts.Communicate(text, "pt-PT-RaquelNeural")
        await communicate.save("response.mp3")
        
        pygame.mixer.music.load("response.mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)
        pygame.mixer.music.unload()
    except Exception as e:
        print(f"❌ Erro ao gerar áudio: {e}")

# -----------------------------
# SKILL: VISÃO E WEB
# -----------------------------
def process_image_to_base64(image_path):
    path = image_path.strip(' "\'')
    if not os.path.exists(path): 
        print(f"❌ Erro: Ficheiro não encontrado em: {path}")
        return None
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"❌ Erro de leitura: {e}")
        return None

def scrape_website(url):
    print(f"📄 A ler conteúdo em: {url}...")
    try:
        downloaded = trafilatura.fetch_url(url)
        content = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
        return content[:3000] if content else "Conteúdo vazio."
    except:
        return "Não consegui ler o site."

# -----------------------------
# NÚCLEO: OLLAMA INTEGRADO
# -----------------------------
def query_ollama(user_input, emotion, image_base64=None):
    estado_natural = emotion_to_natural(emotion)
    
    # Prompt que une a personalidade Jarvis com o estado emocional detectado
    system_prompt = (
        f"Você é o Jarvis. O utilizador parece estar {estado_natural}. "
        f"Responda de forma curta, natural e empática, adaptando o seu tom ao estado dele."
    )
    
    payload = {
        "model": MODEL_NAME,
        "prompt": f"{system_prompt}\nUtilizador: {user_input}",
        "stream": False
    }
    if image_base64: 
        payload["images"] = [image_base64]
    
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=120)
        return r.json().get("response", "").strip()
    except: 
        return "Erro de conexão com o Ollama."

# -----------------------------
# LOOP PRINCIPAL
# -----------------------------
async def main_loop():
    print("\n==========================================")
    print("SISTEMA JARVIS v1.5 - Voz, Visão e Emoção")
    print("ESTG - Instituto Politécnico da Guarda")
    print("==========================================\n")

    loop = asyncio.get_event_loop()

    while True:
        print("Opções: [Texto] | 'mic' | 'imagem: path' | 'site: url' | 'exit'")
        cmd = input("Tu: ").strip()

        if cmd.lower() == 'exit': break
        if not cmd: continue
        
        user_text = cmd
        image_base64 = None
        
        # 1. Captura de Input (Voz/Imagem/Site/Texto)
        if cmd.lower() == 'mic':
            user_text = await loop.run_in_executor(executor, listen_mic)
            if not user_text: continue
            
        elif cmd.lower().startswith("imagem:"):
            match = re.search(r'imagem:\s*["\']?([^"\']+)["\']?\s*(.*)', cmd, re.IGNORECASE)
            if match:
                path = match.group(1).strip()
                pergunta = match.group(2).strip()
                user_text = pergunta if pergunta else "O que vês nesta imagem?"
                image_base64 = process_image_to_base64(path)
                if not image_base64: continue
            else:
                print("❌ Formato: imagem: 'caminho' pergunta")
                continue

        elif cmd.lower().startswith("site:"):
            url = cmd.replace("site:", "").strip()
            web_content = await loop.run_in_executor(executor, scrape_website, url)
            user_text = f"Resuma este conteúdo: {web_content}"

        # 2. Processamento em paralelo: Emoção + LLM
        print(f"🧠 Jarvis está a processar...")
        
        # Analisa o sentimento enquanto prepara a resposta (executor para não travar)
        emotion = await loop.run_in_executor(executor, analyze_sentiment, user_text)
        estado_humano = emotion_to_natural(emotion)
        
        # Consulta o Ollama passando a emoção e a imagem (se houver)
        response = await loop.run_in_executor(executor, query_ollama, user_text, emotion, image_base64)
        
        # 3. Output
        print(f"\n(Pensamento do Jarvis: O utilizador está {estado_humano})")
        print(f"JARVIS: {response}\n")

        # 4. Lógica de resposta em áudio
        palavras_audio = ["áudio", "fala", "diga", "escutar", "ouvir", "explica"]
        if cmd.lower() == 'mic' or any(word in user_text.lower() for word in palavras_audio):
            print("🔊 Gerando áudio...")
            await speak_text(response)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\nJARVIS desligado. Até logo, Bernardo.")