# 🏗️ ARHITECTURĂ MULTI-FURNIZOR - Plan de Extensie

## 🎯 Obiectiv

Extindere script pentru a suporta **mai mulți furnizori** (nu doar MobileSentrix), păstrând:
- ✅ Funcționalitatea existentă pentru MobileSentrix (perfect funcțională)
- ✅ Arhitectura modulară
- ✅ Procesarea comună (traducere, categorii, CSV, imagini)
- ✅ Interfața GUI cu selecție furnizor

---

## 📋 Analiză Structură Actuală

### Ce este hardcodat pentru MobileSentrix:

1. **URL-uri:**
   - `https://www.mobilesentrix.eu/` hardcodat în mai multe locuri
   - Search URL: `https://www.mobilesentrix.eu/catalogsearch/result/?q={sku}`

2. **Selectori CSS:**
   - `.page-title span`, `h1.page-title` pentru nume
   - `.price-wrapper .price` pentru preț
   - `.product.media img` pentru imagini
   - `var magicToolboxProductId` pentru ID intern

3. **Fișier SKU:**
   - `sku_list.txt` - un singur fișier pentru toate produsele

4. **Headers HTTP:**
   - Referer: `https://www.mobilesentrix.eu/`

---

## 🏗️ Arhitectură Propusă

### Structură Directoare

```
PythonProduse/
├── src/
│   ├── core/                      # Logica comună (neschimbată)
│   │   ├── config.py
│   │   ├── constants.py
│   │   └── logger.py
│   │
│   ├── scraper/                   # Scraping modular
│   │   ├── __init__.py
│   │   ├── base.py                # Clasă abstractă BaseScraper
│   │   ├── mobilesentrix.py       # Scraper MobileSentrix (mutat din import_gui.py)
│   │   ├── ifixit.py              # Scraper iFixit (exemplu)
│   │   ├── aliexpress.py          # Scraper AliExpress (exemplu)
│   │   └── factory.py             # Factory pentru creare scraper
│   │
│   ├── processors/                 # Procesare comună (neschimbată)
│   │   ├── translator.py
│   │   ├── category_detector.py
│   │   ├── title_builder.py
│   │   ├── warranty_detector.py
│   │   └── sku_generator.py
│   │
│   ├── images/                     # Imagini (neschimbată)
│   ├── export/                     # CSV export (neschimbată)
│   ├── woocommerce/                # WooCommerce (neschimbată)
│   ├── io/                         # I/O (extins)
│   │   ├── file_reader.py         # Citire sku_list per furnizor
│   │   └── supplier_config.py     # Configurare furnizori
│   │
│   └── gui/                        # GUI (extins)
│       ├── main_window.py          # Fereastra principală
│       ├── tabs/
│       │   ├── import_tab.py       # Tab cu selecție furnizor
│       │   ├── config_tab.py
│       │   └── log_tab.py
│       └── widgets/
│           └── supplier_selector.py  # Widget selecție furnizor
│
├── suppliers/                      # Configurare furnizori
│   ├── mobilesentrix/
│   │   ├── config.json            # Configurare scraper
│   │   └── sku_list.txt            # Lista SKU-uri MobileSentrix
│   ├── ifixit/
│   │   ├── config.json
│   │   └── sku_list.txt
│   └── aliexpress/
│       ├── config.json
│       └── sku_list.txt
│
├── import_gui.py                   # Entry point (modificat)
└── requirements.txt
```

---

## 🔧 Implementare

### 1. Clasă Abstractă BaseScraper

