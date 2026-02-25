# 📋 ARHITECTURA PROGRAM IMPORT PRODUSE - Documentație Tehnică Detaliată

> **Context actual:** pentru **logica curentă**, regulile CSV (SKU gol, stoc 0, EAN, meta:pret_achizitie EUR, atribute, etc.) și **indexul fișierelor** din repo, vezi **[REPO_OVERVIEW.md](REPO_OVERVIEW.md)**. Acest document descrie arhitectura și funcțiile din cod.

## 📌 OVERVIEW - Ce face programul?

Program pentru **export automizat de produse din MobileSentrix** către **CSV compatible cu WooCommerce**, cu:
- Web scraping de pe site-ul MobileSentrix
- Download imagini produse
- Upload imagini pe WordPress
- Traducere automate în română (fără diacritice)
- Titluri Long Tail SEO optimizate
- Generare coduri de bare (SKU format EAN-13)
- Detectare automată a garanțiilor
- Importare în WooCommerce

---

## 🏗️ SCHEMA LOGICĂ - FLUXUL PRINCIPAL

```
┌─────────────────────────────────────────────────────────────────┐
│                    START PROGRAM (GUI)                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. CITIRE DATE DIN FIȘIER (sku_list.txt)                       │
│     - Citește EAN-uri / URL-uri / SKU-uri                       │
│     - Returnează lista cu itemii                                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. LOOP PENTRU FIECARE PRODUS                                  │
│     (Pentru idx, sku din lista_produse)                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────────┐
        │  3. SCRAPE PRODUS DE PE MOBILESENTRIX  │
        │     ├─ Cauta pe site cu EAN/SKU        │
        │     ├─ Descarcă HTML pagină produsului │
        │     └─ Extrage date cu selectori CSS   │
        └────────────────────┬───────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
        ┌──────────────┐         ┌──────────────────┐
        │ EXTRAGE DATE │         │ DOWNLOAD IMAGINI │
        │              │         │                  │
        │ - Nume       │         │ - De pe site     │
        │ - Preț       │         │ - În folder local│
        │ - Descriere  │         │ - Redimensionare│
        │ - Imagini    │         └──────────────────┘
        │ - ID produs  │
        └──────────────┘
                │
                └────────────┬────────────┘
                             │
                             ▼
        ┌────────────────────────────────────────┐
        │  4. PROCESARE PRODUS (Transformări)    │
        │                                        │
        │  a) Generare SKU EAN-13:               │
        │     890 + [5 cifre din EAN] + 00000   │
        │                                        │
        │  b) Traducere titlu în română:         │
        │     - Google Translate                 │
        │     - Elimina diacritice              │
        │                                        │
        │  c) Construire titlu Long Tail:        │
        │     [Piesa] [Model] [Calitate] [Culoare]│
        │                                        │
        │  d) Detectare garantie automat         │
        │                                        │
        │  e) Upload imagini pe WordPress        │
        └────────────────────┬───────────────────┘
                             │
                             ▼
        ┌────────────────────────────────────────┐
        │  5. SALVARE ÎN LISTA PRODUSE (RAM)     │
        │     product_data = {                   │
        │       name, price, sku_generated,      │
        │       images, description, tags, ...   │
        │     }                                  │
        └────────────────────┬───────────────────┘
                             │
                             ▼
        ┌────────────────────────────────────────┐
        │  6. NEXT PRODUS (Merge la loop)        │
        └────────────────────┬───────────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │  (Cât timp mai sunt produse)            │
        └────────────────────┬────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  7. CREARE FIȘIER CSV                                           │
│     - Construiește CSV cu toți parametrii                       │
│     - Salvează în folder data/                                  │
│     - Format WooCommerce Import                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  8. IMPORT ÎN WOOCOMMERCE (Manual de utilizator)                │
│     - Deschide WooCommerce Admin                                │
│     - Products → Import                                         │
│     - Selectează CSV generat                                    │
│     - Finalizează import                                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    END - PRODUSE IMPORTATE                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 STRUCTURA CLASELOR - PYTHON

### **CLASA PRINCIPALĂ: ImportProduse**

```python
class ImportProduse:
    """Clasa principală pentru import produse din MobileSentrix"""
    
    def __init__(self, root):
        # Inițializare GUI și variabile globale
        self.root = root                    # Fereastra Tkinter
        self.running = False               # Flag pentru control procesare
        self.env_file = Path(".env")       # Fișier cu credențiale
        self.config = {}                   # Configurare WooCommerce
        self.category_rules = {}           # Reguli categorii
