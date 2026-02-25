# 📋 Repo Overview – Ce e aici și ce face scriptul

Document pentru AI / developeri: **ce conține repo-ul**, **logica actuală a scriptului** și **ce s-a modificat** față de fișierele .txt (care pot fi depășite). **Citează acest fișier** ca să înțelegi exact ce există și ce se poate modifica.

---

## 1. Ce este acest repo

- **Scraper modular pe furnizori**: suportă **mai mulți furnizori** (nu doar MobileSentrix). În GUI există un **dropdown „Furnizor”**; fiecare furnizor are propriul folder în `suppliers/<nume>/` (config.json + sku_list.txt) și, unde e cazul, scraper dedicat în `src/scraper/`. Furnizorii disponibili sunt: **MobileSentrix**, **Foneday**, **MobileParts**, **MMS Mobile**, **MPS Mobile**, **ComponentiDigitali** (lista vine din `suppliers/*/config.json` cu `enabled: true`).
- Generează un **CSV** în format WooCommerce, gata pentru **import în Supabase** și sincronizare cu WooCommerce.
- **Nu** inserează direct în WooCommerce; doar creează CSV-ul + opțional **upload imagini pe WordPress** (Media), apoi importul se face manual sau prin alt flux (ex. Supabase).

---

## 2. Logica actuală (ce face scriptul)

### 2.0 Script modular pe furnizori

- **GUI:** tab Import – **dropdown „Furnizor”** (valorile din `suppliers/*/config.json` cu `enabled: true`). La schimbarea furnizorului se actualizează calea către fișierul de SKU-uri (ex. `suppliers/mobilesentrix/sku_list.txt`).
- **Factory:** `src/scraper/factory.py` – `ScraperFactory.list_available_suppliers()`, `ScraperFactory.get_scraper(supplier_name, app)`, `ScraperFactory.load_supplier_config(supplier_name)`, `ScraperFactory.get_sku_list_path(supplier_name)`.
- **Config per furnizor:** `suppliers/<nume>/config.json` – conține (printre altele) `name`, `display_name`, `enabled`, `sku_list_file`, **`skip_images`** (dacă `true`, nu se descarcă imagini – ex. furnizori cu watermark).
- **Scraper per furnizor:** în `src/scraper/` există clase pentru fiecare furnizor (ex. `MobileSentrixScraper`, `FonedayScraper`, `MobilepartsScraper`, etc.). La export se folosește scraperul pentru furnizorul selectat; dacă nu există sau nu e disponibil, se poate folosi `scrape_product()` direct (logică MobileSentrix în `import_gui.py`).
- **CSV:** câmpul **`meta:furnizor_activ`** vine din `product_data['furnizor_activ']` / `product_data['supplier']` setat de scraper (ex. `mobilesentrix`, `mmsmobile`), nu e hardcodat.

### 2.1 Intrare

- **Fișier:** depinde de furnizorul selectat – de obicei **`suppliers/<furnizor>/sku_list.txt`** (sau calea din `config.json` → `sku_list_file`). La furnizor „MobileSentrix” se poate folosi și `sku_list.txt` din rădăcină.
- **Conținut:** câte un produs per linie:
  - **URL direct:** ex. `https://www.mobilesentrix.eu/nume-produs/`
  - **URL cu cod categorie:** `https://... | BAT` (pipe + cod din `CATEGORY_CODE_MAP`)
  - **SKU/EAN:** 12–13 cifre (căutare pe site)

### 2.2 Flux principal (butonul de export din GUI)

1. Citește `sku_list.txt` → listă de `{url, code?}`.
2. Pentru fiecare intrare:
   - **Scrape** prin scraperul furnizorului selectat (sau fallback pe logică MobileSentrix în `import_gui.py`): nume, preț EUR, descriere, imagini, SKU furnizor, EAN. Dacă în config furnizorului e **`skip_images: true`**, nu se descarcă imagini (ex. watermark).
   - **Download imagini** în `images/` (dacă e bifat „Descarcă imagini”).
   - Opțional **Ollama**: traducere/adaptare nume, tip produs, descriere, SEO (dacă `OLLAMA_URL` e setat în `.env`).
   - Altfel: **Google Translate** + logică internă pentru titlu/tip.
   - **Categorii:** `get_woo_category()` → path (ex. `Piese > Piese iPhone > Ecrane`); `get_webgsm_category()` → slug (ex. `ecrane-iphone`). Cod manual din `sku_list` (ex. `| BAT`) are prioritate.
   - **Upload imagini** pe WordPress (Media) – dacă în `.env` există `WP_USERNAME` + `WP_APP_PASSWORD` (utilizator WordPress real + Application Password, **nu** Consumer Key/Secret).
   - Construiește rândul pentru CSV (vezi secțiunea CSV mai jos).
