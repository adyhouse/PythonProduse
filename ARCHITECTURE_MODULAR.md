# 🏗️ ARHITECTURĂ MODULARĂ - Plan de Refactorizare

## 📋 Analiză Structură Actuală

### Problema Actuală
- **Fișier monolitic**: `import_gui.py` cu **4700+ linii** într-o singură clasă
- **Responsabilități multiple**: GUI, scraping, traducere, categorii, CSV, imagini, badge-uri, config
- **Dificil de întreținut**: modificările afectează întregul cod
- **Dificil de testat**: dependențe între componente
- **Reutilizare limitată**: componentele nu pot fi folosite independent

### Obiective Modularizare
✅ **Separare responsabilități** în module distincte  
✅ **Cod mai ușor de întreținut** și testat  
✅ **Reutilizare componente** în alte proiecte  
✅ **Compatibilitate** cu funcționalitatea existentă  
✅ **Extensibilitate** pentru funcții noi  
✅ **Portabilitate** - schimbarea platformei (WooCommerce → Shopify/Next.js) fără modificări majore  

---

## 🎯 Arhitectură Propusă

```
PythonProduse/
├── src/                          # Cod sursă modular
│   ├── __init__.py
│   │
│   ├── core/                     # Logica de bază
│   │   ├── __init__.py
│   │   ├── config.py             # Configurare (.env, load/save)
│   │   ├── constants.py          # Constante globale (CATEGORY_CODE_MAP, etc.)
│   │   └── logger.py             # Sistem de logging
│   │
│   ├── scraper/                  # Web scraping
│   │   ├── __init__.py
│   │   ├── mobilesentrix.py      # Scraper MobileSentrix
│   │   ├── image_downloader.py   # Download imagini
│   │   └── availability.py      # Detectare disponibilitate
│   │
│   ├── processors/                # Procesare date
│   │   ├── __init__.py
│   │   ├── translator.py         # Traducere (Google Translate / Ollama)
│   │   ├── category_detector.py # Detectare categorii (get_woo_category, get_webgsm_category)
│   │   ├── title_builder.py       # Construire titlu Long Tail SEO
│   │   ├── warranty_detector.py  # Detectare garanție
│   │   └── sku_generator.py      # Generare SKU
│   │
│   ├── images/                    # Procesare imagini
│   │   ├── __init__.py
│   │   ├── uploader.py           # Upload WordPress
│   │   ├── badge/                # Badge-uri
│   │   │   ├── __init__.py
│   │   │   ├── generator.py      # Generare badge-uri
│   │   │   ├── preview.py        # Preview badge-uri (BadgePreviewWindow)
│   │   │   └── storage.py        # Salvare/încărcare badge-uri
│   │   └── optimizer.py          # Optimizare imagini
│   │
│   ├── export/                     # Export CSV
│   │   ├── __init__.py
│   │   ├── csv_exporter.py      # Export CSV WooCommerce
│   │   └── csv_fields.py        # Definiții coloane CSV
│   │
│   ├── woocommerce/               # Integrare WooCommerce
│   │   ├── __init__.py
│   │   ├── api.py                # API WooCommerce
│   │   └── cleanup.py            # Curățare produse orfane
│   │
│   │
│   ├── io/                        # Input/Output
│   │   ├── __init__.py
│   │   ├── file_reader.py        # Citire sku_list.txt
│   │   └── category_rules.py    # Încărcare reguli categorii
│   │
│   └── gui/                       # Interfață grafică
│       ├── __init__.py
│       ├── main_window.py        # Fereastra principală (ImportProduse)
│       ├── tabs/                 # Tab-uri GUI
│       │   ├── __init__.py
│       │   ├── import_tab.py     # Tab Export CSV
│       │   ├── config_tab.py     # Tab Configurare
│       │   └── log_tab.py        # Tab Log
│       └── widgets/              # Widget-uri custom
│           ├── __init__.py
│           └── progress.py      # Progress bar custom
│
├── tests/                         # Teste unitare
│   ├── __init__.py
│   ├── test_scraper.py
│   ├── test_processors.py
│   ├── test_category_detector.py
│   └── test_csv_exporter.py
│
├── data/                          # Date (există deja)
├── images/                        # Imagini (există deja)
├── logs/                          # Log-uri (există deja)
│
├── import_gui.py                  # Entry point (wrapper pentru compatibilitate)
├── requirements.txt               # Dependențe
├── .env.example                   # Template configurare
└── README.md                      # Documentație
```

---

## 📦 Module Detaliate

### 1. `core/` - Logica de Bază

#### `core/config.py`
```python
class Config:
    """Gestionare configurare .env"""
    - load_config()
    - save_config()
    - reload_config()
    - get(key, default)
    - set(key, value)
```

