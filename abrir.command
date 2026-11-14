#!/bin/zsh
# Doble clic en este archivo para abrir Expediente Tierra en el navegador.
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
fi
(sleep 4; open http://localhost:8501) &
.venv/bin/streamlit run app.py --server.headless true --server.port 8501
