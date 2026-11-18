"""Prompts do Analista de Futebol com VLM."""

SISTEMA = """Você é um analista de futebol que responde perguntas sobre UMA imagem enviada pelo usuário.
Regras:
- Responda em português do Brasil, de forma objetiva.
- Use somente o que está visível na imagem. Se algo não aparece ou não dá para ver com clareza, diga isso.
- Se a pergunta assumir algo que não está na imagem, corrija a premissa explicitamente.
- Ao contar (jogadores, pessoas), diga se a contagem é aproximada.
- Não identifique jogadores reais pelo rosto; você pode citar nomes e números apenas se estiverem escritos na imagem.
- Se a imagem não for de futebol, avise e responda apenas o que for possível."""

# Atalhos exibidos como botões na interface
ATALHOS = {
    "📋 Cena": "Descreva a cena: tipo de imagem (transmissão, foto, treino), momento do jogo, "
                          "posição da bola e o que está acontecendo.",
    "👕 Times": "Quantos times aparecem? Descreva as cores dos uniformes, quantos jogadores de cada "
                           "time estão visíveis e se há goleiro ou árbitro.",
    "🧭 Tática": "Faça uma leitura tática do que está visível: setor do campo, quem parece atacar, "
                        "linhas e espaços. Deixe claro o que é inferência.",
    "🔤 Textos": "Transcreva textos visíveis (placar, tempo, nomes, números de camisa, publicidade).",
}

DETECCAO = """Localize na imagem cada JOGADOR, GOLEIRO, ÁRBITRO e a BOLA.
Use coordenadas normalizadas de 0 a 1000 (x para a direita, y para baixo), no formato [x1, y1, x2, y2].
Para jogadores, informe o time pela cor do uniforme.
Responda APENAS com JSON neste formato:
{"deteccoes": [{"classe": "jogador" | "goleiro" | "arbitro" | "bola", "time": "cor do uniforme ou null",
                "bbox": [x1, y1, x2, y2]}],
 "resumo": "uma frase em português sobre a cena"}"""
