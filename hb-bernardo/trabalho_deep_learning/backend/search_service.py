"""
Search Service - Pesquisa web usando DuckDuckGo.
Fornece resultados de pesquisa para enriquecer as respostas do modelo (RAG).
"""

import logging
from typing import List, Dict, Optional
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)


class SearchService:
    """Serviço de pesquisa web usando DuckDuckGo."""

    def __init__(self):
        logger.info("Search Service inicializado.")

    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Pesquisa na web usando DuckDuckGo.

        Args:
            query: Termo de pesquisa.
            max_results: Número máximo de resultados.

        Returns:
            Lista de dicionários com 'title', 'url', 'snippet'.
        """
        try:
            results = []
            with DDGS() as ddgs:
                ddgs_results = ddgs.text(
                    query,
                    max_results=max_results,
                    region="pt-pt",
                )
                for r in ddgs_results:
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })

            logger.info(
                f"Pesquisa '{query}': {len(results)} resultados encontrados."
            )
            return results

        except Exception as e:
            logger.error(f"Erro na pesquisa: {e}")
            return []

    def format_results_for_llm(self, results: List[Dict]) -> str:
        """
        Formata os resultados de pesquisa para injetar no prompt do LLM.

        Args:
            results: Lista de resultados de pesquisa.

        Returns:
            String formatada com os resultados.
        """
        if not results:
            return "Nenhum resultado encontrado na pesquisa web."

        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(
                f"[{i}] {r['title']}\n"
                f"    URL: {r['url']}\n"
                f"    {r['snippet']}"
            )

        return "\n\n".join(formatted)

    def search_and_format(self, query: str, max_results: int = 5) -> str:
        """
        Pesquisa e formata os resultados numa única chamada.

        Args:
            query: Termo de pesquisa.
            max_results: Número máximo de resultados.

        Returns:
            String formatada com os resultados.
        """
        results = self.search(query, max_results)
        return self.format_results_for_llm(results)
