"""Cliente de LLM compatible con la API de chat de OpenAI.

Proveedores soportados (la clave se lee SIEMPRE de variables de entorno, nunca del código):
  openrouter   -> https://openrouter.ai/api/v1          (OPENROUTER_API_KEY)
  huggingface  -> https://router.huggingface.co/v1      (HF_TOKEN)
  mock         -> respuesta simulada, solo para pruebas sin red (RAG_TEST_MODE=1)
"""
from __future__ import annotations

import os
import re
import time

import requests

PROVIDERS = {
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "env_key": "OPENROUTER_API_KEY"},
    "huggingface": {"base_url": "https://router.huggingface.co/v1", "env_key": "HF_TOKEN"},
}


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, provider: str, model: str, temperature: float, max_tokens: int, seed: int,
                 top_p: float = 1.0, test_mode: bool = False, timeout: int = 120, max_retries: int = 4):
        self.provider = "mock" if test_mode else provider
        self.model = model
        self.params = {"temperature": temperature, "max_tokens": max_tokens, "seed": seed, "top_p": top_p}
        self.timeout = timeout
        self.max_retries = max_retries
        if self.provider != "mock":
            if provider not in PROVIDERS:
                raise ValueError(f"Proveedor desconocido: {provider}")
            key = os.getenv(PROVIDERS[provider]["env_key"])
            if not key:
                raise LLMError(f"Falta la variable de entorno {PROVIDERS[provider]['env_key']}. "
                               "Configúrala en .env o en los secretos del entorno (ver README).")
            self._key = key
            self._url = PROVIDERS[provider]["base_url"] + "/chat/completions"

    # --------------------------------------------------------------------------------
    def chat(self, system: str, user: str) -> dict:
        """Devuelve {'texto', 'modelo_servido', 'uso', 'intentos', 'latencia_s'}.
        Los fallos se registran en 'intentos' y se reintenta con la MISMA configuración."""
        if self.provider == "mock":
            return self._mock(system, user)
        payload = {"model": self.model,
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                   **self.params}
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json",
                   "HTTP-Referer": "https://github.com/rag-mesa-ayuda", "X-Title": "RAG Mesa de Ayuda (academico)"}
        intentos = []
        for attempt in range(1, self.max_retries + 1):
            t0 = time.perf_counter()
            try:
                r = requests.post(self._url, json=payload, headers=headers, timeout=self.timeout)
                dt = time.perf_counter() - t0
                if r.status_code == 200:
                    data = r.json()
                    if "choices" in data and data["choices"]:
                        texto = (data["choices"][0]["message"].get("content") or "").strip()
                        if texto:
                            intentos.append({"intento": attempt, "estado": "ok", "latencia_s": round(dt, 3)})
                            return {"texto": texto, "modelo_servido": data.get("model", self.model),
                                    "proveedor_servido": data.get("provider"), "uso": data.get("usage"),
                                    "intentos": intentos, "latencia_s": dt}
                        err = "respuesta vacía"
                    else:
                        err = str(data.get("error", data))[:300]
                else:
                    err = f"HTTP {r.status_code}: {r.text[:300]}"
            except requests.RequestException as e:
                dt = time.perf_counter() - t0
                err = f"{type(e).__name__}: {e}"[:300]
            intentos.append({"intento": attempt, "estado": "fallo", "error": err, "latencia_s": round(dt, 3)})
            time.sleep(min(60, 5 * 2 ** (attempt - 1)))
        raise LLMError(f"La llamada falló tras {self.max_retries} intentos: {intentos}")

    # --------------------------------------------------------------------------------
    @staticmethod
    def _mock(system: str, user: str) -> dict:
        """LLM simulado y determinista. Solo verifica que la tubería funciona de punta a punta."""
        t0 = time.perf_counter()
        frags = re.findall(r"\[(F\d+)\] \(archivo[^\n]*\n(.*?)(?=\n\n\[F\d+\] \(archivo|\n\nPregunta:)", user, re.S)
        q = re.search(r"Pregunta: (.*?)\n", user)
        q_terms = set(re.findall(r"\w{5,}", (q.group(1) if q else "").lower()))
        if not frags:
            texto = "NO TENGO INFORMACIÓN SUFICIENTE: respuesta simulada del modo de prueba."
        else:
            best = None
            for label, body in frags:
                for sent in re.split(r"(?<=[.!?])\s+", body.replace("\n", " ")):
                    ov = len(q_terms & set(re.findall(r"\w{5,}", sent.lower())))
                    if best is None or ov > best[0]:
                        best = (ov, label, sent.strip())
            if best is None or best[0] < 2:
                texto = "EVIDENCIA INSUFICIENTE: (simulado) los fragmentos no cubren la pregunta."
            else:
                texto = f"{best[2]} [{best[1]}]"
        return {"texto": texto, "modelo_servido": "mock", "proveedor_servido": "mock", "uso": None,
                "intentos": [{"intento": 1, "estado": "ok"}], "latencia_s": time.perf_counter() - t0}
