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
from transformers import pipeline
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

# -----------------------------
# CONFIG & MODELS
# -----------------------------
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma4"
# Carregamos o Whisper para STT (O modelo 'base' é rápido e preciso)
print("Carregando ouvidos (Whisper)...")
stt_model = whisper.load_model("base")

# Inicializa o Mixer do Pygame para áudio
pygame.mixer.init()

# -----------------------------
# SKILL: VOZ (OUVIR)
# -----------------------------
def listen_mic():
    """Grava áudio do microfone e transcreve para texto."""
    fs = 16000  # Frequência para o Whisper
    seconds = 5 # Tempo de gravação por comando
    print(f"\n🎤 Ouvindo por {seconds} segundos... (Fale agora)")
    
    recording = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
    sd.wait()
    sf.write("input_audio.wav", recording, fs)
    
    result = stt_model.transcribe("input_audio.wav", fp16=False)
    text = result["text"].strip()
    print(f"🎙️ Você disse: {text}")
    return text

# -----------------------------
# SKILL: VOZ (FALAR)
# -----------------------------
async def speak_text(text):
    """Transforma texto em fala e reproduz."""
    # Vozes recomendadas: pt-PT-RaquelNeural (Portugal) ou pt-BR-AntonioNeural (Brasil)
    communicate = edge_tts.Communicate(text, "pt-PT-RaquelNeural")
    await communicate.save("response.mp3")
    
    pygame.mixer.music.load("response.mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        continue
    pygame.mixer.music.unload() # Libera o arquivo

# -----------------------------
# MANTENDO AS FUNÇÕES ANTERIORES (Simplificadas para o exemplo)
# -----------------------------
def process_image_to_base64(image_path):
    image_path = image_path.strip(' "')
    if not os.path.exists(image_path): return None
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def query_ollama(user_input, image_base64=None):
    system_prompt = "Você é o Jarvis. Responda de forma curta e natural. Hoje é 21/04/2026."
    payload = {
        "model": MODEL_NAME,
        "prompt": f"{system_prompt}\nUtilizador: {user_input}",
        "stream": False
    }
    if image_base64: payload["images"] = [image_base64]
    
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=120)
        return r.json().get("response", "").strip()
    except: return "Erro de conexão."

# -----------------------------
# LOOP PRINCIPAL
# -----------------------------
async def main_loop():
    print("\n==========================================")
    print("SISTEMA JARVIS v1.3 - Visão e Voz Ativos")
    print("==========================================\n")

    while True:
        print("Opções: [Texto normal] | 'mic' para falar | 'imagem: path' | 'exit'")
        cmd = input("Tu: ").strip()

        if cmd.lower() == 'exit': break
        
        user_text = cmd
        image_base64 = None
        
        # Se o usuário quiser falar
        if cmd.lower() == 'mic':
            user_text = listen_mic()
            if not user_text: continue
            
        # Se houver imagem (mesma lógica anterior)
        elif cmd.lower().startswith("imagem:"):
            content = cmd[7:].strip()
            # ... (lógica de extração de path que usamos no v1.2) ...
            # Simplificado para o exemplo:
            path = content.split(" ")[0].replace('"', '')
            user_text = content.replace(path, "").strip() or "O que vês aqui?"
            image_base64 = process_image_to_base64(path)
            print(f"📸 Imagem carregada.")

        # Processar com a IA
        print("🧠 Pensando...")
        response = query_ollama(user_text, image_base64)
        
        print(f"\nJARVIS: {response}\n")

        # LOGICA DE RESPOSTA EM ÁUDIO
        # Se o usuário falou via 'mic' OU se a frase contém "áudio" ou "fala"
        palavras_audio = ["áudio", "fala", "diga", "escutar", "ouvir"]
        if cmd.lower() == 'mic' or any(word in user_text.lower() for word in palavras_audio):
            print("🔊 Gerando áudio...")
            await speak_text(response)

if __name__ == "__main__":
    asyncio.run(main_loop())