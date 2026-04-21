import requests
import re
import sys
from datetime import datetime
from tavily import TavilyClient

# --- CONFIGURAÇÃO ---
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma4" 
TAVILY_API_KEY = "SUA_CHAVE_AQUI"

tavily = TavilyClient(api_key=TAVILY_API_KEY)

def clean_user_input(text):
    """Limpa ruídos e prefixos redundantes."""
    cleaned = re.sub(r"^(Tu:|Olá|ola|Oi|oi|,|\s)+", "", text, flags=re.IGNORECASE)
    return cleaned.strip()

def generate_search_query(user_text):
    """Prompt ultra-curto para transformar a pergunta em keywords em milissegundos."""
    prompt = f"Short search query (max 3 words) for: {user_text}\nQuery:"
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 8, "temperature": 0} # Mínimo de tokens possível
        }, timeout=10)
        query = response.json().get("response", "").strip().replace('"', '')
        return query if len(query) > 2 else user_text
    except:
        return user_text

def web_research(optimized_query):
    """Busca optimizada com contexto reduzido para performance."""
    print(f"🔍 Busca Optimizada: {optimized_query}")
    try:
        search = tavily.search(query=optimized_query, search_depth="basic", max_results=3)
        context = ""
        for r in search['results']:
            # Reduzimos para 1000 caracteres para acelerar o prefill da GPU
            content = r['content'][:1000].replace('\n', ' ')
            context += f"\n[Fonte: {r['url']}] {content}\n"
        return context
    except Exception as e:
        return f"Erro web: {e}"

def solve_streaming(user_input):
    """Executa o RAG com streaming para resposta instantânea."""
    start_time = datetime.now()
    
    clean_text = clean_user_input(user_input)
    search_query = generate_search_query(clean_text)
    context = web_research(search_query)
    
    today = datetime.now().strftime("%d/%m/%Y")
    final_prompt = f"Data: {today}. Contexto: {context}\n\nPergunta: {clean_text}\n\nResposta (curta e direta):"

    print("\nOllama: ", end="", flush=True)
    
    try:
        # Ativamos o streaming para o utilizador não ficar à espera
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL_NAME,
            "prompt": final_prompt,
            "stream": True, # <--- A CHAVE PARA A PERFORMANCE PERCEBIDA
            "options": {
                "temperature": 0.1, 
                "num_ctx": 4096 # Reduzido para ser 2x mais rápido que 8k
            }
        }, stream=True, timeout=120)

        full_response = ""
        for line in response.iter_lines():
            if line:
                import json
                chunk = json.loads(line.decode('utf-8'))
                token = chunk.get("response", "")
                full_response += token
                print(token, end="", flush=True)
                if chunk.get("done"):
                    break
        
        duration = (datetime.now() - start_time).total_seconds()
        print(f"\n\n[Tempo total: {duration:.2f}s]")
        return full_response

    except Exception as e:
        print(f"\nErro: {e}")

def main():
    print(f"--- RAG HIGH PERFORMANCE (Gemma 4 + Tavily) ---")
    while True:
        text = input("\nTu: ").strip()
        if text.lower() in ['sair', 'exit']: break
        solve_streaming(text)
        print("-" * 40)

if __name__ == "__main__":
    main()