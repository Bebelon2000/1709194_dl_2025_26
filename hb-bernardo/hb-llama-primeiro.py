import requests
import threading
from queue import Queue

# =========================
# CONFIG
# =========================
OLLAMA_URL = "http://localhost:11434"
MODEL = "llama3"

# =========================
# MEMÓRIA
# =========================
chat_history = []
MAX_HISTORY = 6

# =========================
# CONTROLE
# =========================
model_ready = threading.Event()
stop_chat = threading.Event()
input_queue = Queue()

# =========================
# FUNÇÃO DE CHAT
# =========================
def gerar_resposta(user_input):
    global chat_history

    chat_history.append({
        "role": "user",
        "content": user_input
    })

    chat_history = chat_history[-MAX_HISTORY:]

    payload = {
        "model": MODEL,
        "messages": chat_history,
        "stream": False
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=300)

    if response.status_code != 200:
        return f"Erro: {response.text}"

    data = response.json()
    resposta = data["message"]["content"]

    chat_history.append({
        "role": "assistant",
        "content": resposta
    })

    chat_history = chat_history[-MAX_HISTORY:]
    return resposta

# =========================
# INIT DO MODELO
# =========================
def inicializar_modelo():
    try:
        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": "Responda apenas com: pronto"
                }
            ],
            "stream": False
        }

        response = requests.post(OLLAMA_URL, json=payload, timeout=300)
        if response.status_code == 200:
            print("Modelo inicializado com sucesso.")
            model_ready.set()
        else:
            print(f"Erro ao inicializar modelo: {response.text}")
    except Exception as e:
        print(f"Erro ao inicializar modelo: {e}")

# =========================
# LOOP DE CONVERSA
# =========================
def chat_loop():
    print("\n🔥 Chat com LLaMA3 via Ollama (local)\n")

    model_ready.wait()
    print("Modelo pronto. Pode conversar.\n")

    while not stop_chat.is_set():
        user_input = input("Você: ")

        if user_input.lower() in ["sair", "exit", "quit"]:
            stop_chat.set()
            break

        user_input = (
            "Agora você só fala estritamente em português, mesmo que eu fale em inglês. "
            "Responda apenas em português. " + user_input
        )

        resposta = gerar_resposta(user_input)
        print("AI:", resposta)

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    thread_init = threading.Thread(target=inicializar_modelo)
    thread_chat = threading.Thread(target=chat_loop)

    thread_init.start()
    thread_chat.start()

    thread_init.join()
    thread_chat.join()