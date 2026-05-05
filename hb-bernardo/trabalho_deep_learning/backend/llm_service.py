"""
LLM Service - Comunicação com Ollama (Gemma4:e4b)
Suporta chat de texto, visão multimodal e integração com pesquisa web.
"""

import ollama
import base64
import logging
from datetime import datetime
from typing import List, Dict, Optional, Generator

logger = logging.getLogger(__name__)

MODEL_NAME = "gemma4:e4b"

SYSTEM_PROMPT_TEMPLATE = """Tens como nome Multiopen AI. És um assistente de IA avançado e prestável que funciona localmente.

INFORMAÇÃO DE CONTEXTO ATUAL:
- Data e hora atual: {current_datetime}
- Fuso horário: Europa/Lisboa (Portugal)
- Localização do utilizador: Portugal

=== REGRAS DE ALINHAMENTO ===

REGRA 1 — IDENTIDADE: O teu nome é Multiopen AI. És um assistente de inteligência artificial local e multimodal. Não finjas ser humano. Se te perguntarem quem és, apresenta-te como Multiopen AI.

REGRA 2 — IDIOMA: Responde SEMPRE em português europeu (pt-PT), salvo se o utilizador pedir explicitamente outro idioma. Usa vocabulário e expressões de Portugal (ex: "telemóvel" e não "celular", "ecrã" e não "tela").

REGRA 3 — CONCISÃO E CLAREZA: Sê direto e objetivo nas respostas. Evita repetições e textos desnecessariamente longos. Quando a pergunta for simples, dá uma resposta curta. Quando for complexa, estrutura a resposta com tópicos ou passos numerados.

REGRA 4 — TEMPORALIDADE: Quando o utilizador perguntar sobre horas, datas, dias da semana ou qualquer informação temporal, usa a data/hora atual fornecida acima como referência para dar uma resposta precisa e direta. Nunca digas que não sabes a hora ou a data.

REGRA 5 — PESQUISA WEB: Quando te forem fornecidos resultados de pesquisa web, usa-os para complementar a tua resposta com informação atualizada. Cita as fontes quando relevante. Não inventes informação que não esteja nos resultados — se os resultados não cobrirem a pergunta, diz o que encontraste e o que não foi possível confirmar.

REGRA 6 — ANÁLISE DE IMAGENS: Quando receberes uma imagem, analisa-a de forma detalhada e útil. Descreve o que vês com precisão. Se o utilizador fizer uma pergunta específica sobre a imagem, foca a tua resposta nessa questão em vez de descrever tudo.

REGRA 7 — SEGURANÇA E ÉTICA: Recusa pedidos que envolvam gerar conteúdo ilegal, perigoso, discriminatório ou que viole a privacidade de terceiros. Explica o motivo da recusa de forma educada e breve.

REGRA 8 — FORMATAÇÃO: Usa markdown nas respostas quando adequado (negrito, listas, blocos de código, etc.) para melhorar a legibilidade. Para código, indica sempre a linguagem no bloco de código. Para respostas simples e curtas, não uses formatação desnecessária.

REGRA 9 — HONESTIDADE: Se não souberes a resposta ou não tiveres certeza, admite-o honestamente em vez de inventar. Sugere alternativas, como ativar a pesquisa web para obter informação atualizada.

REGRA 10 — TOM CONVERSACIONAL: Mantém um tom amigável, natural e profissional. Sê prestável sem ser excessivamente formal. Adapta o nível de detalhe ao contexto — uma conversa casual merece um tom leve, uma questão técnica merece rigor."""


