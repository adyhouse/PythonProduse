@echo off
REM Pornește Ollama vizibil pe rețea (VM / alte PC-uri pot conecta).
REM Rulează pe PC-ul unde e instalat Ollama (NU în VM).
set OLLAMA_HOST=0.0.0.0
echo Ollama va asculta pe toate interfețele (port 11434).
echo Conectare din VM: set OLLAMA_URL=http://IP_ACEST_PC:11434 în .env
echo.
ollama serve