```python
# src/scraper/base.py

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import requests

class BaseScraper(ABC):
    """Clasă abstractă pentru scraper-uri furnizori"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.base_url = config['base_url']
        self.name = config['name']
        self.headers = config.get('headers', {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    @abstractmethod
    def find_product_url(self, sku_or_ean: str) -> Optional[str]:
        """Găsește URL-ul produsului pe baza SKU/EAN"""
        pass
    
    @abstractmethod
    def extract_name(self, soup: BeautifulSoup) -> str:
        """Extrage numele produsului"""
        pass
    
    @abstractmethod
    def extract_price(self, soup: BeautifulSoup) -> float:
        """Extrage prețul produsului"""
        pass
    
    @abstractmethod
    def extract_description(self, soup: BeautifulSoup) -> str:
        """Extrage descrierea produsului"""
        pass
    
    @abstractmethod
    def extract_images(self, soup: BeautifulSoup) -> List[str]:
        """Extrage URL-urile imaginilor"""
        pass
    
    @abstractmethod
    def extract_sku_ean(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extrage SKU și EAN de la furnizor"""
        pass
    
    def scrape_product(self, sku_or_url: str) -> Optional[Dict]:
        """Metodă comună care orchestrează scraping-ul"""
        # 1. Găsește URL produs
        if sku_or_url.startswith('http'):
            product_url = sku_or_url
        else:
            product_url = self.find_product_url(sku_or_url)
            if not product_url:
                return None
        
        # 2. Descarcă pagina
        response = requests.get(product_url, headers=self.headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 3. Extrage date folosind metodele abstracte
        return {
            'name': self.extract_name(soup),
            'price': self.extract_price(soup),
            'description': self.extract_description(soup),
            'images': self.extract_images(soup),
            'sku_ean': self.extract_sku_ean(soup),
            'source_url': product_url,
            'supplier': self.name,  # ← IMPORTANT: pentru meta:furnizor_activ în CSV
            'furnizor_activ': self.name  # ← Compatibilitate cu codul existent
        }
```

---

### 2. Scraper MobileSentrix (Refactorizat)

```python
# src/scraper/mobilesentrix.py

from .base import BaseScraper
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Optional

class MobileSentrixScraper(BaseScraper):
    """Scraper pentru MobileSentrix.eu"""
    
    def find_product_url(self, sku_or_ean: str) -> Optional[str]:
        """Găsește URL produs pe MobileSentrix"""
        # Logica existentă din import_gui.py
        if re.match(r'^\d{10,14}$', sku_or_ean.strip()):
            search_url = f"{self.base_url}/catalogsearch/result/?q={sku_or_ean}"
            # ... restul logicii existente
        return None
    
    def extract_name(self, soup: BeautifulSoup) -> str:
        """Extrage nume - selectori MobileSentrix"""
        name_selectors = [
            '.page-title span',
            'h1.page-title',
            'h1[itemprop="name"]',
            '.product-name',
            'h1'
        ]
        for selector in name_selectors:
            elem = soup.select_one(selector)
            if elem:
                name = elem.text.strip()
                # Curăță numele
                name = re.sub(r'\s*\bCopy\b\s*', '', name)
                name = re.sub(r'\s*\bEAN:.*', '', name)
                return name.strip()
        return "Produs necunoscut"
    
    def extract_price(self, soup: BeautifulSoup) -> float:
        """Extrage preț - selectori MobileSentrix"""
        price_selectors = [
            '.price-wrapper .price',
            '.product-info-price .price',
            'span[data-price-type="finalPrice"]',
            # ... restul selectorilor existente
        ]
        # ... logica existentă
        return 0.0
    
    def extract_description(self, soup: BeautifulSoup) -> str:
        """Extrage descriere - selectori MobileSentrix"""
        # ... logica existentă
        return ""
    
    def extract_images(self, soup: BeautifulSoup) -> List[str]:
        """Extrage imagini - selectori MobileSentrix"""
        # ... logica existentă
        return []
    
    def extract_sku_ean(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extrage SKU/EAN - logica MobileSentrix"""
        # ... logica existentă pentru magicToolboxProductId
        return {'sku': '', 'ean': ''}
```

---

### 3. Configurare Furnizori (JSON)

```json
// suppliers/mobilesentrix/config.json

{
  "name": "MobileSentrix",
  "display_name": "MobileSentrix.eu",
  "base_url": "https://www.mobilesentrix.eu",
  "search_url_template": "{base_url}/catalogsearch/result/?q={sku}",
  "headers": {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.mobilesentrix.eu/"
  },
  "selectors": {
    "name": [
      ".page-title span",
      "h1.page-title",
      "h1[itemprop=\"name\"]"
    ],
    "price": [
      ".price-wrapper .price",
      ".product-info-price .price",
      "span[data-price-type=\"finalPrice\"]"
    ],
    "description": [
      ".product.attribute.description",
      ".product-info-description"
    ],
    "images": [
      ".product.media img",
      ".fotorama__img"
    ],
    "product_id": "var magicToolboxProductId"
  },
  "sku_list_file": "suppliers/mobilesentrix/sku_list.txt",
  "enabled": true
}
```