class LLMService:
    """Serviço de comunicação com o modelo Gemma4:e4b via Ollama."""

    def __init__(self):
        self.model = MODEL_NAME
        self.conversation_history: List[Dict] = []
        self._verify_model()

    def _verify_model(self):
        """Verifica se o modelo está disponível no Ollama."""
        try:
            models = ollama.list()
            model_names = [m.model for m in models.models]
            # Check for partial match
            found = any(self.model in name for name in model_names)
            if found:
                logger.info(f"Modelo {self.model} encontrado no Ollama.")
            else:
                logger.warning(
                    f"Modelo {self.model} não encontrado. Modelos disponíveis: {model_names}"
                )
        except Exception as e:
            logger.error(f"Erro ao verificar modelo: {e}")

    def _build_messages(
        self,
        user_message: str,
        images: Optional[List[str]] = None,
        search_context: Optional[str] = None,
        use_history: bool = True,
        voice_response: bool = False,
    ) -> List[Dict]:
        """Constrói a lista de mensagens para o Ollama."""
        # Gerar system prompt com data/hora atual
        now = datetime.now()
        current_dt = now.strftime("%A, %d de %B de %Y, %H:%M:%S")
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(current_datetime=current_dt)
        
        messages = [{"role": "system", "content": system_prompt}]

        # Adicionar histórico de conversa
        if use_history and self.conversation_history:
            messages.extend(self.conversation_history[-20:])  # Últimas 20 mensagens

        # Construir mensagem do utilizador
        content = user_message

        if search_context:
            content = (
                f"O utilizador perguntou: {user_message}\n\n"
                f"Aqui estão os resultados de pesquisa web relevantes:\n"
                f"{search_context}\n\n"
                f"Usa estes resultados para dar uma resposta completa e atualizada. "
                f"Cita as fontes quando relevante."
            )
            
        if voice_response:
            content += "\n\n[INSTRUÇÃO DO SISTEMA: Responde APENAS de forma falada e natural como se fosses um humano ao telefone. NUNCA menciones que és uma inteligência artificial baseada em texto, que não tens áudio ou que não podes emitir voz. Age 100% como se tivesses voz e estivesses a falar agora mesmo com o utilizador.]"

        msg = {"role": "user", "content": content}
        if images:
            msg["images"] = images

        messages.append(msg)
        return messages

    def chat(
        self,
        user_message: str,
        search_context: Optional[str] = None,
        voice_response: bool = False,
        use_history: bool = True,
    ) -> str:
        """
        Envia mensagem para o modelo e retorna a resposta completa.
        """
        try:
            messages = self._build_messages(
                user_message=user_message,
                search_context=search_context,
                voice_response=voice_response,
                use_history=use_history,
            )

            response = ollama.chat(model=self.model, messages=messages)

            assistant_message = response.message.content

            # Guardar no histórico
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append(
                {"role": "assistant", "content": assistant_message}
            )

            return assistant_message

        except Exception as e:
            logger.error(f"Erro no chat: {e}")
            raise Exception(f"Erro ao comunicar com o modelo: {str(e)}")

    def chat_stream(
        self,
        user_message: str,
        search_context: Optional[str] = None,
        voice_response: bool = False,
        use_history: bool = True,
    ) -> Generator[str, None, None]:
        """
        Envia mensagem e retorna um gerador com os tokens em streaming.
        """
        try:
            messages = self._build_messages(
                user_message=user_message,
                search_context=search_context,
                voice_response=voice_response,
                use_history=use_history,
            )

            full_response = ""
            stream = ollama.chat(model=self.model, messages=messages, stream=True)

            for chunk in stream:
                token = chunk.message.content
                full_response += token
                yield token

            # Guardar no histórico
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append(
                {"role": "assistant", "content": full_response}
            )

        except Exception as e:
            logger.error(f"Erro no chat stream: {e}")
            raise Exception(f"Erro ao comunicar com o modelo: {str(e)}")

    def chat_with_image(
        self,
        user_message: str,
        image_base64: str,
        voice_response: bool = False,
        use_history: bool = True,
    ) -> str:
        """
        Analisa uma imagem juntamente com o texto (Multimodal).
        """
        try:
            messages = self._build_messages(
                user_message=user_message,
                images=[image_base64],
                use_history=use_history,
                voice_response=voice_response,
            )

            response = ollama.chat(model=self.model, messages=messages)

            assistant_message = response.message.content

            # Guardar no histórico (sem imagem para poupar memória)
            self.conversation_history.append(
                {"role": "user", "content": f"[Imagem enviada] {user_message}"}
            )
            self.conversation_history.append(
                {"role": "assistant", "content": assistant_message}
            )

            return assistant_message

        except Exception as e:
            logger.error(f"Erro no chat com imagem: {e}")
            raise Exception(f"Erro ao processar imagem: {str(e)}")

    def chat_with_image_stream(
        self,
        user_message: str,
        image_base64: str,
        voice_response: bool = False,
        use_history: bool = True,
    ) -> Generator[str, None, None]:
        """
        Multimodal com streaming de resposta.
        """
        try:
            messages = self._build_messages(
                user_message=user_message,
                images=[image_base64],
                use_history=use_history,
                voice_response=voice_response,
            )

            full_response = ""
            stream = ollama.chat(model=self.model, messages=messages, stream=True)

            for chunk in stream:
                token = chunk.message.content
                full_response += token
                yield token

            # Guardar no histórico
            self.conversation_history.append(
                {"role": "user", "content": f"[Imagem enviada] {user_message}"}
            )
            self.conversation_history.append(
                {"role": "assistant", "content": full_response}
            )

        except Exception as e:
            logger.error(f"Erro no chat com imagem stream: {e}")
            raise Exception(f"Erro ao processar imagem: {str(e)}")

    def clear_history(self):
        """Limpa o histórico de conversa."""
        self.conversation_history.clear()
        logger.info("Histórico de conversa limpo.")

    def get_history(self) -> List[Dict]:
        """Retorna o histórico de conversa."""
        return self.conversation_history.copy()
