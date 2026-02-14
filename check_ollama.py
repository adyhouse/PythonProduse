#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verifică dacă Ollama răspunde pe rețea (pentru scraper din VM).
Citește OLLAMA_URL din .env sau folosește http://localhost:11434.
Rulează din VM: python check_ollama.py
"""
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def check_ollama(base_url=None, timeout=5):
    """Verifică dacă Ollama răspunde la base_url. Returnează (ok: bool, msg: str)."""
    if not base_url or not base_url.strip():
        base_url = "http://localhost:11434"
    base_url = base_url.rstrip("/")
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{base_url}/api/tags",
            headers={"Accept": "application/json"},
            method="GET"
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read().decode("utf-8", errors="ignore")
            if "models" in data or "[]" in data:
                return True, f"OK – Ollama vizibil la {base_url}"
            return True, f"OK – Ollama răspunde la {base_url}"
    except Exception as e:
        return False, f"Eroare: {e}"

def main():
    url = os.getenv("OLLAMA_URL", "").strip() or "http://localhost:11434"
    print(f"Verific Ollama la: {url}")
    ok, msg = check_ollama(url)
    print(msg)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
