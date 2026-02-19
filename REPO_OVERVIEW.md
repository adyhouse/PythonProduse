# 📋 Repo Overview – Ce e aici și ce face scriptul

Document pentru AI / developeri: **ce conține repo-ul**, **logica actuală a scriptului** și **ce s-a modificat** față de fișierele .txt (care pot fi depășite). **Citează acest fișier** ca să înțelegi exact ce există și ce se poate modifica.

---

## 1. Ce este acest repo

- **Scraper** care extrage produse de pe **MobileSentrix** (URL-uri sau EAN/SKU din `sku_list.txt`).
- Generează un **CSV** în format WooCommerce, gata pentru **import în Supabase** și sincronizare cu WooCommerce.
- **Nu** inserează direct în WooCommerce; doar creează CSV-ul + opțional **upload imagini pe WordPress** (Media), apoi importul se face manual sau prin alt flux (ex. Supabase).

---

## 2. Logica actuală (ce face scriptul)

### 2.1 Intrare

- **Fișier:** `sku_list.txt`
- **Conținut:** câte un produs per linie:
  - **URL direct:** `https://www.mobilesentrix.eu/nume-produs/`
  - **URL cu cod categorie:** `https://... | BAT` (pipe + cod din `CATEGORY_CODE_MAP`)
  - **SKU/EAN:** 12–13 cifre (căutare pe site)

### 2.2 Flux principal (butonul de export din GUI)

1. Citește `sku_list.txt` → listă de `{url, code?}`.
2. Pentru fiecare intrare:
   - **Scrape** pe MobileSentrix: nume, preț EUR, descriere, imagini, SKU furnizor, EAN (din pagină/JSON-LD).
   - **Download imagini** în `images/` (dacă e bifat „Descarcă imagini”).
   - Opțional **Ollama**: traducere/adaptare nume, tip produs, descriere, SEO (dacă `OLLAMA_URL` e setat în `.env`).
   - Altfel: **Google Translate** + logică internă pentru titlu/tip.
   - **Categorii:** `get_woo_category()` → path (ex. `Piese > Piese iPhone > Ecrane`); `get_webgsm_category()` → slug (ex. `ecrane-iphone`). Cod manual din `sku_list` (ex. `| BAT`) are prioritate.
   - **Upload imagini** pe WordPress (Media) – dacă în `.env` există `WP_USERNAME` + `WP_APP_PASSWORD` (utilizator WordPress real + Application Password, **nu** Consumer Key/Secret).
   - Construiește rândul pentru CSV (vezi secțiunea CSV mai jos).
3. Scrie **un singur CSV** în `data/export_webgsm_TIMESTAMP.csv`.

### 2.3 CSV generat – reguli actuale

- **SKU:** mereu **gol**. SKU-ul intern (100001, 100002, …) se generează în **Supabase** la import; scriptul nu decide SKU.
- **EAN / GTIN:** `meta:gtin_ean`, coloana „GTIN, UPC, EAN, or ISBN” și `meta:sku_furnizor` – **cifre fără apostrof** (s-au scos prefixele cu `'`).
- **Stoc:** `In stock?` = `0`, `Stock` = `0` (nu avem stoc real; nu se mai pune 100).
- **Preț achiziție:** `meta:pret_achizitie` = **preț în EUR** de pe site-ul furnizorului (nu convertit în lei).
- **Brand (Atribut 3):** brand **real** din titlul furnizorului (Ampsentrix, I2C, Wiha, Qianli, etc.), **nu** calitatea (Premium OEM, Aftermarket).
- **Atribut 4:** Tip Produs (Baterie, Ecran, Cablu/Încărcător, Unealtă, etc.) – ghicit din categorie (`CATEGORY_TO_TYPE`).
- **Atribut 5:** Tehnologie (OLED, LCD, etc.).
- **Toate atributele (1–5):** `global` = `0` (atribute custom pe produs).
- **Coloane suplimentare:** GTIN/UPC/EAN or ISBN, Low stock amount, Backorders allowed?, Allow customer reviews?; Published = 0 (draft).

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
| Test Conexiune WooCommerce | Import `from woocommerce import API`; citește și din .env |
| Upload imagini | Doar WP_USERNAME + WP_APP_PASSWORD (nu Consumer Key ca user) |
| Verificare Ollama | Buton în Configurare + script `check_ollama.py`, `start_ollama_network.bat` / `.sh` |

Fișierele **.txt** din repo (GHID_*, CURATA_*, DUPLICATE_*, etc.) pot descrie fluxuri vechi sau pași manuale; **sursa de adevăr pentru comportamentul scriptului este codul din `import_gui.py`** și acest OVERVIEW.

---

## 4. Index fișiere – ce citești pentru ce

### 4.1 Documentație principală (sursă de adevăr)

| Fișier | Rol |
|--------|-----|
| **REPO_OVERVIEW.md** (acest fișier) | Ce face repo-ul, logica actuală, modificări, index fișiere. **Start aici** pentru context complet. |
| **README.md** | Prezentare scurtă, instalare, configurare, linkuri. |
| **PROGRAM_ARCHITECTURE.md** | Arhitectură tehnică, flux, funcții importante, categorii WebGSM. |

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
| **sku_list.txt** | Lista de URL-uri / EAN-uri de procesat. |
| **requirements.txt** | Dependențe Python (inclusiv `woocommerce`). |
| **check_ollama.py** | Verifică dacă Ollama răspunde la OLLAMA_URL. |
| **start_ollama_network.bat** / **start_ollama_network.sh** | Pornesc Ollama cu OLLAMA_HOST=0.0.0.0 (vizibil pe rețea). |

---

## 5. Ce se poate modifica / ce nu

- **Modifică fără griji:** reguli categorii, keyword-uri brand/tip, `.env`, `sku_list.txt`, `category_rules.txt`, constante din `import_gui.py` (ex. `MAX_IMAGES_IN_CSV`, `CATEGORY_TO_TYPE`, liste de branduri).
- **Modifică cu atenție:** fluxul de export (ordine câmpuri CSV, formule preț), logica de categorii (`get_woo_category`, `get_webgsm_category`), upload imagini (endpoint, auth). Asigură-te că CSV rămâne compatibil cu importul Supabase/WooCommerce.
- **Nu schimba** fără acord: formatul coloanelor CSV obligatorii pentru Supabase (SKU gol, nume coloane meta), semnătura funcțiilor folosite și în alte scripturi.

---

## 6. Versiune și dată

- **OVERVIEW:** actualizat pentru starea din 2026 (SKU gol, EAN fără apostrof, stoc 0, meta:pret_achizitie EUR, brand real, atribute 4–5, global=0, coloane noi, upload WP, Ollama, test conexiune).
- **Sursă de adevăr:** `import_gui.py` + acest `REPO_OVERVIEW.md`.