#### `core/constants.py`
```python
# Constante globale
- MAX_IMAGES_IN_CSV
- CATEGORY_TO_TYPE
- CATEGORY_CODE_MAP
- PIESE_TIP_KEYWORDS
- UNELTE_SUBCAT_KEYWORDS
- ACCESORII_SUBCAT_KEYWORDS
```

#### `core/logger.py`
```python
class Logger:
    """Sistem de logging centralizat"""
    - log(message, level)
    - setup_file_logging()
    - get_log_text()
```

---

### 2. `scraper/` - Web Scraping

#### `scraper/mobilesentrix.py`
```python
class MobileSentrixScraper:
    """Scraper pentru MobileSentrix"""
    - scrape_product(url_or_ean)
    - _extract_product_data(soup)
    - _find_product_url(ean)
    - _parse_price(price_text)
    - _extract_images(soup)
    - _extract_description(soup)
    - _extract_sku_ean(soup)
```

#### `scraper/image_downloader.py`
```python
class ImageDownloader:
    """Download și procesare imagini"""
    - download_images(image_urls, output_dir)
    - optimize_image(image_path, max_size)
    - generate_seo_filename(title, ext, index)
```

#### `scraper/availability.py`
```python
class AvailabilityDetector:
    """Detectare disponibilitate produs"""
    - detect_availability(soup, page_text)
    - is_in_stock()
    - is_preorder()
    - is_out_of_stock()
```

---

### 3. `processors/` - Procesare Date

#### `processors/translator.py`
```python
class Translator:
    """Traducere text (Google Translate / Ollama)"""
    - translate_text(text, source, target)
    - translate_via_ollama(text, field_type)
    - remove_diacritics(text)
    - ollama_generate_product_fields(...)
```

#### `processors/category_detector.py`
```python
class CategoryDetector:
    """Detectare categorii WooCommerce"""
    - get_woo_category(product_name, manual_code, ...)
    - get_webgsm_category(product_name, ...)
    - load_category_rules(filepath)
    - _detect_brand(text)
    - _detect_product_type(text)
```

#### `processors/title_builder.py`
```python
class TitleBuilder:
    """Construire titlu Long Tail SEO"""
    - build_longtail_title(product_name, description, attrs)
    - _extract_piece_name(text)
    - _extract_phone_model(text)
    - _extract_quality(text)
    - _extract_color(text)
```

#### `processors/warranty_detector.py`
```python
class WarrantyDetector:
    """Detectare garanție automată"""
    - detect_warranty(product_name, category)
    - _get_warranty_by_type(product_type)
```

#### `processors/sku_generator.py`
```python
class SKUGenerator:
    """Generare SKU"""
    - generate_webgsm_sku(product_name, brand, counter, ...)
    - generate_unique_sku(ean)  # Legacy
    - _get_type_code(product_name, manual_code)
    - _get_model_code(product_name)
```

---

### 4. `images/` - Procesare Imagini

#### `images/uploader.py`
```python
class WordPressUploader:
    """Upload imagini pe WordPress Media"""
    - upload_image(image_path)
    - upload_images_parallel(image_paths)
    - _get_wp_credentials()
    - _upload_single_image(image_path)
```

#### `images/badge/generator.py`
```python
class BadgeGenerator:
    """Generare badge-uri pe imagini"""
    - generate_badge_preview(image_path, badge_data, output_path, style)
    - _draw_badge(image, badge_data, style)
    - _get_badge_fonts()
```

#### `images/badge/preview.py`
```python
class BadgePreviewWindow:
    """Fereastră preview badge-uri"""
    - __init__(root, image_path, detected_data, on_done, ...)
    - setup_ui()
    - on_confirm()
    - on_batch()
```

#### `images/badge/storage.py`
```python
class BadgeStorage:
    """Salvare/încărcare badge-uri"""
    - load_custom_brands(script_dir)
    - save_custom_brand(script_dir, brand_name)
    - load_badge_presets_by_brand(script_dir)
    - save_badge_preset_for_brand(...)
```

---

### 5. `export/` - Export CSV

#### `export/csv_exporter.py`
```python
class CSVExporter:
    """Export produse în CSV WooCommerce"""
    - export_to_csv(products_data, filename)
    - _build_csv_row(product, config)
    - _process_product_images(product)
    - _calculate_price(product, convert_price)
```

#### `export/csv_fields.py`
```python
# Definiții coloane CSV
CSV_FIELDNAMES = [
    'ID', 'Type', 'SKU', 'GTIN, UPC, EAN, or ISBN', ...
]

CSV_DEFAULTS = {
    'Type': 'simple',
    'Published': '0',
    'In stock?': '0',
    'Stock': '0',
    ...
}
```

---

### 6. `woocommerce/` - Integrare WooCommerce

#### `woocommerce/api.py`
```python
class WooCommerceAPI:
    """API WooCommerce"""
    - __init__(url, consumer_key, consumer_secret)
    - test_connection()
    - get_products(params)
    - create_product(product_data)
```

