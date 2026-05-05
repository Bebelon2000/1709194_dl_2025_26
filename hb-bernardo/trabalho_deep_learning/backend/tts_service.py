"""
TTS Service - Text-to-Speech usando edge-tts.
Sintetiza voz natural com vozes neurais da Microsoft em português.
"""

import asyncio
import io
import logging
import edge_tts

logger = logging.getLogger(__name__)

# Vozes disponíveis em português
AVAILABLE_VOICES = {
    "pt-PT-DuarteNeural": "Duarte (Português PT - Masculino)",
    "pt-PT-RaquelNeural": "Raquel (Português PT - Feminino)",
    "pt-BR-AntonioNeural": "António (Português BR - Masculino)",
    "pt-BR-FranciscaNeural": "Francisca (Português BR - Feminino)",
}

DEFAULT_VOICE = "pt-PT-DuarteNeural"


class TTSService:
    """Serviço de síntese de voz usando edge-tts."""

    def __init__(self, default_voice: str = DEFAULT_VOICE):
        """
        Inicializa o serviço TTS.

        Args:
            default_voice: Voz padrão para síntese.
        """
        self.default_voice = default_voice
        logger.info(f"TTS Service inicializado com voz padrão: {default_voice}")

    async def synthesize_async(
        self,
        text: str,
        voice: str = None,
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
    ) -> bytes:
        """
        Sintetiza texto em áudio MP3 (assíncrono).

        Args:
            text: Texto para sintetizar.
            voice: Nome da voz (ex: 'pt-PT-DuarteNeural').
            rate: Velocidade da fala (ex: '+10%', '-20%').
            volume: Volume (ex: '+10%', '-10%').
            pitch: Tom da voz (ex: '+5Hz', '-5Hz').

        Returns:
            Bytes do áudio MP3.
        """
        if not text or not text.strip():
            raise ValueError("Texto vazio para síntese.")

        voice = voice or self.default_voice

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                volume=volume,
                pitch=pitch,
            )

            # Recolher todos os bytes de áudio
            audio_buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])

            audio_bytes = audio_buffer.getvalue()

            if len(audio_bytes) == 0:
                raise Exception("Nenhum áudio gerado.")

            logger.info(
                f"Áudio sintetizado: {len(audio_bytes)} bytes, voz={voice}"
            )

            return audio_bytes

        except Exception as e:
            logger.error(f"Erro na síntese TTS: {e}")
            raise Exception(f"Erro ao sintetizar voz: {str(e)}")

    def synthesize(
        self,
        text: str,
        voice: str = None,
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
    ) -> bytes:
        """
        Sintetiza texto em áudio MP3 (síncrono).
        Wrapper para uso em contextos não-async.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Se já há um loop a correr, criar uma nova task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(
                        asyncio.run,
                        self.synthesize_async(text, voice, rate, volume, pitch)
                    ).result()
                return result
            else:
                return loop.run_until_complete(
                    self.synthesize_async(text, voice, rate, volume, pitch)
                )
        except RuntimeError:
            return asyncio.run(
                self.synthesize_async(text, voice, rate, volume, pitch)
            )

    def get_voices(self) -> dict:
        """Retorna as vozes disponíveis."""
        return AVAILABLE_VOICES.copy()

    def set_default_voice(self, voice: str):
        """Define a voz padrão."""
        if voice in AVAILABLE_VOICES:
            self.default_voice = voice
            logger.info(f"Voz padrão alterada para: {voice}")
        else:
            raise ValueError(
                f"Voz '{voice}' não encontrada. Disponíveis: {list(AVAILABLE_VOICES.keys())}"
            )
