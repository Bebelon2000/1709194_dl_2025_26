"""
Main FastAPI Application - Assistente IA Local Multiopen
Orquestra todos os serviços: LLM, STT, TTS e Pesquisa Web.
"""

import os
import sys
import json
import base64
import logging
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# --- Inicialização dos Serviços ---
# Import lazy para evitar erros se as dependências não estiverem instaladas
from llm_service import LLMService
from tts_service import TTSService
from search_service import SearchService
from emotion_service import EmotionService

# Carregar todos os serviços no arranque
from stt_service import STTService

llm_service = LLMService()
tts_service = TTSService()
search_service = SearchService()
emotion_service = EmotionService()

logger.info("A carregar modelo STT (isto pode demorar na primeira vez)...")
stt_service = STTService(model_size="small", device="auto")
logger.info("Modelo STT carregado com sucesso!")

# --- FastAPI App ---
app = FastAPI(
    title="Multiopen AI - Assistente Local",
    description="Assistente IA multimodal local usando Gemma4:e4b",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir ficheiros estáticos do frontend
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# --- Rotas ---

@app.get("/")
async def root():
    """Serve a página principal do frontend."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Multiopen AI Backend está a funcionar. Frontend não encontrado."}


@app.get("/health")
async def health_check():
    """Verificação de saúde do servidor."""
    return {
        "status": "ok",
        "model": "gemma4:e4b",
        "services": {
            "llm": True,
            "tts": True,
            "search": True,
            "stt": stt_service is not None,
        },
    }


# --- Chat ---

@app.post("/api/chat")
async def chat(
    message: str = Form(...),
    web_search: bool = Form(False),
    voice_response: bool = Form(False),
):
    """
    Endpoint de chat por texto.
    Opcionalmente realiza pesquisa web para enriquecer a resposta.
    """
    try:
        search_context = None

        if web_search:
            logger.info(f"Pesquisa web ativada para: {message}")
            search_context = search_service.search_and_format(message)

        import asyncio
        loop = asyncio.get_event_loop()
        
        # Correr em paralelo
        emotion_task = loop.run_in_executor(None, emotion_service.analyze_emotion, message)
        llm_task = loop.run_in_executor(None, llm_service.chat, message, search_context, voice_response)
        
        emotion, response = await asyncio.gather(emotion_task, llm_task)
        estado = emotion_service.get_natural_emotion(emotion)
        
        final_response = f"(thinking: o utilizador está {estado})\n\n{response}"

        return {
            "response": final_response,
            "web_search": web_search,
            "search_context": search_context,
        }

    except Exception as e:
        logger.error(f"Erro no chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/image")
async def chat_with_image(
    message: str = Form(...),
    image: UploadFile = File(...),
):
    """
    Endpoint de chat multimodal com imagem.
    """
    try:
        # Ler e converter imagem para base64
        image_bytes = await image.read()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        import asyncio
        loop = asyncio.get_event_loop()
        
        # Correr em paralelo
        emotion_task = loop.run_in_executor(None, emotion_service.analyze_emotion, message)
        llm_task = loop.run_in_executor(None, llm_service.chat_with_image, message, image_base64)

        emotion, response = await asyncio.gather(emotion_task, llm_task)
        estado = emotion_service.get_natural_emotion(emotion)
        
        final_response = f"(thinking: o utilizador está {estado})\n\n{response}"

        return {"response": final_response}

    except Exception as e:
        logger.error(f"Erro no chat com imagem: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Streaming Chat via WebSocket ---

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket para chat com streaming de resposta.
    Recebe JSON: {"message": "...", "web_search": false, "image": "base64..."}
    Envia tokens em tempo real.
    """
    await websocket.accept()
    logger.info("WebSocket conectado.")

    try:
        while True:
            # Receber mensagem
            data = await websocket.receive_text()
            payload = json.loads(data)

            message = payload.get("message", "")
            web_search = payload.get("web_search", False)
            voice_response = payload.get("voice_response", False)
            image_base64 = payload.get("image", None)

            # Pesquisa web se ativada
            search_context = None
            if web_search:
                search_context = search_service.search_and_format(message)
                await websocket.send_text(
                    json.dumps({"type": "search", "data": search_context})
                )

            # Preparar streaming
            if image_base64:
                stream = llm_service.chat_with_image_stream(message, image_base64, voice_response=voice_response)
            else:
                stream = llm_service.chat_stream(message, search_context, voice_response=voice_response)
                
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Executar análise de emoção e fetch do 1º token em paralelo
            emotion_task = loop.run_in_executor(None, emotion_service.analyze_emotion, message)
            first_token_task = loop.run_in_executor(None, next, stream, None)
            
            # 1. Espera apenas pela emoção (muito rápido) e envia imediatamente
            emotion = await emotion_task
            estado = emotion_service.get_natural_emotion(emotion)
            await websocket.send_text(
                json.dumps({"type": "token", "data": f"(thinking: o utilizador está {estado})\n\n"})
            )
            
            # 2. Agora espera pelo primeiro token do Ollama (que demorará mais um bocado)
            first_token = await first_token_task
            if first_token:
                await websocket.send_text(
                    json.dumps({"type": "token", "data": first_token})
                )

            # Enviar os restantes tokens
            def consume_stream(stream_gen, q_obj):
                for t in stream_gen:
                    loop.call_soon_threadsafe(q_obj.put_nowait, t)
                loop.call_soon_threadsafe(q_obj.put_nowait, None)

            q = asyncio.Queue()
            loop.run_in_executor(None, consume_stream, stream, q)
            
            while True:
                token = await q.get()
                if token is None:
                    break
                await websocket.send_text(
                    json.dumps({"type": "token", "data": token})
                )

            # Sinalizar fim da resposta
            await websocket.send_text(
                json.dumps({"type": "done"})
            )

    except WebSocketDisconnect:
        logger.info("WebSocket desconectado.")
    except Exception as e:
        logger.error(f"Erro no WebSocket: {e}")
        try:
            await websocket.send_text(
                json.dumps({"type": "error", "data": str(e)})
            )
        except Exception:
            pass


# --- Speech-to-Text ---

@app.post("/api/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    language: Optional[str] = Form(None),
):
    """
    Converte áudio para texto.
    Aceita ficheiros WAV, MP3, WebM, etc.
    """
    try:
        audio_bytes = await audio.read()

        # Determinar extensão do ficheiro a partir do nome original
        file_ext = ".webm"  # default do browser MediaRecorder
        if audio.filename:
            import os
            _, ext = os.path.splitext(audio.filename)
            if ext:
                file_ext = ext

        logger.info(f"STT: recebido ficheiro '{audio.filename}' ({len(audio_bytes)} bytes, ext={file_ext})")

        result = stt_service.transcribe(
            audio_bytes=audio_bytes,
            language=language,
            file_ext=file_ext,
        )

        return result

    except Exception as e:
        logger.error(f"Erro no STT: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Text-to-Speech ---

@app.post("/api/tts")
async def text_to_speech(
    text: str = Form(...),
    voice: str = Form("pt-PT-DuarteNeural"),
):
    """
    Converte texto para áudio MP3.
    """
    try:
        audio_bytes = await tts_service.synthesize_async(
            text=text,
            voice=voice,
        )

        return StreamingResponse(
            iter([audio_bytes]),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"},
        )

    except Exception as e:
        logger.error(f"Erro no TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tts/voices")
async def get_tts_voices():
    """Retorna as vozes TTS disponíveis."""
    return tts_service.get_voices()


# --- Pesquisa Web ---

@app.post("/api/search")
async def web_search(
    query: str = Form(...),
    max_results: int = Form(5),
):
    """
    Realiza pesquisa web e retorna resultados.
    """
    try:
        results = search_service.search(query, max_results)
        return {"results": results, "query": query}

    except Exception as e:
        logger.error(f"Erro na pesquisa: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Gestão de Conversa ---

@app.post("/api/chat/clear")
async def clear_chat():
    """Limpa o histórico de conversa."""
    llm_service.clear_history()
    return {"message": "Histórico limpo."}


@app.get("/api/chat/history")
async def get_chat_history():
    """Retorna o histórico de conversa."""
    return {"history": llm_service.get_history()}


# --- Inicialização ---

if __name__ == "__main__":
    import uvicorn

    logger.info("=" * 60)
    logger.info("  Multiopen AI - Assistente Local Multimodal")
    logger.info("  Modelo: Gemma4:e4b via Ollama")
    logger.info("  URL: http://localhost:8000")
    logger.info("=" * 60)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
