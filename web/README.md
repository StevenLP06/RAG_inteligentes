# Interfaz web — Asistente RAG Mesa de Ayuda

React + TypeScript + Vite + Tailwind v4 + Motion, con componentes adaptados de Aceternity UI.
Usa la lógica de `rag/` sin modificarla a través de la API de `api/server.py`.

## Desarrollo (dos terminales, desde la raíz del proyecto)

```powershell
pip install -r requirements.txt -r api/requirements.txt
python -m uvicorn api.server:app --port 8000          # terminal 1: API
cd web; npm install; npm run dev                      # terminal 2: http://localhost:5173
```

## Producción (un solo servidor)

```powershell
cd web; npm run build; cd ..
python -m uvicorn api.server:app --port 8000          # http://localhost:8000
```

Prueba sin red ni clave: `$env:RAG_TEST_MODE="1"` antes de iniciar la API (LLM simulado; no válido para el informe).
