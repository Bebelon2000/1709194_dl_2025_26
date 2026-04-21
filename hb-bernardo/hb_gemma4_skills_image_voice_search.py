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
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

# -----------------------------
# CONFIG & MODELS
# -----------------------------
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma4"
SERPER_API_KEY = "b44f98569d153c04d760209a3f27de1702e21c6d" # Substitua pela sua chave do serper.dev

print("Carregando ouvidos (Whisper)...")
stt_model = whisper.load_model("base")
pygame.mixer.init()

# -----------------------------
# SKILL: GOOGLE SEARCH (INTELIGENTE)
# -----------------------------

def get_search_query(user_prompt):
    """Gera query limpa. Se falhar, usa o texto original."""
    print("🧠 Jarvis a extrair intenção...")
    prompt_decisao = f"Gere apenas termos de busca para: {user_prompt}. Seja direto."
    
    payload = {"model": MODEL_NAME, "prompt": prompt_decisao, "stream": False}
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=10) # Timeout curto aqui
        if r.status_code == 200:
            return r.json().get("response", user_prompt).strip().replace('"', '')
    except:
        pass
    return user_prompt

def google_search(user_text):
    query_otimizada = get_search_query(user_text)
    
    # Evitar o "hoje hoje": se a query já tem data, não adicionamos
    query_final = query_otimizada
    if "2026" not in query_final:
        query_final += " Portugal 21/04/2026"
    
    print(f"🌐 Google Search: {query_final}")
    
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query_final, "gl": "pt", "hl": "pt", "num": 5})
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}

    try:
        response = requests.post(url, headers=headers, data=payload, timeout=15)
        res_json = response.json()
        contexto = ""
        
        # Captura Snipetts orgânicos
        if "organic" in res_json:
            for item in res_json["organic"]:
                contexto += f"- {item['title']}: {item['snippet']}\n"
        
        return contexto if contexto else "Nenhum dado recente encontrado."
    except Exception as e:
        return f"Erro na API Serper: {e}"

# -----------------------------
# OUTRAS SKILLS (Voz e Imagem)
# -----------------------------

def process_image_to_base64(image_path):
    image_path = image_path.strip(' "')
    if not os.path.exists(image_path): return None
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def listen_mic():
    fs, seconds = 16000, 5
    print(f"\n🎤 Ouvindo...")
    rec = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
    sd.wait()
    sf.write("input_audio.wav", rec, fs)
    result = stt_model.transcribe("input_audio.wav", fp16=False)
    print(f"🎙️ Você: {result['text']}")
    return result["text"].strip()

async def speak_text(text):
    comm = edge_tts.Communicate(text, "pt-PT-RaquelNeural")
    await comm.save("response.mp3")
    pygame.mixer.music.load("response.mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy(): continue
    pygame.mixer.music.unload()

# -----------------------------
# CORE: OLLAMA
# -----------------------------
def query_ollama(user_input, image_base64=None, web_context=None):
    # Prompt focado em extrair dados dos resultados do Google
    system_prompt = (
        "Você é o Jarvis. Use o contexto abaixo para responder de forma factual.\n"
        "Se o contexto tiver jogos, horários ou nomes, liste-os claramente."
    )
    
    context_str = f"\n[DADOS DO GOOGLE]:\n{web_context}" if web_context else ""
    full_prompt = f"{system_prompt}\n{context_str}\n\nUtilizador: {user_input}\nJarvis:"

    payload = {
        "model": MODEL_NAME,
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": 0.1}
    }
    if image_base64: payload["images"] = [image_base64]
    
    try:
        # Aumentamos o timeout porque processar contexto web demora mais
        r = requests.post(OLLAMA_URL, json=payload, timeout=180)
        
        if r.status_code != 200:
            return f"Erro do Servidor Ollama: Status {r.status_code}"
            
        result = r.json().get("response")
        if result is None:
            return "Ollama retornou um objeto vazio. Verifique se o modelo 'gemma4' está carregado."
            
        return result.strip()
    except requests.exceptions.Timeout:
        return "O Jarvis demorou muito a processar. Tente uma pergunta mais simples."
    except Exception as e:
        return f"Erro inesperado: {str(e)}"
# -----------------------------
# LOOP PRINCIPAL
# -----------------------------
async def main_loop():
    print("\n" + "="*40)
    print("SISTEMA JARVIS v1.5.3 - Debug Ativo")
    print("="*40 + "\n")

    while True:
        raw_cmd = input("Tu: ").strip()
        if not raw_cmd: continue
        if raw_cmd.lower() == 'exit': break
        
        user_text, image_base64, web_context = raw_cmd, None, None
        
        # Verificação de comandos de imagem/mic (iguais ao anterior)
        # ...
        
        # Gatilho de Pesquisa Inteligente
        keywords = ["quem", "hoje", "jogos", "notícias", "preço", "futebol", "clima"]
        if any(k in user_text.lower() for k in keywords) and not raw_cmd.startswith("imagem:"):
            web_context = google_search(user_text)

        print("🧠 Jarvis a processar...")
        response = query_ollama(user_text, image_base64, web_context)
        
        # Proteção final contra o 'None' no print
        output = response if response else "Não consegui gerar uma resposta."
        print(f"\nJARVIS: {output}\n")

        # Áudio
        if "fala" in user_text.lower() or "voz" in user_text.lower():
             await speak_text(output)

if __name__ == "__main__":
    asyncio.run(main_loop())