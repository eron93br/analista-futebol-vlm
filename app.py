"""⚽ Analista de Futebol com VLM — app de teste (Prática 4 · Visão Computacional).

Anexe uma imagem de futebol e converse com um VLM (Groq) sobre ela.
Rodar:  streamlit run app.py
"""
from __future__ import annotations

import hashlib
import io
import os

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

import prompts
from vlm_client import MODELO_PADRAO, ClienteVLM, extrair_json, img_para_data_url, montar_mensagens

st.set_page_config(page_title="Analista de Futebol com VLM", page_icon="⚽", layout="wide")

# ----------------------------------------------------------------------------- estilo (tema azul)
st.markdown("""
<style>
.hero {background: linear-gradient(120deg, #0B2E6B 0%, #1E63E9 60%, #3B82F6 100%);
       color: #FFFFFF; padding: 1.1rem 1.4rem; border-radius: 14px; margin-bottom: 1rem;}
.hero h1 {color: #FFFFFF; font-size: 1.8rem; margin: 0;}
.hero p  {color: #DCE8FB; margin: .25rem 0 0 0;}
.passo {color: #1E63E9; font-weight: 700; letter-spacing: .04em; font-size: .8rem; text-transform: uppercase;}
div[data-testid="stChatMessage"] {border-radius: 12px;}
</style>
<div class="hero">
  <h1>⚽ Analista de Futebol com VLM</h1>
  <p>Anexe uma imagem de jogo e pergunte o que quiser: times, jogadas, placar, posicionamento.</p>
</div>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------------- configuração
def ler_segredo(nome: str, padrao: str = "") -> str:
    try:
        return st.secrets.get(nome, os.environ.get(nome, padrao))
    except Exception:  # sem .streamlit/secrets.toml
        return os.environ.get(nome, padrao)


with st.sidebar:

    st.image("logo.png", width="stretch")
    st.divider()

    st.header("⚙️ Configuração")
    api_key = ler_segredo("GROQ_API_KEY")
    if not api_key:
        api_key = st.text_input("GROQ_API_KEY", type="password",
                                help="Crie uma chave gratuita em https://console.groq.com")
    else:
        st.success("Chave do Groq carregada", icon="🔑")
    modelo = st.text_input("Modelo de visão", ler_segredo("VISION_MODEL", MODELO_PADRAO),
                           help="Veja os modelos de visão em https://console.groq.com/docs/vision")
    temperatura = st.slider("Temperatura", 0.0, 1.0, 0.2, 0.1,
                            help="Valores baixos deixam as respostas mais estáveis (bom para contagem).")
    if st.button("🗑️ Nova conversa", width="stretch"):
        st.session_state.mensagens = []
        st.session_state.anotada = None
        st.rerun()
    if api_key and st.button("📃 Listar modelos da conta", width="stretch"):
        try:
            st.write(ClienteVLM(api_key, modelo).listar_modelos())
        except Exception as e:
            st.error(f"Não foi possível listar os modelos: {e}")
    uso = st.session_state.get("uso")
    if uso:
        st.caption(f"Última chamada: {uso.prompt_tokens} tokens de entrada · {uso.completion_tokens} de saída")
    st.divider()
    st.caption("Prática 4 · Visão Computacional · CESAR School. App de teste: as respostas do VLM podem conter erros.")

# ----------------------------------------------------------------------------- estado
ss = st.session_state
ss.setdefault("mensagens", [])     # [{"role", "content", "api_text"?, "imagem"?}]
ss.setdefault("img_bytes", None)
ss.setdefault("img_id", None)
ss.setdefault("anotada", None)


def definir_imagem(dados: bytes) -> None:
    """Troca a imagem atual; uma imagem nova começa uma conversa nova."""
    novo_id = hashlib.md5(dados).hexdigest()
    if novo_id != ss.img_id:
        ss.img_bytes, ss.img_id = dados, novo_id
        ss.mensagens, ss.anotada = [], None


def imagem_atual() -> Image.Image | None:
    return Image.open(io.BytesIO(ss.img_bytes)).convert("RGB") if ss.img_bytes else None


def cliente() -> ClienteVLM | None:
    if not api_key:
        st.warning("Informe a GROQ_API_KEY na barra lateral ou em .streamlit/secrets.toml.")
        return None
    return ClienteVLM(api_key, modelo)


# ----------------------------------------------------------------------------- detecção
CORES = ["#1E63E9", "#E11D48", "#F59E0B", "#10B981", "#8B5CF6", "#06B6D4"]


def desenhar_deteccoes(img: Image.Image, deteccoes: list[dict]) -> Image.Image:
    out = img.copy()
    d = ImageDraw.Draw(out)
    W, H = out.size
    esp = max(2, W // 300)
    try:
        fonte = ImageFont.truetype("DejaVuSans-Bold.ttf", max(12, W // 70))
    except OSError:
        fonte = ImageFont.load_default()
    times = sorted({str(x.get("time")) for x in deteccoes if x.get("classe") == "jogador"})
    for x in deteccoes:
        try:
            x1, y1, x2, y2 = [float(v) for v in x["bbox"]]
        except (KeyError, TypeError, ValueError):
            continue
        caixa = [x1 / 1000 * W, y1 / 1000 * H, x2 / 1000 * W, y2 / 1000 * H]
        classe = str(x.get("classe", "?")).lower()
        if classe == "bola":
            cor = "#FACC15"
        elif classe in ("arbitro", "árbitro"):
            cor = "#111827"
        elif classe == "goleiro":
            cor = "#F97316"
        else:
            cor = CORES[times.index(str(x.get("time"))) % len(CORES)] if str(x.get("time")) in times else CORES[0]
        d.rectangle(caixa, outline=cor, width=esp)
        rotulo = classe if classe != "jogador" else f"{x.get('time') or 'jogador'}"
        tb = d.textbbox((caixa[0], caixa[1]), rotulo, font=fonte)
        d.rectangle([tb[0], tb[1] - (tb[3] - tb[1]) - 4, tb[2] + 6, tb[1]], fill=cor)
        d.text((caixa[0] + 3, tb[1] - (tb[3] - tb[1]) - 3), rotulo, fill="white", font=fonte)
    return out


def rodar_deteccao() -> None:
    c = cliente()
    img = imagem_atual()
    if not c or img is None:
        return
    pedido = {"role": "user", "content": "🎯 Detectar jogadores, goleiros, árbitro e bola",
              "api_text": prompts.DETECCAO}
    msgs = montar_mensagens(ss.mensagens + [pedido], img_para_data_url(img), prompts.SISTEMA)
    with st.spinner("Localizando jogadores e bola..."):
        try:
            dados = extrair_json(c.conversar(msgs, json_mode=True, max_tokens=2000, temperature=0.1))
        except Exception as e:
            st.error(f"Falha na detecção: {e}")
            return
    ss.uso = c.ultimo_uso
    det = dados.get("deteccoes", []) or []
    anotada = desenhar_deteccoes(img, det)
    buf = io.BytesIO()
    anotada.save(buf, format="PNG")
    ss.anotada = buf.getvalue()
    contagem = pd.Series([str(x.get("classe", "?")) for x in det]).value_counts().to_dict() if det else {}
    texto = (f"**{len(det)} objetos localizados** · " + ", ".join(f"{k}: {v}" for k, v in contagem.items())
             + (f"\n\n{dados.get('resumo')}" if dados.get("resumo") else "")
             + "\n\n_Caixas geradas pelo VLM: posições aproximadas (veja a comparação com o YOLO na Aula 09)._")
    ss.mensagens += [pedido, {"role": "assistant", "content": texto, "imagem": ss.anotada,
                              "api_text": f"Resultado da detecção (JSON): {dados}"}]


# ----------------------------------------------------------------------------- chat
def responder(pergunta: str, api_text: str | None = None) -> None:
    c = cliente()
    img = imagem_atual()
    if not c:
        return
    if img is None:
        st.info("Anexe uma imagem de futebol primeiro.")
        return
    msg = {"role": "user", "content": pergunta}
    if api_text:
        msg["api_text"] = api_text
    ss.mensagens.append(msg)
    msgs = montar_mensagens(ss.mensagens, img_para_data_url(img), prompts.SISTEMA)
    with st.spinner("Analisando a imagem..."):
        try:
            resposta = c.conversar(msgs, temperature=temperatura)
        except Exception as e:
            ss.mensagens.pop()
            st.error(f"Erro ao consultar o VLM: {e}")
            return
    ss.uso = c.ultimo_uso
    ss.mensagens.append({"role": "assistant", "content": resposta})


# ----------------------------------------------------------------------------- layout
col_img, col_chat = st.columns([1, 1.25], gap="large")

with col_img:
    st.markdown('<div class="passo">1 · Anexe a imagem</div>', unsafe_allow_html=True)
    arquivo = st.file_uploader("Imagem de futebol (JPG, PNG ou WEBP)", type=["jpg", "jpeg", "png", "webp"],
                               label_visibility="collapsed")
    if arquivo is not None:
        definir_imagem(arquivo.getvalue())

    if ss.img_bytes:
        ver_anotada = ss.anotada is not None and st.toggle("Mostrar detecções", value=True)
        st.image(ss.anotada if ver_anotada else ss.img_bytes, width="stretch")
        if st.button("🎯 Detectar jogadores e bola", type="primary", width="stretch"):
            rodar_deteccao()
            st.rerun()
    else:
        st.info("Envie uma imagem aqui ou pelo clipe 📎 do chat. Dica: um frame de transmissão funciona bem.",
                icon="🖼️")

with col_chat:
    st.markdown('<div class="passo">2 · Converse sobre a imagem</div>', unsafe_allow_html=True)
    atalhos = st.columns(len(prompts.ATALHOS))
    for col, (rotulo, texto) in zip(atalhos, prompts.ATALHOS.items()):
        if col.button(rotulo, width="stretch", disabled=not ss.img_bytes, help=texto):
            responder(texto)
            st.rerun()

    caixa = st.container(height=470, border=True)
    with caixa:
        if not ss.mensagens:
            st.caption("Exemplos: “Quem está com a bola?” · “Quantos jogadores do time de azul aparecem?” · "
                       "“Qual é o placar?” · “Há impedimento nesse lance?”")
        for m in ss.mensagens:
            with st.chat_message(m["role"], avatar="🧑" if m["role"] == "user" else "⚽"):
                st.markdown(m["content"])
                if m.get("imagem"):
                    st.image(m["imagem"], width="stretch")

    entrada = st.chat_input("Pergunte algo sobre a imagem...", accept_file=True,
                            file_type=["jpg", "jpeg", "png", "webp"])
    if entrada:
        if entrada.files:
            definir_imagem(entrada.files[0].getvalue())
        if entrada.text:
            responder(entrada.text)
        st.rerun()