```

---

## 📍 FUNCȚIILE PRINCIPALE - Detalii Python

### **1️⃣ read_sku_file(filepath)**
```python
def read_sku_file(self, filepath):
    """
    SCOP: Citește din sku_list.txt EAN-uri sau URL-uri
    
    INPUT:
        filepath (str): Cale fișier cu EAN-uri
        
    OUTPUT:
        list: Lista cu EAN-uri/URL-uri de procesat
        
    LOGICĂ:
        ├─ Deschide fișierul
        ├─ Citește linie cu linie
        ├─ Ignora liniile goale și comentariile (#)
        └─ Returnează lista de itemi
        
    EXEMPLU:
        Input file (sku_list.txt):
            107182127516
            888888888888
            https://www.mobilesentrix.eu/produs-x
        
        Output: ['107182127516', '888888888888', 'https://...']
    """
```

### **2️⃣ scrape_product(ean)**
```python
def scrape_product(self, ean):
    """
    SCOP: Extrage date produs de pe MobileSentrix
    
    FLOW:
    
    A. DACĂ INPUT E URL DIRECT:
       ├─ Descarcă pagina
       └─ Merge la step D
    
    B. DACĂ INPUT E EAN:
       ├─ Caută pe Google: "site:mobilesentrix.eu" + EAN
       ├─ Extrage link din rezultate
       └─ Merge la step C
    
    C. DESCARCĂ PAGINA PRODUSULUI:
       ├─ requests.get(url) cu headers
       ├─ Parsare HTML cu BeautifulSoup
       └─ Merge la step D
    
    D. EXTRAGE DATE CU SELECTORI CSS:
       ├─ h1.page-title → product_name
       ├─ span.price → price
       ├─ img[alt*="product"] → images[]
       ├─ div.description → description
       └─ Merge la step E
    
    E. DOWNLOAD IMAGINI:
       ├─ Pentru fiecare imagine
       │  ├─ requests.get(img_url)
       │  ├─ PIL redimensionare la 1000x1000
       │  └─ Salvează în folder images/
       └─ Merge la step F
    
    F. RETURNEAZA DICT:
       {
           'name': 'iPhone 14',
           'price': 2500.00,
           'description': '...',
           'images': ['/path/img1.jpg', ...],
           'sku': '107182127516',
           ...
       }
    
    PARAMETRI IMPORTANȚI:
        - User-Agent: Setare pentru a nu fi blocat de site
        - Timeout: 30 secunde pentru request
        - Image max size: 1000x1000 px
    """
```

### **3️⃣ generate_unique_sku(ean)**
```python
def generate_unique_sku(self, ean):
    """
    SCOP: Generează SKU în format EAN-13 cu prefix 890
    
    FORMULĂ:
        SKU = "890" + sequential_id[5 cifre] + "00000"
        
    CALCUL sequential_id:
        - Extrage ultimele 5 cifre din EAN
        - Folosit % 100000 pentru a obține doar 5 cifre
        
    EXEMPLU:
        Input:  ean = "107182127516"
        
        Calcul:
            ean_int = 107182127516
            sequential_id = 107182127516 % 100000 = 27516
            sku = f"890{27516:05d}00000"
            
        Output: "8902751600000" (13 cifre - EAN-13)
    
    FORMAT FINAL:
        ┌──────┬──────────┬──────┐
        │ 890  │ 27516    │ 00000│
        └──────┴──────────┴──────┘
          GS1   ID Unic   Padding
        
    DE CE ACEST FORMAT?
        - 890: Prefix GS1 pentru utilizare internă
        - 5 cifre ID: Ușor de scris și memorat
        - 00000: Padding pentru EAN-13 standard (13 cifre)
        - Scanabil: Acceptat de orice scanner cod de bare
    """