```json
// suppliers/ifixit/config.json

{
  "name": "iFixit",
  "display_name": "iFixit Store",
  "base_url": "https://www.ifixit.com",
  "search_url_template": "{base_url}/Search?query={sku}",
  "headers": {
    "User-Agent": "Mozilla/5.0..."
  },
  "selectors": {
    "name": [
      "h1.product-title",
      ".product-name"
    ],
    "price": [
      ".price",
      ".product-price"
    ],
    "description": [
      ".product-description"
    ],
    "images": [
      ".product-images img"
    ]
  },
  "sku_list_file": "suppliers/ifixit/sku_list.txt",
  "enabled": true
}
```

---

### 4. Factory pentru Scraper-uri

```python
# src/scraper/factory.py

from pathlib import Path
import json
from typing import Optional
from .base import BaseScraper
from .mobilesentrix import MobileSentrixScraper
from .ifixit import IFixitScraper  # Când va fi implementat

class ScraperFactory:
    """Factory pentru creare scraper-uri"""
    
    _suppliers_dir = Path(__file__).parent.parent.parent / "suppliers"
    
    @classmethod
    def get_scraper(cls, supplier_name: str) -> Optional[BaseScraper]:
        """Creează scraper pentru furnizor"""
        config_path = cls._suppliers_dir / supplier_name / "config.json"
        
        if not config_path.exists():
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if not config.get('enabled', True):
            return None
        
        # Mapare nume furnizor → clasă scraper
        scraper_classes = {
            'mobilesentrix': MobileSentrixScraper,
            'ifixit': IFixitScraper,
            # Adaugă alți furnizori aici
        }
        
        scraper_class = scraper_classes.get(supplier_name)
        if not scraper_class:
            return None
        
        return scraper_class(config)
    
    @classmethod
    def list_available_suppliers(cls) -> List[Dict]:
        """Listează furnizorii disponibili"""
        suppliers = []
        
        if not cls._suppliers_dir.exists():
            return suppliers
        
        for supplier_dir in cls._suppliers_dir.iterdir():
            if not supplier_dir.is_dir():
                continue
            
            config_path = supplier_dir / "config.json"
            if not config_path.exists():
                continue
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if config.get('enabled', True):
                suppliers.append({
                    'name': config['name'],
                    'display_name': config.get('display_name', config['name']),
                    'enabled': True
                })
        
        return suppliers
```

---

### 5. GUI cu Selecție Furnizor

```python
# src/gui/tabs/import_tab.py

class ImportTab:
    def setup_import_tab(self, parent):
        """Setup tab Import cu selecție furnizor"""
        
        # Frame selecție furnizor
        frame_supplier = ttk.LabelFrame(parent, text="Selectează Furnizor", padding=10)
        frame_supplier.pack(fill='x', padx=10, pady=10)
        
        # Dropdown furnizori
        self.supplier_var = tk.StringVar()
        suppliers = ScraperFactory.list_available_suppliers()
        supplier_names = [s['display_name'] for s in suppliers]
        
        ttk.Label(frame_supplier, text="Furnizor:").grid(row=0, column=0, sticky='w', padx=5)
        supplier_combo = ttk.Combobox(frame_supplier, textvariable=self.supplier_var,
                                     values=supplier_names, state='readonly', width=30)
        supplier_combo.grid(row=0, column=1, padx=5)
        supplier_combo.current(0)  # Selectează primul
        
        # Frame SKU file (dinamic per furnizor)
        frame_sku = ttk.LabelFrame(parent, text="Selectează fișier SKU", padding=10)
        frame_sku.pack(fill='x', padx=10, pady=10)
        
        self.sku_file_var = tk.StringVar()
        
        def update_sku_file(*args):
            """Actualizează calea fișierului SKU când se schimbă furnizorul"""
            supplier_name = self.supplier_var.get()
            supplier = next((s for s in suppliers if s['display_name'] == supplier_name), None)
            if supplier:
                config_path = Path("suppliers") / supplier['name'] / "config.json"
                with open(config_path, 'r') as f:
                    config = json.load(f)
                sku_file = config.get('sku_list_file', f"suppliers/{supplier['name']}/sku_list.txt")
                self.sku_file_var.set(sku_file)
        
        self.supplier_var.trace_add('write', update_sku_file)
        update_sku_file()  # Inițializare
        
        ttk.Label(frame_sku, text="Fișier:").grid(row=0, column=0, sticky='w', padx=5)
        ttk.Entry(frame_sku, textvariable=self.sku_file_var, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(frame_sku, text="Răsfoire...", command=self.browse_sku_file).grid(row=0, column=2, padx=5)
        
        # Restul interfeței (opțiuni, progress, butoane) rămâne la fel
```