#### `woocommerce/cleanup.py`
```python
class ProductCleanup:
    """Curățare produse orfane"""
    - cleanup_orphans(api)
    - find_orphans(products)
    - delete_product(product_id)
```

---

### 7. `io/` - Input/Output

#### `io/file_reader.py`
```python
class SKUFileReader:
    """Citire sku_list.txt"""
    - read_sku_file(filepath)
    - _parse_line(line)
    - _extract_url_and_code(line)
```

#### `io/category_rules.py`
```python
class CategoryRulesLoader:
    """Încărcare reguli categorii"""
    - load_category_rules(filepath)
    - _parse_rule_line(line)
```

---

### 8. `gui/` - Interfață Grafică

#### `gui/main_window.py`
```python
class ImportProduse:
    """Fereastră principală GUI"""
    - __init__(root)
    - setup_gui()
    - start_import()
    - stop_import()
    - run_import()  # Thread principal
```

#### `gui/tabs/import_tab.py`
```python
class ImportTab:
    """Tab Export CSV"""
    - setup_import_tab(parent)
    - _setup_sku_file_selector()
    - _setup_options()
    - _setup_progress()
```

#### `gui/tabs/config_tab.py`
```python
class ConfigTab:
    """Tab Configurare"""
    - setup_config_tab(parent)
    - _setup_woocommerce_fields()
    - _setup_ollama_fields()
    - on_save_config()
    - on_test_connection()
```

#### `gui/tabs/log_tab.py`
```python
class LogTab:
    """Tab Log"""
    - setup_log_tab(parent)
    - update_log(message, level)
    - clear_log()
```

---

## 🔄 Flux de Date Modulat

```
┌─────────────────────────────────────────────────────────────┐
│                    GUI (main_window.py)                      │
│                    ┌──────────────┐                          │
│                    │  ImportTab   │                          │
│                    └──────┬───────┘                          │
└───────────────────────────┼──────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              IO (file_reader.py)                             │
│              read_sku_file() → [{url, code}, ...]            │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│         Scraper (mobilesentrix.py)                           │
│         scrape_product() → {name, price, images, ...}        │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│         Processors (multiple)                               │
│         ├─ translator.py → translate_text()                │
│         ├─ category_detector.py → get_woo_category()        │
│         ├─ title_builder.py → build_longtail_title()        │
│         ├─ warranty_detector.py → detect_warranty()         │
│         └─ sku_generator.py → generate_webgsm_sku()         │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│         Images (uploader.py)                                 │
│         upload_images_parallel() → [wp_urls]                │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│         Export (csv_exporter.py)                             │
│         export_to_csv() → CSV file                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Plan de Migrare

### Faza 1: Creare Structură Module (Fără modificări funcționale)
1. ✅ Creare folder `src/` cu structura de directoare
2. ✅ Mutare constante în `core/constants.py`
3. ✅ Creare clase wrapper pentru compatibilitate

### Faza 2: Migrare Module Individuale
1. ✅ Migrare `core/` (config, constants, logger)
2. ✅ Migrare `scraper/` (mobilesentrix, image_downloader)
3. ✅ Migrare `processors/` (translator, category_detector, etc.)
4. ✅ Migrare `images/` (uploader, badge)
5. ✅ Migrare `export/` (csv_exporter)
6. ✅ Migrare `woocommerce/` (api, cleanup)
7. ✅ Migrare `io/` (file_reader, category_rules)

### Faza 3: Migrare GUI
1. ✅ Separare GUI în module (`gui/main_window.py`, `gui/tabs/`)
2. ✅ Actualizare `import_gui.py` să folosească modulele noi
3. ✅ Testare compatibilitate completă

### Faza 4: Teste și Documentație
1. ✅ Scriere teste unitare pentru fiecare modul
2. ✅ Actualizare documentație
3. ✅ Cleanup cod vechi

---

## ✅ Beneficii Arhitectură Modulară

1. **Mentenabilitate**: Fiecare modul are responsabilitate clară
2. **Testabilitate**: Modulele pot fi testate independent
3. **Reutilizare**: Modulele pot fi folosite în alte proiecte
4. **Extensibilitate**: Ușor de adăugat funcții noi
5. **Colaborare**: Echipe diferite pot lucra pe module diferite
6. **Debugging**: Mai ușor de identificat probleme

---

## 🔧 Compatibilitate

Pentru a menține compatibilitatea cu codul existent:
- `import_gui.py` rămâne entry point
- Import-urile din modulele noi sunt transparente
- Funcționalitatea rămâne identică
- Configurarea rămâne aceeași (`.env`, `sku_list.txt`)

---

---

**Data creare**: 19.02.2026  
**Status**: Planificare  
**Versiune**: 1.0
