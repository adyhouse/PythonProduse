================================================================================
                    EXTRACTOARE DE LINK-URI PE CATEGORII
                          MOBILESENTRIX
================================================================================

Am creat 3 SCRIPTURI PYTHON SEPARATE pentru a extrage link-urile de produse din
fiecare categorie a site-ului MobileSentrix.

================================================================================
                            SCRIPTURILE CREATE
================================================================================

1. extractor_category_links.py
   ➜ Extrage link-uri dintr-o categorie cu paginație automată
   ➜ Creează config file automat cu URL-urile categoriilor
   ➜ Exportă în CSV și JSON
   ➜ RECOMANDA]

2. extractor_from_csv.py
   ➜ Ia o listă existentă de link-uri (CSV sau text)
   ➜ Le clasifică automat pe categorii (Apple, Samsung, etc.)
   ➜ Util dacă ai deja o lista de link-uri
   ➜ Output: CSV și JSON organizate

3. extractor_selenium.py
   ➜ Folosește browser automat pentru site-uri cu Cloudflare/JS
   ➜ Necesită: pip install selenium webdriver-manager
   ➜ Mai lent dar mai robust

================================================================================
                        UTILIZARE RAPIDĂ - START HERE
================================================================================

OPȚIUNEA 1: Extrage dintr-o categorie (cu config)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Pasul 1: Rulează scriptul
    python extractor_category_links.py
    
    ➜ Creează category_config.txt cu categorii de exemplu
  
  Pasul 2: Editează category_config.txt
    - Adaugă/elimină categorii în funcție de nevoi
    - Format: category_name | category_url
    - Exemplu:
      Apple - iPhone | https://www.mobilesentrix.eu/accessories/apple-iphone/
      Apple - iPad | https://www.mobilesentrix.eu/accessories/apple-ipad/
    
    - Liniile cu # sunt comentarii
  
  Pasul 3: Rulează din nou
    python extractor_category_links.py
    
    ➜ Extrage link-urile din toate categoriile
    ➜ Creează:
       - category_links.csv
       - category_links.json


OPȚIUNEA 2: Organizează link-uri existente
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Ai deja link-uri într-un CSV sau text file? 
  
  Rulează:
    python extractor_from_csv.py produse.csv
    
  SAU:
    python extractor_from_csv.py sku_list.txt
    
  ➜ Citește link-urile
  ➜ Le clasifică pe categorii (automat)
  ➜ Exportă în:
     - products_by_category.csv
     - products_by_category.json


================================================================================
                        STRUCTURA CATEGORIILOR (EXEMPLU)
================================================================================

APPLE IPHONE
  ├─ https://www.mobilesentrix.eu/accessories/apple-iphone/case-1/
  ├─ https://www.mobilesentrix.eu/accessories/apple-iphone/screen-protector/
  └─ https://www.mobilesentrix.eu/accessories/apple-iphone/battery/

APPLE IPAD
  ├─ https://www.mobilesentrix.eu/accessories/apple-ipad/cover/
  ├─ https://www.mobilesentrix.eu/accessories/apple-ipad/stand/
  └─ ...

SAMSUNG GALAXY S
  ├─ https://www.mobilesentrix.eu/accessories/samsung-galaxy-s/screen/
  ├─ https://www.mobilesentrix.eu/accessories/samsung-galaxy-s/battery/
  └─ ...

(și așa mai departe pentru fiecare categorie din config)

================================================================================
                          OUTPUT FINAL (CSV)
================================================================================

Fiecare script creează un CSV cu format:

  Categoria,Link Produs
  Apple - iPhone,https://www.mobilesentrix.eu/...
  Apple - iPhone,https://www.mobilesentrix.eu/...
  Apple - iPad,https://www.mobilesentrix.eu/...
  Samsung - Galaxy S,https://www.mobilesentrix.eu/...
  ...

Acest CSV poate fi:
  1. Copiat în sku_list.txt
  2. Folosit direct cu import_gui.py
  3. Procesat pentru alte scopuri

================================================================================
                    INTEGRARE CU IMPORT_GUI.PY
================================================================================

După ce ai CSV-ul cu link-uri pe categorii:

  1. Copiază link-urile din CSV în sku_list.txt
  
  2. Rulează import_gui.py
  
  3. Click butonul "Importa" -> Program descarcă și procesează
  
  4. CSV final export va conține:
     - Categoria (din linkul original) ✓
     - Imaginile uploadate pe WordPress ✓
     - Toate detaliile produsului ✓
     - Preț EUR/RON ✓
     - Descriere etc.

