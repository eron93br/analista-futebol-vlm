# ⚽ Analista de Futebol com VLM

App de teste da **Prática 4 · Visão Computacional (CESAR School)**: uma interface em Streamlit, com tema azul,
onde você anexa uma imagem de futebol e conversa com um Modelo de Visão e Linguagem (VLM) servido pelo Groq.

## O que o app faz
- **Anexar imagem:** pelo campo da coluna da esquerda ou pelo clipe 📎 do chat (JPG, PNG ou WEBP).
- **Chat sobre a imagem:** perguntas livres em português, com histórico. A imagem é enviada uma única vez,
  na primeira mensagem, e o modelo continua "vendo" a imagem nos turnos seguintes.
- **Atalhos:** descrever a cena, times e uniformes, leitura tática e textos visíveis (placar, números).
- **🎯 Detecção:** o VLM devolve caixas em JSON (coordenadas 0–1000) para jogadores, goleiros, árbitro e bola,
  e o app desenha as caixas sobre a imagem (cor por time). As caixas são aproximadas: compare com o YOLO (Aula 08/09).

## Como rodar
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
A chave fica em `.streamlit/secrets.toml` (veja `.streamlit/secrets.toml.example`). Também funciona com a
variável de ambiente `GROQ_API_KEY` ou digitando a chave na barra lateral.

## Estrutura
| Arquivo | Papel |
|---|---|
| `app.py` | Interface: upload, imagem anotada, chat e atalhos |
| `vlm_client.py` | Cliente do Groq (base64, histórico, modo JSON, nova tentativa em limite de taxa) |
| `prompts.py` | Prompt de sistema, atalhos e prompt de detecção |
| `.streamlit/config.toml` | Tema azul |
| `.streamlit/secrets.toml` | Sua chave (**não versionar**) |

## Modelo
O padrão é `qwen/qwen3.8-27b`, o mesmo modelo de visão do notebook da Aula 09. Se o Groq mudar o nome,
use **📃 Listar modelos da conta** na barra lateral e troque em `VISION_MODEL` (ou no campo da barra lateral).
Limites do plano gratuito: https://console.groq.com/docs/rate-limits · Visão: https://console.groq.com/docs/vision

## Segurança
`.streamlit/secrets.toml` está no `.gitignore`. Nunca suba a chave para o GitHub; se ela vazar, revogue em
https://console.groq.com/keys e gere outra.

## Limitações conhecidas (para discutir na apresentação)
- Alucinação com premissa falsa (o prompt de sistema pede para o modelo corrigir a premissa).
- Contagens instáveis entre execuções; use temperatura baixa.
- Caixas do VLM menos precisas que as de um detector como o YOLO.
- Cada imagem custa cerca de 2 mil tokens de entrada.
