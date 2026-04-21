import requests
import json
import base64
import os
from transformers import pipeline
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor
from PIL import Image # Apenas para verificar se o arquivo é uma imagem válida

# -----------------------------
# CONFIG
# -----------------------------
# Mudamos para /api/generate pois é mais fácil lidar com imagens e prompts únicos
OLLAMA_URL = "http://localhost:11434/api/generate" 
MODEL_NAME = "gemma4" # Certifique-se que o Gemma 4 está carregado no Ollama

# -----------------------------
# SENTIMENT PIPELINE (Mantido)
# -----------------------------
print("Carregando pipeline de sentimento...")
try:
    sentiment_pipeline = pipeline(
        "text-classification",
        model="j-hartmann/emotion-english-distilroberta-base",
        top_k=1,
        device=-1 # Força CPU para poupar VRAM da RTX 5070 para o Gemma 4
    )
except Exception as e:
    print(f"Erro ao carregar sentimento (talvez falte instalar transformers/torch): {e}")
    sentiment_pipeline = None

# -----------------------------
# FUNÇÕES DE UTILIDADE
# -----------------------------

def analyze_sentiment(text):
    """Analisa o sentimento do texto (Mantido)."""
    if not sentiment_pipeline or not text:
        return "neutro"
    
    try:
        translated = GoogleTranslator(source='auto', target='en').translate(text)
        result = sentiment_pipeline(translated)[0][0]
        emotion = result["label"].lower()
        score = result["score"]
        if score < 0.4: emotion = "neutral"
        
        mapping = {
            "joy": "alegria", "sadness": "tristeza", "anger": "raiva",
            "fear": "medo", "surprise": "surpresa", "disgust": "nojo", "neutral": "neutro"
        }
        return mapping.get(emotion, "neutro")
    except:
        return "neutro"

def emotion_to_natural(e):
    """Converte emoção para adjetivo natural (Mantido)."""
    return {
        "tristeza": "triste", "alegria": "feliz", "raiva": "zangado",
        "medo": "com medo", "surprise": "surpreendido", "nojo": "enojado", "neutro": "neutro"
    }.get(e, e)

# -----------------------------
# NOVA FUNÇÃO: PROCESSAR IMAGEM
# -----------------------------
def process_image_to_base64(image_path):
    """Lê uma imagem local e converte para Base64 para o Ollama."""
    image_path = image_path.strip(' "') # Remove aspas extras se o usuário arrastar o arquivo
    if not os.path.exists(image_path):
        print(f"❌ Erro: Arquivo não encontrado em {image_path}")
        return None
    
    try:
        # Verifica se é uma imagem válida antes de converter
        with Image.open(image_path) as img:
            img.verify() 
        
        # Converte para Base64
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return encoded_string
    except Exception as e:
        print(f"❌ Erro ao processar imagem: {e}")
        return None

# -----------------------------
# OLLAMA FUNCTION (Atualizada para Visão)
# -----------------------------
def query_ollama(user_input, emotion=None, image_base64=None):
    """Envia prompt (e imagem opcional) para o Gemma 4 via Ollama."""
    
    # Criando o Prompt System/Contexto
    system_prompt = "Você é um assistente pessoal inteligente e empático. Hoje é dia 21/04/2026."
    
    if image_base64 and user_input:
        full_prompt = f"{system_prompt}\nO utilizador enviou uma imagem. Analise-a e responda à pergunta: {user_input}"
    elif image_base64:
        full_prompt = f"{system_prompt}\nAnalise e descreva esta imagem em pormenor."
    elif emotion:
        full_prompt = f"{system_prompt}\nUtilizador está {emotion_to_natural(emotion)}. Responda de forma empática a: {user_input}"
    else:
        full_prompt = f"{system_prompt}\nResponda a: {user_input}"

    # Montando o Payload para a API /api/generate
    payload = {
        "model": MODEL_NAME,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.7
        }
    }

    # Adiciona a imagem ao payload se ela existir
    if image_base64:
        payload["images"] = [image_base64]

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120) # Aumentado timeout para visão
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"Erro ao conectar ao Ollama: {e}"

# -----------------------------
# CHAT LOOP (Atualizado)
# -----------------------------
# ... (mantenha o resto do script igual)

def chat():
    print("\n==========================================")
    print("SISTEMA JARVIS v1.2 - Visão (Fix de Caminhos)")
    print("Hoje é 21/04/2026")
    print("------------------------------------------")
    print("Dica: Se o caminho tiver espaços, o script agora resolve!")
    print("Como usar: imagem: C:\\caminho com espaços\\foto.png O que é isto?")
    print("==========================================\n")

    with ThreadPoolExecutor(max_workers=2) as executor:
        while True:
            raw_input = input("Tu: ").strip()

            if not raw_input: continue
            if raw_input.lower() == "exit": break

            image_base64 = None
            user_text = raw_input
            img_path = None

            # LÓGICA MELHORADA PARA DETECTAR IMAGEM
            if raw_input.lower().startswith("imagem:"):
                # Remove o prefixo "imagem:"
                content = raw_input[7:].strip()
                
                # Se o usuário colocar o caminho entre aspas (comum ao arrastar arquivos)
                if content.startswith('"'):
                    end_quote = content.find('"', 1)
                    img_path = content[1:end_quote]
                    user_text = content[end_quote+1:].strip()
                else:
                    # Se não houver aspas, vamos procurar extensões comuns
                    # e assumir que o texto da pergunta vem depois delas
                    terminacoes = [".png", ".jpg", ".jpeg", ".webp"]
                    found_ext = False
                    for ext in terminacoes:
                        if ext in content.lower():
                            pos = content.lower().find(ext) + len(ext)
                            img_path = content[:pos].strip()
                            user_text = content[pos:].strip()
                            found_ext = True
                            break
                    
                    if not found_ext:
                        # Fallback: pega a primeira palavra (se não houver extensão clara)
                        parts = content.split(" ", 1)
                        img_path = parts[0]
                        user_text = parts[1] if len(parts) > 1 else "Descreva a imagem."

                print(f"📸 Processando imagem em: {img_path}")
                image_base64 = process_image_to_base64(img_path)
                
                if not image_base64:
                    print("❌ Falha na leitura. Verifique se o caminho está correto.")
                    continue

                if not user_text: 
                    user_text = "Descreva esta imagem em detalhe."

            # Execução (Sentimento + LLM)
            future_sentiment = executor.submit(analyze_sentiment, user_text)
            future_llm = executor.submit(query_ollama, user_text, None, image_base64)

            emotion = future_sentiment.result()
            response = future_llm.result()
            estado = emotion_to_natural(emotion)

            print(f"\nResposta:")
            if image_base64:
                 print(f"(thinking: analisando imagem e respondendo com base no sentimento {estado}...)")
            else:
                 print(f"(thinking: sentimento detectado -> {estado})")
            print(f"\n{response}\n")

# ... (o resto permanece igual)

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    # Pequeno ajuste para garantir que o Windows lide bem com UTF-8 no terminal
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    chat()