```

### **4️⃣ build_longtail_title(product_name, description)**
```python
def build_longtail_title(self, product_name, description):
    """
    SCOP: Construire titlu SEO Long Tail: [Piesa] [Model] [Calitate] [Culoare]
    
    PROCES:
    
    STEP 1 - EXTRAGE PIESA:
        Dicționar cu keyword-uri:
        {
            'display': ['display', 'lcd', 'ecran', ...],
            'baterie': ['baterie', 'battery', ...],
            'carcasa': ['carcasa', 'casing', ...],
            ...
        }
        Caută în text și returnează piesa potrivită
        Default: 'Piesa'
    
    STEP 2 - EXTRAGE MODEL TELEFON:
        Lista hardcodată: ['iPhone 17', 'Samsung Galaxy S24', ...]
        Caută modele în text
        Default: 'Telefon'
    
    STEP 3 - EXTRAGE CALITATE:
        Dicționar:
        {
            'original': ['original', 'oem', 'genuin'],
            'premium': ['premium', 'high quality'],
            'compatible': ['compatible', 'aftermarket'],
            'standard': []
        }
        Default: 'Standard'
    
    STEP 4 - EXTRAGE CULOARE:
        Dicționar cu culori în RO și EN:
        {
            'Negru': ['negru', 'black'],
            'Alb': ['alb', 'white'],
            ...
        }
        Default: 'Standard'
    
    STEP 5 - CONSTRUIRE TITLU:
        longtail = f"{piece_name} {phone_model} {quality} {color}"
    
    EXEMPLU COMPLET:
        Input: "iPhone 14 Pro Display Original Black"
        
        Extrage:
            piece_name = "Display"
            phone_model = "iPhone 14"
            quality = "Original"
            color = "Negru"
        
        Output: "Display iPhone 14 Original Negru"
    
    SEO BENEFITS:
        - Long tail keywords
        - Specific și relevant
        - Crește CTR pe Google
        - Include model telefon (important!)
    """
```

### **5️⃣ Categorii WooCommerce (WebGSM)** {#categorii-woocommerce-webgsm}

Sistemul de categorii folosește două funcții complementare:

**a) `get_webgsm_category(product_name, product_type='', description='')`**  
Returnează **slug-ul** categoriei (ex: `ecrane-iphone`, `baterii-samsung`, `surubelnite`, `folii-protectie`). Folosit la export WebGSM (câmp `category_slug`). Analizează nume + descriere + tip; detectează brand (iPhone, Samsung, Huawei, Xiaomi, etc.) și tipul produsului; returnează doar slug-uri din arborele site-ului.

**b) `get_woo_category(product_name, product_type='', manual_code=None, description='', url_slug='', tags='')`**  
Returnează **path-ul** pentru coloana Categories din CSV (ex: `Piese > Piese iPhone > Ecrane`, `Unelte > Șurubelnițe`). Prioritate: cod manual din sku_list (link \| COD) → apoi detectare automată din titlu/URL/descriere/taguri.

**Arbore categorii (slug-uri valide):**

- **Piese** [piese] → Piese iPhone [piese-iphone]: ecrane-iphone, baterii-iphone, camere-iphone, carcase-iphone, difuzoare-iphone, flexuri-iphone, mufe-incarcare-iphone
- Piese Samsung / Huawei / Xiaomi: același tip de slug-uri (ecrane-samsung, baterii-huawei, etc.)
- **Unelte** [unelte]: surubelnite, pensete, statii-lipit, separatoare-ecrane, microscoape, programatoare, kituri-complete
- **Accesorii** [accesorii]: huse-carcase, folii-protectie, cabluri-incarcatoare, adezivi-consumabile
- **Dispozitive** [dispozitive]: telefoane-folosite, telefoane-refurbished, tablete, smartwatch
- **Servicii** [servicii]: reparatii, training, buy-back

**Slug-uri care NU EXISTĂ în site (nu se folosesc niciodată):**  
`accesorii-service`, `accesorii-service-xiaomi`, `baterii-iphone-piese`, `camere-iphone-piese`, `ecrane-telefoane`, `baterii-telefoane`.

**Coduri manuale (CATEGORY_CODE_MAP):**  
Dacă în sku_list este `URL | COD` (ex: SCR, BAT, TOOL), categoria se ia din mapare; pentru Piese se completează brandul din titlu/descriere. Codurile: SCR, BAT, CAM, CHG, FLX, SPK, CAS, STC (Piese); TOOL, PENS, SOLD, SEP, MICRO, PROG, KIT, EQP (Unelte); HUSA, FOIL, CBL, CNS (Accesorii).

---

### **6️⃣ detect_warranty(product_name, category)**
```python
def detect_warranty(self, product_name, category):
    """
    SCOP: Detectare automată a perioadei de garanție
    
    LOGICĂ - IF-ELIF LANȚ:
        
        IF 'display' OR 'lcd' OR 'ecran' IN text:
            return "12 luni"
        
        ELIF 'baterie' OR 'battery' IN text:
            return "6 luni"
        
        ELIF 'cablu' OR 'flex' IN text:
            return "6 luni"
        
        ELIF 'carcasa' OR 'casing' IN text:
            return "3 luni"
        
        ELIF 'accesoriu' OR 'protector' IN text:
            return "1-3 luni"
        
        ELSE:
            return "12 luni"  # Default
    
    EXEMPLU:
        Input: "LCD Display iPhone 14"
        Output: "12 luni"
        
        Input: "Baterie iPhone"
        Output: "6 luni"
    
    UNDE SE SALVEAZĂ:
        CSV Column: 'meta:_warranty_period'
        WooCommerce: postmeta (nu e vizibil frontend)
    """
