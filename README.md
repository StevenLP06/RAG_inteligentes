# Asistente RAG para la Mesa de Ayuda de TI — Andina Tech (empresa ficticia)

Parcial práctico de Sistemas Inteligentes Computacionales (Corte 2). Asistente que responde preguntas sobre manuales, políticas, preguntas frecuentes y el catálogo de servicios de una Mesa de Ayuda. Cita la evidencia (archivo y localizador) y se abstiene cuando la evidencia es insuficiente.

> **Datos:** todo el corpus es **sintético** y está identificado como tal dentro de cada archivo. Andina Tech S.A.S. no existe, así que el corpus es apto para procesarse con servicios externos.

## Caso de uso

| | |
|---|---|
| **Usuarios** | Analistas de nivel 1 de la Mesa de Ayuda y empleados que buscan autoservicio. |
| **Preguntas que resuelve** | Errores y uso de la VPN, bloqueo y restablecimiento de cuentas, MFA, cuotas y errores de correo, impresión, prioridades y tiempos de atención (SLA), solicitudes de servicio y seguridad del puesto de trabajo. |
| **Fuera de alcance** | Temas no documentados (costos y licencias, infraestructura de servidores y bases de datos, redes del hogar, desarrollo de software), acciones sobre sistemas (no desbloquea cuentas ni abre casos) y cualquier dato personal. |

## Estructura

```
rag_mesa_ayuda/
├── RAG_Mesa_Ayuda.ipynb        Cuaderno principal (instalación → demo → evaluación → métricas)
├── corpus/                     5 archivos, 3 formatos (PDF ×2, DOCX ×1, MD ×2), se leen al iniciar
├── evaluacion/preguntas.json   9 preguntas con respuesta esperada, evidencia literal y ubicación
├── HIPOTESIS.md                Qué esperamos que cambie en cada comparación (antes de correr)
├── INFORME_borrador.md         Esqueleto del informe con el flujo, la metodología y tablas por llenar
├── rag/
│   ├── config.py               R0, R1, R2, C0, B1, B2, B3 (+ R2K8 opcional) y modelos
│   ├── ingest.py               Lectores PDF/DOCX/MD con localizadores
│   ├── chunking.py             Fragmentación fija (tokens + solapamiento) y estructural
│   ├── retrieval.py            Embeddings, coseno, BM25 y fusión RRF
│   ├── llm.py                  Cliente OpenRouter / Hugging Face (clave desde variables de entorno)
│   ├── prompts.py              Plantillas RAG (iguales en R0/R1/R2) y C0
│   ├── pipeline.py             Consulta, contexto con límite, citas y abstención
│   ├── evaluation.py           Corridas, registros, pre-valoración y métricas
│   └── cli.py                  Línea de comandos
├── scripts/
│   ├── generar_corpus.py       Regenera el corpus sintético
│   └── verificar_evidencia.py  Comprueba que cada pasaje de referencia exista en el corpus
└── resultados/                 Se crea al evaluar (registros.jsonl, valoracion.csv, tabla_resultados.md)
```

## Instalación

Python 3.10 o superior. Opción recomendada: **Google Colab** (abrir `RAG_Mesa_Ayuda.ipynb` y seguir las celdas). En local:

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

La primera ejecución descarga de Hugging Face los modelos de embeddings (`intfloat/multilingual-e5-base`, ~1,1 GB; `BAAI/bge-m3` para el experimento B, ~2,3 GB).

## Credenciales (sin entregar claves)

1. Cree una clave en <https://openrouter.ai/keys> (los modelos con sufijo `:free` no tienen costo).
2. **Local:** copie `.env.example` a `.env` y escriba la clave en `OPENROUTER_API_KEY=`. El archivo `.env` está en `.gitignore` y **no se entrega**.
3. **Colab:** en el panel lateral 🔑 *Secretos* cree `OPENROUTER_API_KEY` y active el acceso del cuaderno. El cuaderno la lee con `google.colab.userdata`; si no existe, la pide con `getpass` (no se muestra ni se guarda).
4. Alternativa: `LLM_PROVIDER=huggingface` y `HF_TOKEN` para usar los proveedores de inferencia de Hugging Face.

## Modelos (identificadores registrados)

