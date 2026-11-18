"""Cliente do VLM via API do Groq.

Adaptado das funções do notebook da Aula 09 (img_para_data_url, perguntar_vlm, extrair_json),
agora com suporte a conversa em vários turnos sobre a mesma imagem.
"""
from __future__ import annotations

import base64
import io
import json
import re
import time

import groq
from groq import Groq
from PIL import Image

MODELO_PADRAO = "qwen/qwen3.8-27b"  # mesmo modelo de visão do notebook da Aula 09


def img_para_data_url(img: Image.Image, lado_max: int = 1024, qualidade: int = 90) -> str:
    """Redimensiona (maior lado <= lado_max) e devolve a imagem como data URL JPEG em base64."""
    im = img.convert("RGB").copy()
    im.thumbnail((lado_max, lado_max))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=qualidade)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")


def extrair_json(texto: str) -> dict:
    """Lê JSON mesmo se vier dentro de ```json ... ```."""
    texto = re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.M).strip()
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fim == -1:
        raise ValueError("A resposta do modelo não contém JSON.")
    return json.loads(texto[inicio:fim + 1])


def montar_mensagens(historico: list[dict], data_url: str, sistema: str) -> list[dict]:
    """Converte o histórico do chat no formato da API.

    A imagem vai anexada apenas à PRIMEIRA mensagem do usuário: assim ela conta uma única vez
    (~2 mil tokens) e o modelo continua "vendo" a imagem nos turnos seguintes.
    """
    mensagens = [{"role": "system", "content": sistema}]
    imagem_anexada = False
    for m in historico:
        texto = m.get("api_text", m["content"])
        if m["role"] == "user" and not imagem_anexada:
            mensagens.append({"role": "user", "content": [
                {"type": "text", "text": texto},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]})
            imagem_anexada = True
        else:
            mensagens.append({"role": m["role"], "content": texto})
    return mensagens


class ClienteVLM:
    def __init__(self, api_key: str, modelo: str = MODELO_PADRAO):
        self.client = Groq(api_key=api_key)
        self.modelo = modelo
        self.usar_params_raciocinio = True  # vira False sozinho se o modelo não aceitar
        self.ultimo_uso = None

    def listar_modelos(self) -> list[str]:
        return sorted(m.id for m in self.client.models.list().data)

    def conversar(self, mensagens: list[dict], json_mode: bool = False, max_tokens: int = 800,
                  temperature: float = 0.2, tentativas: int = 4) -> str:
        kwargs = dict(model=self.modelo, messages=mensagens, max_tokens=max_tokens, temperature=temperature)
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        resp = None
        for t in range(tentativas):
            extras = dict(reasoning_effort="none", reasoning_format="hidden") if self.usar_params_raciocinio else {}
            try:
                resp = self.client.chat.completions.create(**kwargs, **extras)
                break
            except groq.BadRequestError as e:
                if extras and "reasoning" in str(e).lower():  # modelo sem esses parâmetros
                    self.usar_params_raciocinio = False
                    continue
                raise
            except groq.RateLimitError:
                time.sleep(10 * (t + 1))  # limite do plano gratuito: espera e tenta de novo
        if resp is None:
            raise RuntimeError("Limite de requisições atingido. Aguarde um minuto e tente de novo.")

        self.ultimo_uso = resp.usage
        texto = resp.choices[0].message.content or ""
        return re.sub(r"<think>.*?</think>", "", texto, flags=re.S).strip()