```

### **7️⃣ remove_diacritics(text)**
```python
def remove_diacritics(self, text):
    """
    SCOP: Elimina diacritice din text (ă→a, ț→t, ș→s, etc.)
    
    LOGICĂ:
        1. import unicodedata
        2. unicodedata.normalize('NFKD', text)
           → Descompune caractere cu diacritice
           → "ă" devine "a" + diacritic_mark
        3. Filtrează caractere de diacritic
        4. Reune în string final
    
    EXEMPLU:
        Input:  "Aceasta este o descriere cu diacritice"
        
        Proces:
            normalize → separă caractere
            filtrare → elimina diacritice
        
        Output: "Aceasta este o descriere cu diacritice"
                (Note: aceasta devine aceasta, etc.)
    
    APLICARE:
        - În translate_text() dacă target='ro'
        - After Google Translate
    
    EXEMPLU REAL:
        Google Translate: "Baterie pentru telefon"
        After diacritice: "Baterie pentru telefon"
                (ă devine a, etc.)
    """
```

### **8️⃣ translate_text(text, source, target)**
```python
def translate_text(self, text, source='en', target='ro'):
    """
    SCOP: Traducere automată cu Google Translate
    
    PARAMETRI:
        text (str): Textul de tradus
        source (str): Limba sursă (default: 'en')
        target (str): Limba țintă (default: 'ro')
    
    FLOW:
        1. Check dacă text e gol → returnează original
        2. deep_translator.GoogleTranslator(source, target)
        3. IF len(text) > 4500 caractere:
               → Împarte în chunks
               → Traduce fiecare chunk
               → Unjoin
           ELSE:
               → Traduce direct
        4. IF target == 'ro':
               → Aplică remove_diacritics()
        5. Return text tradus
    
    PARAMETRI IMPORTANȚI:
        - Max length: 4500 caractere per request
        - Limita Google: Nu acceptă +5000 caractere
    
    EXEMPLU:
        Input: "iPhone 14 Display", target='ro'
        
        Process:
            → Google Translate: "Display iPhone 14"
            → Remove diacritice: "Display iPhone 14"
        
        Output: "Display iPhone 14"
    """