3. Scrie **un singur CSV** în `data/export_webgsm_TIMESTAMP.csv`.

### 2.3 CSV generat – reguli actuale

- **SKU:** mereu **gol**. SKU-ul intern (100001, 100002, …) se generează în **Supabase** la import; scriptul nu decide SKU.
- **EAN / GTIN:** `meta:gtin_ean`, coloana „GTIN, UPC, EAN, or ISBN” și `meta:sku_furnizor` – în cod sunt cu **apostrof** în față pentru Excel (păstrare cifre ca text). Dacă vrei strict **fără apostrof**, trebuie schimbat în `import_gui.py` (assign la `ean_text` și `sku_furnizor` fără `"'" +`).
- **Stoc:** `In stock?` = `0`, `Stock` = `0` (nu avem stoc real; nu se mai pune 100).
- **Preț achiziție:** `meta:pret_achizitie` = **preț în EUR** de pe site-ul furnizorului (nu convertit în lei).
- **Brand (Atribut 3):** brand **real** din titlul furnizorului (Ampsentrix, I2C, Wiha, Qianli, etc.), **nu** calitatea (Premium OEM, Aftermarket).
- **Atribut 4:** Tip Produs (Baterie, Ecran, Cablu/Încărcător, Unealtă, etc.) – ghicit din categorie (`CATEGORY_TO_TYPE`).
- **Atribut 5:** Tehnologie (OLED, LCD, etc.).
- **Toate atributele (1–5):** `global` = `0` (atribute custom pe produs).
- **Coloane suplimentare:** GTIN/UPC/EAN or ISBN, Low stock amount = 3, Backorders allowed? (0 sau notify la precomandă), Allow customer reviews? = 1; Published = 0 (draft).

#### Verificare cerințe CSV (fix-urile inițiale)

| # | Cerință | În cod (import_gui.py) | Status |
|---|--------|-------------------------|--------|
| 1 | SKU = gol | `sku_value = ''` | ✅ |
| 2 | EAN/sku_furnizor ca text (evită 1.07E+11) | Apostrof în față (`'` + valoare); dacă ceri fără apostrof, se poate scoate | ✅ (cu apostrof) |
| 3 | Stoc = 0 | `in_stock = '0'`, `stock_value = '0'` | ✅ |
| 4 | Brand = brand real (nu calitate) | `brand_real = _extract_real_brand(clean_name)`; Atribut 3 value = brand_real | ✅ |
| 5 | Atribut 4 = Tip Produs, Atribut 5 = Tehnologie | `tip_produs = _guess_product_type(categories)`; row Attribute 4/5 | ✅ |
| 6 | Attribute global = 0 | Toate Attribute 1–5 global = `'0'` | ✅ |
| 7 | Coloane: GTIN, Low stock amount, Backorders, Allow reviews, Published=0 | În fieldnames și în row | ✅ |
| – | meta:pret_achizitie = EUR furnizor | `f"{price_eur:.2f}"` | ✅ |

### 2.4 Categorii

- Slug-uri permise: cele din arborele WebGSM (ex. `ecrane-iphone`, `baterii-samsung`, `surubelnite`, `folii-protectie`). **Nu** se folosesc: `accesorii-service`, `ecrane-telefoane`, `baterii-telefoane`, `baterii-iphone-piese`, `camere-iphone-piese`.

### 2.5 Imagini

- Se descarcă local, apoi se uploadează pe WordPress (Media). În CSV se pun **doar URL-uri de pe domeniul tău** (link-urile directe MobileSentrix sunt filtrate). Dacă lipsește `WP_APP_PASSWORD`, upload-ul eșuează și în CSV pot rămâne mai puține imagini sau niciuna.

### 2.6 Ollama

- Opțional: traducere/adaptare nume, tip produs, descriere, SEO. În `.env`: `OLLAMA_URL=http://IP:11434`. Pe mașina unde rulează Ollama trebuie pornit cu **OLLAMA_HOST=0.0.0.0** ca să fie vizibil pe rețea. Scriptul oferă buton „Verifică Ollama pe rețea” în tab Configurare.

---

## 3. Modificări importante (față de versiuni vechi / .txt)

