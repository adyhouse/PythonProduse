# 📚 Analiză Documentație MD - PythonProduse

## 📋 Documente Disponibile

Proiectul conține **4 documente MD principale**:

1. **REPO_OVERVIEW.md** - Overview complet, logica actuală, modificări, index fișiere
2. **PROGRAM_ARCHITECTURE.md** - Arhitectură tehnică detaliată, flux, funcții
3. **README.md** - Prezentare scurtă, instalare, configurare
4. **ARCHITECTURE_MODULAR.md** - Plan de refactorizare modulară (nou creat)

---

## 🔍 Analiză Conținut

### 1. REPO_OVERVIEW.md - Ce spune?

**Scop:** Document pentru AI/developeri - ce conține repo-ul și logica actuală

**Puncte cheie:**
- **Scraper** MobileSentrix → CSV WooCommerce/Supabase
- **Nu** inserează direct în WooCommerce; doar CSV + upload imagini WordPress
- **SKU gol** în CSV (generat în Supabase)
- **Stoc 0** (nu avem stoc real)
- **Preț achiziție în EUR** (`meta:pret_achizitie`)
- **Brand real** (Atribut 3), nu calitatea
- **Atribute 1-5:** Model, Calitate, Brand, Tip Produs, Tehnologie (toate `global=0`)
- **Categorii:** `get_woo_category()` → path, `get_webgsm_category()` → slug
- **Ollama opțional** pentru traducere/adaptare
- **Upload imagini** pe WordPress Media (WP_USERNAME + WP_APP_PASSWORD)

**Flux principal:**
1. Citește `sku_list.txt` → `{url, code?}`
2. Pentru fiecare: scrape → download imagini → traducere → categorii → upload imagini → CSV
3. Scrie CSV în `data/export_webgsm_TIMESTAMP.csv`

---

### 2. PROGRAM_ARCHITECTURE.md - Ce spune?

**Scop:** Arhitectură tehnică detaliată, flux, funcții importante

**Puncte cheie:**

#### Structură Clasă Principală
```python
class ImportProduse:
    - __init__(root)
    - setup_gui()
    - read_sku_file()
    - scrape_product()
    - generate_unique_sku()
    - build_longtail_title()
    - get_woo_category() / get_webgsm_category()
    - detect_warranty()
    - translate_text()
    - export_to_csv()
```

#### Funcții Principale Identificate:

1. **read_sku_file()** - Citește EAN-uri/URL-uri din sku_list.txt
2. **scrape_product()** - Extrage date de pe MobileSentrix
3. **generate_unique_sku()** - Generează SKU EAN-13 (legacy)
4. **build_longtail_title()** - Construiește titlu SEO: [Piesa] [Model] [Calitate] [Culoare]
5. **get_woo_category()** - Returnează path categorie (ex: `Piese > Piese iPhone > Ecrane`)
6. **get_webgsm_category()** - Returnează slug categorie (ex: `ecrane-iphone`)
7. **detect_warranty()** - Detectare automată garanție
8. **translate_text()** - Traducere Google Translate / Ollama
9. **export_to_csv()** - Export CSV WooCommerce

#### Flux Logic:
```
START → Citire sku_list.txt → Loop produse → Scrape → Procesare → CSV → END
```

#### Variabile Globale:
- `MAX_IMAGES_IN_CSV = 5`
- `CATEGORY_TO_TYPE` - Mapare categorie → Tip Produs
- `CATEGORY_CODE_MAP` - Coduri manuale (SCR, BAT, TOOL, etc.)
- `PIESE_TIP_KEYWORDS` - Keywords pentru tipuri piese
- `UNELTE_SUBCAT_KEYWORDS` - Keywords pentru unelte
- `ACCESORII_SUBCAT_KEYWORDS` - Keywords pentru accesorii

---

### 3. README.md - Ce spune?

**Scop:** Prezentare scurtă, instalare, configurare

**Puncte cheie:**
- Program pentru scraping MobileSentrix → CSV WooCommerce/Supabase
- Caracteristici: scraping, download imagini, traducere, titluri SEO, SKU EAN-13, garanție automată
- Instalare: `pip install -r requirements.txt`, configurează `.env`, rulează `python import_gui.py`
- Format CSV: SKU gol, stoc 0, preț achiziție EUR, atribute 1-5
- Link către REPO_OVERVIEW.md și PROGRAM_ARCHITECTURE.md pentru detalii

---

### 4. ARCHITECTURE_MODULAR.md - Ce propune?

**Scop:** Plan de refactorizare modulară