================================================================================
                              EXEMPLE COMENZI
================================================================================

# Extrage categorii (cu configurare manuală):
python extractor_category_links.py

# Extrage din CSV existent:
python extractor_from_csv.py produse.csv

# Extrage din text file:
python extractor_from_csv.py sku_list.txt

# Extrage cu Selenium (pentru site-uri cu JS):
python extractor_selenium.py

# Rulează import_gui cu link-urile:
python import_gui.py

================================================================================
                        FLOWCHART - CUM SE FOLOSESC
================================================================================

┌─────────────────────────────────────────────────────────────┐
│   1. Alegi o abordare:                                      │
│   ┌─────────────────┐  ┌──────────────────┐  ┌───────────┐ │
│   │ Nou extractor   │  │ Linkuri existente│  │ JavaScript│ │
│   │ (din categor.)  │  │ (CSV/text)       │  │(Selenium) │ │
│   └────────┬────────┘  └────────┬─────────┘  └─────┬─────┘ │
│            │                    │                   │       │
│            v                    v                   v       │
│   ┌─────────────────┐  ┌──────────────────┐  ┌───────────┐ │
│   │ extractor_      │  │ extractor_       │  │ extractor_│ │
│   │ category_links  │  │ from_csv         │  │ selenium  │ │
│   └────────┬────────┘  └────────┬─────────┘  └─────┬─────┘ │
│            │                    │                   │       │
│            v                    v                   v       │
│   ┌─────────────────────────────────────────────────────┐  │
│   │ CSV cu link-uri organizate pe categorii            │  │
│   │ (products_by_category.csv sau category_links.csv)  │  │
│   └────────┬──────────────────────────────────────────┘  │
│            │                                              │
│            v                                              │
│   ┌─────────────────────────────────────────────────────┐  │
│   │ Copiază link-urile în sku_list.txt                 │  │
│   └────────┬──────────────────────────────────────────┘  │
│            │                                              │
│            v                                              │
│   ┌─────────────────────────────────────────────────────┐  │
│   │ Rulează import_gui.py                              │  │
│   └────────┬──────────────────────────────────────────┘  │
│            │                                              │
│            v                                              │
│   ┌─────────────────────────────────────────────────────┐  │
│   │ Import final CSV cu imagini + categorii            │  │
│   │ (export_produse.csv)                               │  │
│   └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

================================================================================
                            FIȘIERE GENERATE
================================================================================

După rulare, se vor crea:

De la extractor_category_links.py:
  ✓ category_config.txt (configurație)
  ✓ category_links.csv (linkuri pe categorii)
  ✓ category_links.json (aceleași date în JSON)

De la extractor_from_csv.py:
  ✓ products_by_category.csv
  ✓ products_by_category.json

De la import_gui.py (după import):
  ✓ export_produse.csv (cu imagini + categorii + pret)

================================================================================
                          TROUBLESHOOTING
================================================================================

P: Script-ul nu extrage niciun link
R: 
  - Site-ul poate folosi JavaScript (încearcă extractor_selenium.py)
  - URL-urile din config pot fi greșite
  - Verifică în browser dacă URL-urile sunt corecte

P: 404 Not Found pentru anumite categorii
R:
  - MobileSentrix s-ar fi schimbat structura URL
  - Caută URL-urile manuale și actualizează config

P: Rate limiting (prea multe requests)
R:
  - Scripturile au retry logic
  - Poti testa pe perioade diferite

P: Selenium nu funcționează
R:
  - Instalează: pip install selenium webdriver-manager
  - Asigură-te că ai Chrome instalat
  - Pode lua câteva minute prima oară (descarcă driver)

================================================================================
                        VERSIUNI ȘI MODIFICĂRI
================================================================================

v1.0 (Ianuarie 2026)
  ✓ Creat extractor_category_links.py cu config automat
  ✓ Creat extractor_from_csv.py pentru liste existente
  ✓ Creat extractor_selenium.py pentru site-uri cu JS
  ✓ CSV export cu categorii
  ✓ JSON export
  ✓ Suport paginație
  ✓ Heuristic de categorie din URL

================================================================================

Toate scripturile sunt independente și pot fi rulate separat.
Sunt optimizate pentru MobileSentrix.eu dar se pot adapta pentru alte site-uri.