| Ce | Stare actuală |
|----|----------------|
| SKU în CSV | Gol (generat în Supabase) |
| EAN / meta:gtin_ean / meta:sku_furnizor | Cifre fără apostrof |
| Stock | 0 (nu 100) |
| meta:pret_achizitie | EUR (de pe furnizor) |
| Brand (Atribut 3) | Brand real din titlu (nu calitate) |
| Atribut 4 | Tip Produs (din categorie) |
| Atribut 5 | Tehnologie |
| Attribute global | 0 pentru toate |
| Coloane CSV | + GTIN/UPC/EAN or ISBN, Low stock amount, Backorders allowed?, Allow customer reviews? |
| Description (CSV) | Structură h3/p: „Titlu: conținut” → h3 + p; restul în p (_build_description_html) |
| Test Conexiune WooCommerce | Import `from woocommerce import API`; citește și din .env |
| Upload imagini | Doar WP_USERNAME + WP_APP_PASSWORD (nu Consumer Key ca user) |
| Verificare Ollama | Buton în Configurare + script `check_ollama.py`, `start_ollama_network.bat` / `.sh` |
| **Script modular pe furnizori** | Dropdown furnizor în GUI, `ScraperFactory`, `suppliers/<nume>/config.json` + `sku_list.txt`, scraper per furnizor în `src/scraper/` (MobileSentrix, Foneday, MobileParts, MMS Mobile, MPS Mobile, ComponentiDigitali), `skip_images` în config, `meta:furnizor_activ` din scraper. |

Fișierele **.txt** din repo (GHID_*, CURATA_*, DUPLICATE_*, etc.) pot descrie fluxuri vechi sau pași manuale; **sursa de adevăr pentru comportamentul scriptului este codul din `import_gui.py`** și acest OVERVIEW.

---

## 4. Index fișiere – ce citești pentru ce

### 4.1 Documentație principală (sursă de adevăr)

| Fișier | Rol |
|--------|-----|
| **REPO_OVERVIEW.md** (acest fișier) | Ce face repo-ul, logica actuală, **modular furnizori**, modificări, index fișiere. **Start aici** pentru context complet. |
| **README.md** | Prezentare scurtă, instalare, configurare, linkuri. |
| **PROGRAM_ARCHITECTURE.md** | Arhitectură tehnică, flux, funcții importante, categorii WebGSM. |
| **PLAN_IMPLEMENTARE_MULTI_FURNIZOR.md** | Plan implementare multi-furnizor (ScraperFactory, dropdown, suppliers/). |
| **ARHITECTURA_MULTI_FURNIZOR.md** | Arhitectură modulară furnizori, clase scraper, config per furnizor. |
| **suppliers/README.md** | Reguli pentru folderul suppliers: config per furnizor, **watermark** și `skip_images`. |
| **ANALIZA_FURNIZORI.md** | Analiză furnizori, config template per furnizor, reguli imagini. |

### 4.2 Ghiduri utilizare / setup

| Fișier | Conține |
|--------|--------|
| **GHID_RAPID_CSV.txt** | Pași rapizi export CSV, unde sunt rezultatele, opțiuni recomandate. |
| **GHID_UTILIZARE.txt** | Documentație utilizare mai detaliată. |
| **README_START.txt** | Pornire rapidă, prima rulare. |
| **INDEX_FISIERE.txt** | Index vechi al fișierelor; versiunea Python (import_gui) e cea recomandată. |
| **SETUP_GHID.txt** | Setup inițial. |
| **START_PROGRAM.txt** | Cum pornești programul. |

### 4.3 Categorii / reguli

| Fișier | Conține |
|--------|--------|
| **category_rules.txt** | Reguli keyword → cale categorie (folosite unde se apelează `detect_category`). |
| **category_config.txt** / **category_config_auto.txt** | Configurare categorii. |

### 4.4 Extractoare / fluxuri alternative

| Fișier | Conține |
|--------|--------|
| **README_EXTRACTOARE.txt** | Info despre extractoare. |
| **EXTRACTOARE_INDEX.txt**, **EXTRACTOARE_SUMMARY.txt** | Index și sumar extractoare. |
| **GHID_EXTRACTOARE.txt** | Ghid extractoare. |
| **START_HERE_EXTRACTOARE.txt** | Punct de start pentru extractoare. |

### 4.5 Curățare / reparații / diagnoză

