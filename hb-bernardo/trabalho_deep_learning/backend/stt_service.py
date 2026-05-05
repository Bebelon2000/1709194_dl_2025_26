"""
STT Service - Speech-to-Text usando faster-whisper.
Transcreve áudio para texto com suporte a português.
"""

import io
import os
import tempfile
import logging
import wave
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class STTService:
    """Serviço de transcrição de fala para texto usando faster-whisper."""

    def __init__(self, model_size: str = "small", device: str = "auto"):
        """
        Inicializa o modelo de transcrição.

        Args:
            model_size: Tamanho do modelo ('tiny', 'base', 'small', 'medium', 'large-v3')
            device: Dispositivo ('cuda', 'cpu', 'auto')
        """
        self.model_size = model_size
        self.model = None
        self.device = device
        self._load_model()

    def _load_model(self):
        """Carrega o modelo faster-whisper."""
        try:
            logger.info(
                f"A carregar modelo faster-whisper '{self.model_size}' no dispositivo '{self.device}'..."
            )

            # Configurar compute type baseado no dispositivo
            if self.device == "auto":
                try:
                    self.model = WhisperModel(
                        self.model_size,
                        device="cuda",
                        compute_type="float16",
                    )
                    self.device = "cuda"
                    logger.info("Modelo carregado na GPU (CUDA) com float16.")
                except Exception:
                    logger.info("CUDA não disponível, a usar CPU...")
                    self.model = WhisperModel(
                        self.model_size,
                        device="cpu",
                        compute_type="int8",
                    )
                    self.device = "cpu"
                    logger.info("Modelo carregado na CPU com int8.")
            elif self.device == "cuda":
                self.model = WhisperModel(
                    self.model_size,
                    device="cuda",
                    compute_type="float16",
                )
            else:
                self.model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8",
                )

            logger.info(f"Modelo faster-whisper '{self.model_size}' carregado com sucesso.")

        except Exception as e:
            logger.error(f"Erro ao carregar modelo faster-whisper: {e}")
            raise

    def transcribe(self, audio_bytes: bytes, language: str = None, file_ext: str = ".webm") -> dict:
        """
        Transcreve áudio para texto.

        Args:
            audio_bytes: Bytes do ficheiro de áudio (WAV, MP3, WebM, etc.)
            language: Código do idioma (ex: 'pt'). Se None, deteta automaticamente.
            file_ext: Extensão do ficheiro de áudio (ex: '.webm', '.wav').

        Returns:
            dict com 'text' (texto transcrito) e 'language' (idioma detetado)
        """
        if self.model is None:
            raise Exception("Modelo não carregado.")

        temp_path = None
        try:
            logger.info(f"A transcrever áudio: {len(audio_bytes)} bytes, extensão={file_ext}")

            # Gravar bytes num ficheiro temporário com a extensão correta
            with tempfile.NamedTemporaryFile(
                suffix=file_ext, delete=False
            ) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name

            # Transcrever
            segments, info = self.model.transcribe(
                temp_path,
                language=language,
                vad_filter=True,
                vad_parameters=dict(
                    threshold=0.3,
                    min_silence_duration_ms=1000,
                    speech_pad_ms=400,
                    min_speech_duration_ms=250,
                ),
                beam_size=5,
            )

            # Concatenar todos os segmentos
            text = " ".join([segment.text.strip() for segment in segments])

            result = {
                "text": text.strip(),
                "language": info.language,
                "language_probability": round(info.language_probability, 2),
                "duration": round(info.duration, 2),
            }

            logger.info(
                f"Transcrição concluída: idioma={result['language']} "
                f"(prob={result['language_probability']}), "
                f"duração={result['duration']}s"
            )

            return result

        except Exception as e:
            logger.error(f"Erro na transcrição: {e}")
            raise Exception(f"Erro ao transcrever áudio: {str(e)}")

        finally:
            # Limpar ficheiro temporário
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def get_info(self) -> dict:
        """Retorna informações sobre o modelo carregado."""
        return {
            "model_size": self.model_size,
            "device": self.device,
            "loaded": self.model is not None,
        }
