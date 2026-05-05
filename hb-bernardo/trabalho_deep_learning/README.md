# Multiopen AI - Assistente Local Multimodal

Assistente de inteligencia artificial multimodal com backend FastAPI, frontend web e modelo local **Gemma4:e4b** via Ollama. O sistema combina chat, voz, visao, pesquisa web, sintese de fala e uma camada de analise emocional do texto do utilizador.

**Trabalho de Deep Learning - 2026**

> Nota de localidade: o LLM e o STT correm localmente. A pesquisa web usa DuckDuckGo, o TTS usa `edge-tts` e a analise emocional usa traducao via `deep-translator`/GoogleTranslator antes do classificador, por isso essas partes podem depender de rede.

---

## Funcionalidades

| Funcionalidade | Tecnologia | Descricao |
|---|---|---|
| Chat inteligente | Gemma4:e4b via Ollama | Modelo LLM local multimodal com historico de conversa e system prompt em pt-PT |
| Analise emocional | Transformers + DistilRoBERTa | Deteta a emocao provavel do texto do utilizador e acrescenta um prefixo emocional a resposta |
| Comando de voz | faster-whisper | Transcricao de fala para texto em portugues com VAD e CUDA quando disponivel |
| Resposta por voz | edge-tts | Sintese de voz neural em PT-PT e PT-BR |
| Compreensao de imagem | Gemma4:e4b Vision | Analise de imagens enviadas pelo frontend em base64 |
| Pesquisa web | DuckDuckGo | Pesquisa opcional para enriquecer respostas com contexto atualizado |
| Interface web | HTML/CSS/JS + FastAPI | Chat responsivo com sidebar, WebSocket, upload de imagem, gravacao de voz e TTS |

---

## Arquitetura

```text
Frontend (HTML/CSS/JS)
  - Chat, voz, imagem, pesquisa web, seletor TTS
  - WebSocket para streaming de texto
  - REST para STT, TTS, imagens e fallback de chat
        |
        v
Backend (FastAPI)
  - main.py orquestra os servicos
  - llm_service.py comunica com Ollama
  - emotion_service.py analisa a emocao do utilizador
  - stt_service.py transcreve audio
  - tts_service.py gera MP3
  - search_service.py pesquisa e formata contexto web
        |
        v
Ollama + Gemma4:e4b
```

No chat por texto, o backend executa a analise emocional e a chamada ao LLM em paralelo. No streaming por WebSocket, a emocao e enviada primeiro como prefixo no formato:

```text
(thinking: o utilizador esta neutro)
```

Depois seguem os tokens gerados pelo Gemma4:e4b.

---

## Pre-requisitos

- Windows 10/11
- Python 3.9+
- Ollama instalado e com o modelo `gemma4:e4b`
- GPU NVIDIA com CUDA recomendada para STT mais rapido
- Ligacao a internet para pesquisa web, `edge-tts`, traducao da analise emocional e descarregamento inicial de modelos

---

## Instalacao

1. Abrir a pasta do projeto:

   ```powershell
   cd trabalho_deep_learning
   ```

2. Criar ambiente virtual, se ainda nao existir:

   ```powershell
   python -m venv venv
   ```

3. Instalar dependencias:

   ```powershell
   .\venv\Scripts\pip.exe install -r backend\requirements.txt
   ```

4. Verificar o Ollama:

   ```powershell
   ollama list
   ```

   A lista deve incluir `gemma4:e4b`.

---

## Como Executar

### Opcao 1: Script automatico

Fazer duplo clique em `start.bat`.

### Opcao 2: Manual

```powershell
.\venv\Scripts\activate
python backend\main.py
```

A aplicacao fica disponivel em:

```text
http://localhost:8000
```

---

## Como Usar

### Chat por texto

Escreve uma mensagem e prime `Enter` ou usa o botao de envio. Quando o WebSocket esta disponivel, a resposta aparece em streaming.

### Comando de voz

Carrega no botao do microfone, fala, e carrega novamente para parar. O audio e enviado para `/api/stt`; o texto transcrito aparece no input para revisao antes do envio.