| Fișier | Conține |
|--------|--------|
| **CURATA_NUCLEAR.txt** | Proceduri curățare „nucleară”. |
| **CURATA_ORFANE_GHID.txt** | Ghid curățare produse orfane. |
| **DUPLICATE_SKU_FIX.txt** | Remediere duplicate SKU. |
| **URGENT_DATABASE_REPAIR.txt** | Reparații urgente bază de date. |
| **DIAGNOZA_AUTO_INCREMENT.txt**, **DIAGNOZA_EROARE_400.txt** | Diagnoze tehnice. |
| **DISCOVERY_15_01_2026.txt** | Note discovery. |
| **PHANTOM_PRODUCTS_GUIDE.txt** | Ghid produse fantomă. |
| **EROARE_500_FIX.txt**, **CONFIG_FIX_README.txt** | Fix-uri erori / config. |
| **ROOT_CAUSE_ANALYSIS.txt** | Analize cauză. |

### 4.6 Alte .txt (referință / istoric)

| Fișier | Conține |
|--------|--------|
| **IMPORT_FISIER_GHID.txt** | Import din fișier. |
| **README_MOD_CSV.txt** | Modificări CSV. |
| **PROIECT_COMPLET.txt**, **PROGRAM_GATA.txt** | Stare proiect / program. |
| **VERSIUNE_3_2_CHANGELOG.txt**, **VERSIUNE_3_3_CHANGELOG.txt** | Changelog-uri versiuni. |
| **QUICK_ACTION_15_01_2026.txt** | Acțiuni rapide. |
| **CLEANUP_COPY_PASTE.txt**, **CLEANUP_COPY_PASTE_FINAL.txt** | Cleanup copy-paste. |
| **MANUAL_CLEANUP_PHANTOM_5141-5145.txt** | Cleanup manual phantom. |

### 4.7 Configurare și scripturi

| Fișier | Rol |
|--------|-----|
| **.env** | Credențiale (WOOCOMMERCE_*, WP_USERNAME, WP_APP_PASSWORD, OLLAMA_URL, etc.). Nu se versionă. |
| **.env.example** | Template .env. |
| **sku_list.txt** | Lista de URL-uri / EAN-uri (poate fi în rădăcină sau per furnizor în `suppliers/<nume>/sku_list.txt`). |
| **requirements.txt** | Dependențe Python (inclusiv `woocommerce`). |
| **check_ollama.py** | Verifică dacă Ollama răspunde la OLLAMA_URL. |
| **start_ollama_network.bat** / **start_ollama_network.sh** | Pornesc Ollama cu OLLAMA_HOST=0.0.0.0 (vizibil pe rețea). |
| **src/scraper/** | Cod modular furnizori: `factory.py` (ScraperFactory), `base.py` (BaseScraper), `mobilesentrix.py`, `foneday.py`, `mobileparts.py`, `mmsmobile.py`, `mpsmobile.py`, `componentidigitali.py`. |
| **suppliers/** | Un folder per furnizor: `suppliers/<nume>/config.json` (name, display_name, enabled, sku_list_file, skip_images) și `sku_list.txt`. |

---

## 5. Ce se poate modifica / ce nu

- **Modifică fără griji:** reguli categorii, keyword-uri brand/tip, `.env`, `sku_list.txt`, `category_rules.txt`, constante din `import_gui.py` (ex. `MAX_IMAGES_IN_CSV`, `CATEGORY_TO_TYPE`, liste de branduri). **Furnizor nou:** adaugi folder `suppliers/<nume>/` cu `config.json` + `sku_list.txt` și, dacă e nevoie, o clasă scraper în `src/scraper/` + înregistrare în `factory.py`.
- **Modifică cu atenție:** fluxul de export (ordine câmpuri CSV, formule preț), logica de categorii (`get_woo_category`, `get_webgsm_category`), upload imagini (endpoint, auth). Asigură-te că CSV rămâne compatibil cu importul Supabase/WooCommerce.
- **Nu schimba** fără acord: formatul coloanelor CSV obligatorii pentru Supabase (SKU gol, nume coloane meta), semnătura funcțiilor folosite și în alte scripturi.

---

## 6. Versiune și dată

- **OVERVIEW:** actualizat pentru starea din 2026: **script modular pe furnizori** (dropdown, ScraperFactory, suppliers/, config per furnizor, skip_images, meta:furnizor_activ); SKU gol, EAN fără apostrof, stoc 0, meta:pret_achizitie EUR, brand real, atribute 4–5, global=0, coloane noi, upload WP, Ollama, test conexiune.
- **Sursă de adevăr:** `import_gui.py`, `src/scraper/`, `suppliers/` + acest `REPO_OVERVIEW.md`.