```

### **9️⃣ export_to_csv(products_data, filename)**
```python
def export_to_csv(self, products_data, filename):
    """
    SCOP: Export produse în CSV format WooCommerce
    
    PARAMETRI:
        products_data (list): Lista dicționare cu produse
        filename (str): Nume fișier output
    
    FLOW:
    
    A. SETUP CSV:
        ├─ Path: data/export_produse_TIMESTAMP.csv
        ├─ Encoding: UTF-8-SIG (cu BOM pentru Excel)
        └─ Fieldnames (coloane):
           ['ID', 'Type', 'SKU', 'EAN', 'Name', 'Published',
            'Is featured?', 'Visibility in catalog', 
            'Short description', 'Description', 'Tax status',
            'Tax class', 'In stock?', 'Stock', 'Regular price',
            'Categories', 'Tags', 'Images', 'Parent', 
            'meta:_warranty_period']
    
    B. PENTRU FIECARE PRODUS:
        
        1. Upload imagini pe WordPress:
           ├─ Pentru fiecare imagine local
           │  ├─ requests.post(wordpress_media_endpoint)
           │  ├─ Obține URL de pe WordPress
           │  └─ Salveaza URL-ul
           └─ Combina toate URL-urile cu virgulă
        
        2. Calculeaza preț RON:
           ├─ price_eur = product['price']
           ├─ IF convert_price checkbox:
           │  └─ price_ron = price_eur * EXCHANGE_RATE
           └─ ELSE:
              └─ price_ron = price_eur
        
        3. Curață nume:
           ├─ Elimina " Copy" de la sfârşit
           └─ Traduce în română
        
        4. Construire Long Tail:
           └─ longtail_title = build_longtail_title(...)
        
        5. Detectare garanție:
           └─ warranty = detect_warranty(...)
        
        6. Curață descriere:
           ├─ Max 500 caractere
           ├─ Elimina URL-uri cu regex
           └─ Traduce în română
        
        7. Construire rând CSV:
           ```
           row = {
               'ID': '',                    # Gol pentru produse noi
               'Type': 'simple',            # Tip produs
               'SKU': sku_value,            # SKU generat
               'EAN': ean_value,            # EAN furnizor (ascuns)
               'Name': longtail_title,      # Titlu Long Tail
               'Published': '1',            # Auto-publicat
               'Short description': ...,    # Max 160 char
               'Description': ...,          # Descriere complet
               'Regular price': price_ron,  # Preț în RON
               'meta:_warranty_period': warranty,  # Garanție
               ... altele
           }
           ```
        
        8. Scrie rând în CSV
    
    C. OUTPUT:
        ├─ Fișier CSV în data/
        ├─ Ready pentru WooCommerce import
        └─ Toate produse procesat cu date complete
    
    EXEMPLU RÂND CSV:
        | ID | Type | SKU | EAN | Name | Published | ... |
        |----|------|-----|-----|------|-----------|-----|
        |    | simple | 8902751600000 | 107182127516 | Display iPhone 14 Original Negru | 1 | ... |
    """
```

---

## 🗄️ VARIABILE GLOBALE IMPORTANTE

```python
# Configurare WooCommerce
self.config = {
    'WOOCOMMERCE_URL': 'https://webgsm.ro',
    'WOOCOMMERCE_CONSUMER_KEY': 'ck_...',
    'WOOCOMMERCE_CONSUMER_SECRET': 'cs_...',
    'EXCHANGE_RATE': 4.97  # EUR -> RON
}

# Directoare
Path("logs").mkdir(exist_ok=True)      # Pentru loguri
Path("images").mkdir(exist_ok=True)    # Pentru imagini descarcate
Path("data").mkdir(exist_ok=True)      # Pentru CSV generat

# Flag control
self.running = False  # True cand importul e activ

# Categoria reguli
self.category_rules = [
    ('iphone', 'Telefoane > Apple > iPhone'),
    ('samsung', 'Telefoane > Samsung'),
    ...
]
```

---

## 🔄 FLUXUL COMPLET - EXEMPLU REAL

```
INPUT: sku_list.txt
    107182127516
    888888888888

STEP 1: read_sku_file()
    → ['107182127516', '888888888888']