### Envio de imagem

Usa o botao de imagem, escolhe um ficheiro e envia uma pergunta. O frontend usa `/api/chat/image`, que passa a imagem ao Gemma4:e4b em base64.

### Pesquisa web

Ativa o toggle "Pesquisa Web" na sidebar. Quando ativo, o backend chama DuckDuckGo e injeta os resultados formatados no prompt do LLM.

### Resposta por voz

Usa "Ouvir" numa resposta ou ativa "Resposta por Voz" para TTS automatico. A voz e escolhida no seletor da sidebar.

### Analise emocional

Nao precisa de configuracao na interface. O backend analisa automaticamente o texto do utilizador, tenta traduzir para ingles e classifica em emocoes como alegria, tristeza, raiva, medo, surpresa, nojo ou neutro. Se a analise falhar, o sistema usa `neutro`.

---

## Endpoints Principais

| Metodo | Rota | Funcao |
|---|---|---|
| GET | `/` | Serve o frontend |
| GET | `/health` | Estado basico dos servicos |
| POST | `/api/chat` | Chat por texto via REST, com pesquisa opcional |
| POST | `/api/chat/image` | Chat multimodal com imagem |
| WS | `/ws/chat` | Chat por texto com streaming |
| POST | `/api/stt` | Audio para texto |
| POST | `/api/tts` | Texto para audio MP3 |
| GET | `/api/tts/voices` | Lista de vozes TTS |
| POST | `/api/search` | Pesquisa web direta |
| POST | `/api/chat/clear` | Limpa historico |
| GET | `/api/chat/history` | Devolve historico |

---

## Stack Tecnologico

| Componente | Biblioteca/Servico | Versao |
|---|---|---|
| LLM | Gemma4:e4b via Ollama | - |
| Backend | FastAPI | 0.115.12 |
| Servidor ASGI | Uvicorn | 0.34.2 |
| STT | faster-whisper | 1.1.1 |
| TTS | edge-tts | 7.2.8 |
| Pesquisa | duckduckgo-search | 7.5.3 |
| Analise emocional | transformers | >= 4.35.0 |
| Traducao emocional | deep-translator | >= 1.11.4 |
| Tensor backend | torch | >= 2.0.0 |
| Frontend | HTML/CSS/JS puro | - |

---

## Estrutura do Projeto

```text
trabalho_deep_learning/
├── backend/
│   ├── main.py              # FastAPI app principal e rotas
│   ├── llm_service.py       # Ollama/Gemma4:e4b, texto, streaming e imagem
│   ├── emotion_service.py   # Analise emocional do texto do utilizador
│   ├── stt_service.py       # Speech-to-Text com faster-whisper
│   ├── tts_service.py       # Text-to-Speech com edge-tts
│   ├── search_service.py    # Pesquisa DuckDuckGo e formatacao RAG
│   └── requirements.txt     # Dependencias Python
├── frontend/
│   ├── index.html           # Interface principal
│   ├── style.css            # Estilos e responsividade
│   └── app.js               # Logica do chat, voz, imagem, WebSocket e TTS
├── start.bat                # Arranque automatico em Windows
└── README.md                # Documentacao do projeto
```

---

## Conceitos de Deep Learning Utilizados

1. **Transformers**: Gemma4:e4b e o classificador emocional usam arquiteturas baseadas em Transformers.
2. **Multimodal Learning**: o Gemma4:e4b processa texto e imagem.
3. **Speech Recognition**: faster-whisper usa modelos Whisper otimizados via CTranslate2.
4. **Neural TTS**: edge-tts gera fala neural natural.
5. **Emotion Classification**: `j-hartmann/emotion-english-distilroberta-base` classifica emocoes depois de traducao para ingles.
6. **Retrieval-Augmented Generation**: os resultados DuckDuckGo sao injetados como contexto quando a pesquisa web esta ativa.

---

## Licenca

Projeto academico - Instituto Politecnico da Guarda, 2026
