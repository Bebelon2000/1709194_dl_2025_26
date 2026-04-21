from smolagents import CodeAgent, DuckDuckGoSearchTool, LiteLLMModel
from datetime import datetime

# 1. Configurar o modelo
model = LiteLLMModel(
    model_id="ollama_chat/gemma4", 
    api_base="http://localhost:11434"
)

# 2. Obter a data atual formatada
data_hoje = datetime.now().strftime("%d/%m/%Y")

# 3. Criar o Agente com uma instrução de sistema (System Prompt)
agent = CodeAgent(
    tools=[DuckDuckGoSearchTool()], 
    model=model,
    # Adicionamos a data aqui para o modelo se localizar no tempo
    additional_authorized_imports=["datetime"] 
)

# 4. Inserir a data na pergunta para "forçar" o contexto
pergunta_usuario = "quais os jogos de futebol de hoje na espanha?"
prompt_com_data = f"Hoje é dia {data_hoje}. Baseado nisso, responda: {pergunta_usuario}"

print(f"--- Consultando para a data: {data_hoje} ---\n")
resultado = agent.run(prompt_com_data)

print("\n--- Resposta Final ---\n")
print(resultado)
