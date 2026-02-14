#!/bin/sh
# Pornește Ollama vizibil pe rețea (VM / alte PC-uri pot conecta).
# Rulează pe Mac/Linux unde e instalat Ollama (NU în VM).
export OLLAMA_HOST=0.0.0.0
echo "Ollama va asculta pe toate interfețele (port 11434)."
echo "Conectare din VM: OLLAMA_URL=http://IP_ACEST_PC:11434 în .env"
echo ""
exec ollama serve