---

### 6. Modificare run_import() pentru Multi-Furnizor

```python
# src/gui/main_window.py

def run_import(self):
    """Execută exportul cu furnizor selectat"""
    
    # 1. Obține furnizorul selectat
    supplier_display_name = self.supplier_var.get()
    suppliers = ScraperFactory.list_available_suppliers()
    supplier = next((s for s in suppliers if s['display_name'] == supplier_display_name), None)
    
    if not supplier:
        messagebox.showerror("Eroare", "Furnizor invalid!")
        return
    
    # 2. Creează scraper pentru furnizor
    scraper = ScraperFactory.get_scraper(supplier['name'])
    if not scraper:
        messagebox.showerror("Eroare", f"Nu s-a putut inițializa scraper pentru {supplier['display_name']}")
        return
    
    # 3. Citește SKU-uri din fișierul furnizorului
    sku_file = self.sku_file_var.get()
    sku_items = self.read_sku_file(sku_file)
    
    # 4. Loop produse (folosește scraper-ul selectat)
    products_data = []
    for idx, item in enumerate(sku_items, 1):
        url_or_sku = item['url']
        manual_code = item.get('code')
        
        # Folosește scraper-ul pentru a extrage date
        product_data = scraper.scrape_product(url_or_sku)
        
        if product_data:
            # Procesare comună (traducere, categorii, etc.) - NESCHIMBATĂ
            product_data['manual_category_code'] = manual_code
            # ... restul procesării existente
            
            products_data.append(product_data)
    
    # 5. Export CSV (neschimbat)
    csv_filename = f"export_{supplier['name']}_{timestamp}.csv"
    csv_path = self.export_to_csv(products_data, csv_filename)
```

---

## 📁 Structură Fișiere SKU per Furnizor

```
suppliers/
├── mobilesentrix/
│   ├── config.json
│   └── sku_list.txt          # SKU-uri specifice MobileSentrix
│
├── ifixit/
│   ├── config.json
│   └── sku_list.txt          # SKU-uri specifice iFixit
│
└── aliexpress/
    ├── config.json
    └── sku_list.txt          # SKU-uri specifice AliExpress
```

**Format sku_list.txt rămâne același:**
```
https://www.mobilesentrix.eu/product-name/ | BAT
107182127516
888888888888
```

---

## 🔄 Flux Complet Multi-Furnizor