**Problema identificată:**
- Fișier monolitic `import_gui.py` cu 4700+ linii
- Responsabilități multiple într-o singură clasă
- Dificil de întreținut și testat

**Soluție propusă:**
- Separare în 8 module principale:
  1. `core/` - Config, constante, logger
  2. `scraper/` - Web scraping MobileSentrix
  3. `processors/` - Traducere, categorii, titluri, garanție, SKU
  4. `images/` - Upload WordPress, badge-uri
  5. `export/` - Export CSV
  6. `woocommerce/` - API WooCommerce
  7. `io/` - Citire fișiere
  8. `gui/` - Interfață grafică Tkinter

**Plan migrare:**
- Faza 1: Creare structură (fără modificări funcționale)
- Faza 2: Migrare module individuale
- Faza 3: Migrare GUI
- Faza 4: Teste și documentație

---

## 🎯 Concluzii pentru Arhitectură Modulară

### Ce trebuie să păstrăm:
✅ **Funcționalitatea existentă** - CSV cu SKU gol, stoc 0, preț EUR, atribute  
✅ **Fluxul actual** - sku_list.txt → scrape → procesare → CSV  
✅ **Compatibilitate** - `import_gui.py` rămâne entry point  
✅ **Configurarea** - `.env`, `sku_list.txt`, `category_rules.txt`  

### Ce trebuie să modularizăm:
✅ **Scraper** - Separare logică scraping MobileSentrix  
✅ **Procesori** - Traducere, categorii, titluri, garanție, SKU  
✅ **Imagini** - Download, upload WordPress, badge-uri  
✅ **Export** - Generare CSV  
✅ **GUI** - Separare tab-uri și widget-uri  
✅ **Config** - Gestionare configurare centralizată  

### Module Identificate din Documentație:

#### Din PROGRAM_ARCHITECTURE.md:
- `read_sku_file()` → `io/file_reader.py`
- `scrape_product()` → `scraper/mobilesentrix.py`
- `generate_unique_sku()` → `processors/sku_generator.py`
- `build_longtail_title()` → `processors/title_builder.py`
- `get_woo_category()` / `get_webgsm_category()` → `processors/category_detector.py`
- `detect_warranty()` → `processors/warranty_detector.py`
- `translate_text()` → `processors/translator.py`
- `export_to_csv()` → `export/csv_exporter.py`
- Upload imagini → `images/uploader.py`
- Badge-uri → `images/badge/`

#### Din REPO_OVERVIEW.md:
- Constante globale → `core/constants.py`
- Configurare `.env` → `core/config.py`
- Logging → `core/logger.py`
- Category rules → `io/category_rules.py`

---

## 📊 Mapare Funcții → Module

| Funcție Actuală | Modul Propus | Fișier |
|----------------|--------------|--------|
| `read_sku_file()` | `io/` | `file_reader.py` |
| `scrape_product()` | `scraper/` | `mobilesentrix.py` |
| `generate_unique_sku()` | `processors/` | `sku_generator.py` |
| `build_longtail_title()` | `processors/` | `title_builder.py` |
| `get_woo_category()` | `processors/` | `category_detector.py` |
| `get_webgsm_category()` | `processors/` | `category_detector.py` |
| `detect_warranty()` | `processors/` | `warranty_detector.py` |
| `translate_text()` | `processors/` | `translator.py` |
| `export_to_csv()` | `export/` | `csv_exporter.py` |
| Upload imagini WordPress | `images/` | `uploader.py` |
| Badge preview | `images/badge/` | `preview.py` |
| Badge generator | `images/badge/` | `generator.py` |
| `load_config()` | `core/` | `config.py` |
| `load_category_rules()` | `io/` | `category_rules.py` |
| GUI setup | `gui/` | `main_window.py`, `tabs/` |

---

## ✅ Arhitectură Finală Recomandată

Bazată pe analiza documentelor MD, arhitectura modulară propusă este:

```
src/
├── core/          # Config, constante, logger
├── scraper/       # MobileSentrix scraping
├── processors/    # Traducere, categorii, titluri, garanție, SKU
├── images/        # Upload WordPress, badge-uri
├── export/        # CSV export
├── woocommerce/   # API WooCommerce
├── io/            # File I/O
└── gui/           # Tkinter GUI
```

**Compatibilitate:** `import_gui.py` rămâne entry point, folosește modulele noi intern.

---

**Data analiză**: 19.02.2026  
**Bazat pe**: REPO_OVERVIEW.md, PROGRAM_ARCHITECTURE.md, README.md