STEP 2: LOOP - Produs 1 (107182127516)
    
    a) scrape_product('107182127516')
        ├─ Google search cu EAN
        ├─ Gasit: https://www.mobilesentrix.eu/iphone-14-display
        ├─ Descarcă HTML
        ├─ Extrage:
        │   - name: "iPhone 14 Display"
        │   - price: 450.00 EUR
        │   - images: [img1.jpg, img2.jpg, img3.jpg]
        │   - description: "Original OEM Display..."
        │   - sku: "107182127516"
        └─ Download 3 imagini în images/
    
    b) generate_unique_sku('107182127516')
        ├─ ean_int = 107182127516
        ├─ sequential_id = 27516
        └─ sku_generated = "8902751600000"
    
    c) translate_text("iPhone 14 Display", target='ro')
        ├─ Google: "Display iPhone 14"
        ├─ Remove diacritice: "Display iPhone 14"
        └─ Result: "Display iPhone 14"
    
    d) build_longtail_title("Display iPhone 14", description)
        ├─ Piesa: "Display"
        ├─ Model: "iPhone 14"
        ├─ Quality: "Original"
        ├─ Culoare: "Negru" (din descriere)
        └─ Result: "Display iPhone 14 Original Negru"
    
    e) detect_warranty("Display iPhone 14", category)
        ├─ Cauta "display" în text → FOUND
        └─ Result: "12 luni"
    
    f) Traducere descriere + translate
        └─ "Display original OEM pentru iPhone 14"
    
    g) Upload imagini pe WordPress
        ├─ img1.jpg → WordPress → https://site.com/img1.jpg
        ├─ img2.jpg → WordPress → https://site.com/img2.jpg
        └─ img3.jpg → WordPress → https://site.com/img3.jpg
    
    h) Salvare în products_data:
        {
            'name': 'Display iPhone 14 Original Negru',
            'price': 450.00,
            'sku_generated': '8902751600000',
            'ean': '107182127516',
            'images': ['https://site.com/img1.jpg', ...],
            'description': 'Display original OEM...',
            'warranty': '12 luni',
            ...
        }

STEP 3: LOOP - Produs 2 (888888888888)
    (Același proces...)

STEP 4: export_to_csv(products_data)
    
    Crează data/export_produse_20260124_120000.csv:
    
    | ID | Type | SKU | EAN | Name | Published | ... |
    |----|------|-----|-----|------|-----------|-----|
    |    | simple | 8902751600000 | 107182127516 | Display iPhone 14 Original Negru | 1 | ... |
    |    | simple | 8908888888 | 888888888888 | Produs 2 ... | 1 | ... |

OUTPUT:
    CSV file ready pentru WooCommerce import!
```

---

## 🔧 MODIFICĂRI FRECVENTE - UNDE ȘI CUM

### **1. Schimbă format SKU**
**Fișier:** `import_gui.py`  
**Funcție:** `generate_unique_sku()`  
**Linia:** ~450

```python
# ORIGINAL:
sku = f"890{sequential_id:05d}00000"

# MODIFICARE - Format diferit:
sku = f"SKU{sequential_id:05d}"  # Prefix custom
```

---

### **2. Adaugă piese noi la Long Tail**
**Fișier:** `import_gui.py`  
**Funcție:** `build_longtail_title()`  
**Linia:** ~690

```python
piece_names = {
    'display': ['display', 'lcd', ...],
    'NEW_PIECE': ['keyword1', 'keyword2', ...],  # Adaugă aici
}
```

---

### **3. Schimbă perioadele de garanție**
**Fișier:** `import_gui.py`  
**Funcție:** `detect_warranty()`  
**Linia:** ~660

```python
# Schimbă "12 luni" în altceva:
if any(x in text for x in ['display', 'lcd']):
    return "24 luni"  # Modifică aici
```

---

### **4. Adaugă coloane noi în CSV**
**Fișier:** `import_gui.py`  
**Funcție:** `export_to_csv()`  
**Linia:** ~825

```python
fieldnames = ['ID', 'Type', 'SKU', ..., 'NEW_COLUMN']  # Adaugă aici

