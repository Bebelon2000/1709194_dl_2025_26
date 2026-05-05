"""
Emotion Service - Analisa a emoção do utilizador no texto usando um modelo de classificação.
"""

import logging
from transformers import pipeline
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

class EmotionService:
    def __init__(self):
        logger.info("A inicializar Emotion Service (pode demorar a descarregar o modelo na primeira vez)...")
        try:
            self.sentiment_pipeline = pipeline(
                "text-classification",
                model="j-hartmann/emotion-english-distilroberta-base",
                top_k=1
            )
            logger.info("Emotion Service inicializado com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao inicializar Emotion Service: {e}")
            self.sentiment_pipeline = None

    def analyze_emotion(self, text: str) -> str:
        """
        Analisa a emoção do texto e retorna em português.
        """
        if not self.sentiment_pipeline or not text.strip():
            return "neutro"

        try:
            # Traduzir para inglês pois o modelo funciona melhor em inglês
            translated = GoogleTranslator(source='auto', target='en').translate(text)
            
            result = self.sentiment_pipeline(translated)[0][0]
            
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
        except Exception as e:
            logger.error(f"Erro na análise de emoção: {e}")
            return "neutro"

    def get_natural_emotion(self, emotion: str) -> str:
        return {
            "tristeza": "triste",
            "alegria": "feliz",
            "raiva": "zangado",
            "medo": "com medo",
            "surpresa": "surpreendido",
            "nojo": "enojado",
            "neutro": "neutro"
        }.get(emotion, emotion)