```
┌─────────────────────────────────────────────────────────────┐
│                    GUI - Selecție Furnizor                 │
│                    [MobileSentrix ▼] [iFixit] [AliExpress] │
└───────────────────────────┬───────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              ScraperFactory.get_scraper()                   │
│              → Creează scraper pentru furnizor selectat      │
└───────────────────────────┬───────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Citește sku_list.txt per furnizor              │
│              suppliers/{furnizor}/sku_list.txt              │
└───────────────────────────┬───────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Scraper specific furnizor                       │
│              → scrape_product() cu selectori specifici        │
└───────────────────────────┬───────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Procesare COMUNĂ (neschimbată)                  │
│              → Traducere, Categorii, Titluri, CSV           │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Beneficii

1. **Extensibilitate**: Adăugare furnizor nou = creare clasă scraper + config.json
2. **Menținere**: Codul MobileSentrix rămâne intact, doar mutat în modul separat
3. **Reutilizare**: Procesarea comună (traducere, categorii, CSV) rămâne neschimbată
4. **Organizare**: Fiecare furnizor are propriul folder cu config și SKU-uri
5. **GUI clar**: Utilizatorul selectează furnizorul, vede doar SKU-urile relevante

---

## 📝 Plan Implementare

### Faza 1: Refactorizare MobileSentrix (Fără modificări funcționale)
1. ✅ Creează `src/scraper/base.py` (clasă abstractă)
2. ✅ Mută logica MobileSentrix în `src/scraper/mobilesentrix.py`
3. ✅ Creează `suppliers/mobilesentrix/config.json`
4. ✅ Mută `sku_list.txt` → `suppliers/mobilesentrix/sku_list.txt`
5. ✅ **IMPORTANT**: Modifică `scrape_product()` să returneze `supplier` și `furnizor_activ` în `product_data`
6. ✅ **IMPORTANT**: Modifică `export_to_csv()` linia 3674: `product.get('furnizor_activ', 'mobilesentrix')` (deja corect, dar verifică)
7. ✅ Testează că funcționează identic și CSV-ul are `meta:furnizor_activ` corect

### Faza 2: Factory și GUI
1. ✅ Creează `src/scraper/factory.py`
2. ✅ Modifică GUI să aibă dropdown furnizor
3. ✅ Modifică `run_import()` să folosească factory
4. ✅ Testează cu MobileSentrix

### Faza 3: Adăugare Furnizor Nou (mobileparts.shop, mpsmobile.de, mmsmobile.de, componentidigitali.com)
1. ✅ Analizează site-urile pentru selectori CSS
2. ✅ Creează `src/scraper/mobileparts.py`, `mpsmobile.py`, `mmsmobile.py`, `componentidigitali.py`
3. ✅ Creează `suppliers/{furnizor}/config.json` pentru fiecare
4. ✅ Creează `suppliers/{furnizor}/sku_list.txt` pentru fiecare
5. ✅ Testează cu fiecare furnizor

---

## 🎯 Exemplu: Adăugare Furnizor Nou

### Pas 1: Creează Configurare

```json
// suppliers/noul_furnizor/config.json
{
  "name": "noul_furnizor",
  "display_name": "Noul Furnizor",
  "base_url": "https://www.noul-furnizor.com",
  "search_url_template": "{base_url}/search?q={sku}",
  "selectors": {
    "name": ["h1.product-title"],
    "price": [".price"],
    "description": [".description"],
    "images": [".product-images img"]
  },
  "sku_list_file": "suppliers/noul_furnizor/sku_list.txt",
  "enabled": true
}
```

### Pas 2: Implementează Scraper

```python
# src/scraper/noul_furnizor.py

from .base import BaseScraper
from bs4 import BeautifulSoup

class NoulFurnizorScraper(BaseScraper):
    def find_product_url(self, sku_or_ean: str):
        # Logica specifică noul_furnizor
        pass
    
    def extract_name(self, soup):
        # Folosește selectori din config.json
        for selector in self.config['selectors']['name']:
            elem = soup.select_one(selector)
            if elem:
                return elem.text.strip()
        return "Produs necunoscut"
    
    # ... restul metodelor
```

### Pas 3: Adaugă în Factory

```python
# src/scraper/factory.py

scraper_classes = {
    'mobilesentrix': MobileSentrixScraper,
    'noul_furnizor': NoulFurnizorScraper,  # ← Adaugă aici
}
```

### Pas 4: Gata!

Furnizorul apare automat în dropdown-ul GUI și poate fi folosit imediat.

---

---

## ⚠️ Observații din CSV Export

### Modificări Necesare în Codul Existent

**1. `scrape_product()` (linia ~4570):**
```python
# ÎNAINTE:
'furnizor_activ': 'mobilesentrix',  # Hardcodat

# DUPĂ:
'furnizor_activ': self.supplier_name,  # Din scraper
'supplier': self.supplier_name,  # Pentru compatibilitate
```

**2. `export_to_csv()` (linia ~3674):**
```python
# ÎNAINTE:
'meta:furnizor_activ': product.get('furnizor_activ', 'mobilesentrix'),  # Default hardcodat

# DUPĂ (deja corect, dar verifică):
'meta:furnizor_activ': product.get('furnizor_activ', product.get('supplier', 'mobilesentrix')),
```

**3. EAN cu apostrof:**
- CSV-ul exportat are apostrof: `'107082130502`
- Codul procesează EAN fără apostrof (linia ~3542)
- Apostroful probabil se adaugă pentru Excel (să nu convertească în științific)
- **Concluzie**: Păstrăm logica actuală, apostroful e probabil necesar

---

**Data creare**: 19.02.2026  
**Status**: Planificare (actualizat după analiza CSV)  
**Versiune**: 1.1