| Rol | Identificador por defecto | Variable para cambiarlo |
|---|---|---|
| LLM (R0, R1, R2, C0, B1) | `meta-llama/llama-3.3-70b-instruct:free` (OpenRouter) | `LLM_MODEL` |
| LLM alternativo (B2, B3) | `google/gemma-3-27b-it:free` (OpenRouter) | `LLM_MODEL_ALT` |
| Embeddings (R0, R1, R2, B2) | `intfloat/multilingual-e5-base` (local, Hugging Face) | `EMB_MODEL` |
| Embeddings alternativos (B1, B3) | `BAAI/bge-m3` (local, Hugging Face) | `EMB_MODEL_ALT` |
| Tokenizador de fragmentación | el de `intfloat/multilingual-e5-base` en todas las configuraciones | `CHUNK_TOKENIZER` |

Los modelos gratuitos de OpenRouter rotan. **Antes de las corridas finales**, ejecute la celda «Verificar modelos disponibles» del cuaderno y, si un identificador ya no existe, cámbielo en `.env` (no en el código). Una vez fijados, no los cambie entre configuraciones. Cada registro guarda también el modelo y el proveedor efectivamente servidos.

## Configuraciones

| Config. | Fragmentación | Recuperación | k | LLM | Embeddings |
|---|---|---|---|---|---|
| **R0** Base | fija, 400 tokens, solapamiento 60 | densa, coseno | 4 | base | e5-base |
| **R1** Fragmentación | estructural: párrafos completos de una misma sección hasta 400 tokens, sin solapamiento | densa | 4 | base | e5-base |
| **R2** Recuperación | igual a R0 | híbrida: coseno + BM25 fusionados con RRF (constante 60) | 4 | base | e5-base |
| **C0** Control | — (sin documentos) | — | — | base | — |
| **B1** | igual a R0 | densa | 4 | base | **bge-m3** (índice reconstruido) |
| **B2** | igual a R0 | densa | 4 | **alternativo** | e5-base |
| **B3** | igual a R0 | densa | 4 | **alternativo** | **bge-m3** |

Fijos en todas: temperatura 0, `top_p` 1, salida máx. 512 tokens, semilla 42, contexto máx. 2400 tokens, plantilla `rag-v1` (C0 usa `c0-v1`, adaptada a la ausencia de documentos).

## Ejecución

```bash
python scripts/verificar_evidencia.py                       # 1. comprueba las referencias
python -m rag.cli fragmentos --config R0                    # 2. inspecciona fragmentos y localizadores
python -m rag.cli preguntar "¿Qué hago con el error VPN-809?" --config R0
python -m rag.cli evaluar --configs R0 R1 R2 C0 --salida resultados/parte_A   # 36 corridas
python -m rag.cli evaluar --configs B1 B2 B3 --salida resultados/parte_B
# revise y complete las columnas *_manual de resultados/parte_A/valoracion.csv, luego:
python -m rag.cli metricas --salida resultados/parte_A
```

La evaluación es **reanudable**: si se interrumpe (por ejemplo, por límite de peticiones del plan gratuito), vuelva a ejecutar el mismo comando y continuará donde quedó. Los fallos se registran en `fallos.jsonl` y la consulta se repite con la misma configuración. `RAG_SLEEP_S` controla la pausa entre llamadas (3 s por defecto).

**Prueba sin red:** `RAG_TEST_MODE=1` usa embeddings por hashing, un tokenizador por expresión regular y un LLM simulado. Solo sirve para verificar que la tubería funciona; **sus resultados no se usan en el informe**.

## Registros y valoración

Cada línea de `registros.jsonl` guarda: pregunta, configuración, fragmentos recuperados en orden (con puntajes), contexto enviado y estado de cada fragmento (completo/recortado/omitido), si el límite obligó a recortar, respuesta, citas resueltas a archivo y localizador, modelo servido, intentos y tiempos.

`valoracion.csv` trae una **pre-valoración automática** (columnas `*_auto`): la cobertura se calcula buscando cada pasaje de referencia completo dentro de los fragmentos; la corrección busca los hechos clave en la respuesta; el respaldo comprueba que esos hechos estén en los fragmentos citados. Es solo una ayuda: el equipo debe revisar cada respuesta y escribir 1 o 0 en las columnas `*_manual` (que tienen prioridad). La tabla final indica cuántas celdas siguen dependiendo solo de la valoración automática.

## Declaración de uso de IA

Ver la sección correspondiente en `INFORME_borrador.md`.