# Apoi în rând:
'NEW_COLUMN': value,  # Adaugă valoare
```

---

### **5. Schimbă curs EUR-RON**
**Fișier:** `.env`

```
EXCHANGE_RATE=5.00  # Schimbă aici
```

---

### **6. Modifică logica categorii (slug WebGSM)**
**Fișier:** `import_gui.py`  
**Funcție:** `get_webgsm_category()`  
**Linia:** ~2018

Returnează doar slug-uri din arborele site-ului (ex: `ecrane-iphone`, `surubelnite`). Pentru noi tipuri de produs sau cuvinte cheie, adaugă condiții în ordinea din doc (Piese → Unelte → Accesorii → Dispozitive). Nu folosi niciodată slug-urile interzise (vezi comentariul de lângă `CATEGORY_CODE_MAP`).

---

### **7. Modifica User-Agent pentru scraping**
**Fișier:** `import_gui.py`  
**Linia:** ~950 (in scrape_product)

```python
headers = {
    'User-Agent': 'NEW_USER_AGENT_HERE'  # Schimbă
}
```

---

## 📊 STRUCTURA DICT PRODUS (product_data)

```python
product_data = {
    'name': str,                    # Titlu original
    'price': float,                 # Preț EUR
    'description': str,             # Descriere
    'images': list,                 # Lista [img1.jpg, img2.jpg, ...]
    'sku': str,                     # SKU de la furnizor
    'category_path': str,           # Path categorie (ex: Piese > Piese iPhone > Ecrane)
    'category_slug': str,           # Slug WebGSM (ex: ecrane-iphone) – unde e folosit
    'tags': list,                   # Tag-uri deduse
    'supplier_sku': str,            # SKU original furnizor
    'sku_generated': str,           # SKU generat (890...)
    'ean': str,                     # EAN din input
}
```

---

## 🔐 CREDENȚIALE & CONFIGURARE

**Fișier:** `.env`

```
WOOCOMMERCE_URL=https://webgsm.ro
WOOCOMMERCE_CONSUMER_KEY=ck_abcd1234...
WOOCOMMERCE_CONSUMER_SECRET=cs_efgh5678...
EXCHANGE_RATE=4.97
```

---

## 🔐 LOGIN MPS MOBILE (reCAPTCHA + cookie-uri)

**Furnizor:** MPS Mobile (mpsmobile.de) – necesită login pentru produse.

**Strategie scurtă:**
1. **Sesiune activă** – dacă există cookie-uri din produsul anterior, validare la `/de/customer/account`; dacă pagină conține „Abmelden” → OK, fără login.
2. **Cookie-uri salvate** – din `logs/cookies_mpsmobile.json`; validare la fel; dacă valide → fără login.
3. **Login requests** – POST la formular cu Referer/Origin; dacă răspuns conține „recaptcha” → Playwright.
4. **Login Playwright** – browser vizibil. Încarcă cookie-uri salvate în context → merge la `/de/customer/account`; dacă deja logat → gata. Altfel → formular, utilizatorul rezolvă reCAPTCHA manual.
5. **Salvare** – după login reușit, cookie-uri în `logs/cookies_mpsmobile.json`.

**Fișiere:** `src/scraper/base.py` – `_login_if_required()`, `_login_with_playwright()`, `_try_saved_cookies()`, `_save_cookies()`, `_validate_session()`, `_get_saved_cookies_for_playwright()`.

**Detalii:** [REPO_OVERVIEW.md](REPO_OVERVIEW.md#6-strategie-login-mps-mobile-recaptcha--cookie-uri).

---

## 🎯 CHECKLISTA PENTRU MODIFICĂRI

- [ ] Ai citit această documentație complet?
- [ ] Înțelegi fluxul logic?
- [ ] Ai identificat locurile care trebuie modificate?
- [ ] Ai testat modificarea în funcția respectivă?
- [ ] Ai verificat dacă nu s-a stricat altceva?
- [ ] Ai rulat programul cu debugging?

---

**Creat:** 24.01.2026  
**Actualizat:** 01.02.2026 – Categorii WebGSM; Login MPS Mobile (reCAPTCHA, cookie-uri)  
**Versiune Program:** 3.2  
**Autor Documentație:** AI Assistant
