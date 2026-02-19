# 📊 Analiză Site-uri Furnizori - Selectori CSS și Provocări

**Data analiză**: 19.02.2026  
**Furnizori analizați**: mobileparts.shop, mpsmobile.de, mmsmobile.de, componentidigitali.com, **foneday.shop**

---

## 🖼️ Politică imagini (watermark)

**Regulă**: La fiecare furnizor se verifică dacă imaginile produselor au **watermark**.  
- **Dacă imaginile au watermark** → nu preluăm imagini; preluăm doar restul datelor (nume, preț, descriere, SKU/EAN, etc.) fără poze.  
- **Dacă imaginile nu au watermark** → preluăm și imaginile, ca la MobileSentrix.

În config fiecare furnizor are câmpul **`skip_images`**:
- `"skip_images": true` → nu descărcăm/upload imagini (folosim doar date text)
- `"skip_images": false` → preluăm și imaginile

---

## 📋 Rezumat Executiv

| Furnizor | Login preț | Limba | Watermark / Preluare imagini | Provocări |
|----------|------------|-------|-----------------------------|-----------|
| **mobilesentrix.eu** | ❌ NU | EN | ❓ Verificat: fără watermark → preluăm poze | Referință actuală |
| **foneday.shop** | ❓ | EN | ❓ De verificat | SPA/API, catalog pe SKU |
| **mobileparts.shop** | ❓ | EN | ❓ De verificat | Structură HTML necunoscută |
| **mpsmobile.de** | ✅ DA | DE/ES | ❓ De verificat | Login prețuri, B2B |
| **mmsmobile.de** | ✅ DA | EN/DE | ❓ De verificat | Login prețuri, Odoo |
| **componentidigitali.com** | ❌ NU | IT/EN | ❓ De verificat | SKU în text |

---

## 1. 🛒 mobileparts.shop

### Status Analiză
⚠️ **Necesită analiză manuală** - Restricții de rețea au împiedicat accesul direct.

### Ce trebuie verificat manual:

1. **Deschide DevTools (F12)** pe o pagină de produs
2. **Identifică selectori CSS** pentru:
   - Nume produs: `h1.product-title`, `.product-name`, etc.
   - Preț: `.price`, `.product-price`, etc.
   - Descriere: `.product-description`, etc.
   - Imagini: `.product-images img`, etc.
   - SKU/EAN: `.sku`, `.product-sku`, `[itemprop="sku"]`, etc.

3. **Verifică login wall**:
   - Prețul este vizibil fără login?
   - Există mesaje "Login to see price"?

4. **Format URL produse**:
   - Exemplu: `https://mobileparts.shop/product/iphone-14-display`
   - Sau alt format?

5. **Pagină căutare**:
   - URL: `/search?q=...` sau `/catalogsearch/result/?q=...`
   - Selector link produse: `.product-item-link`, etc.

6. **Watermark pe imagini**: ❓ De verificat pe o pagină de produs. Dacă imaginile au watermark → `skip_images: true`.

### Script Python pentru analiză automată:

```python
import requests
from bs4 import BeautifulSoup

def analyze_mobileparts():
    base_url = "https://mobileparts.shop"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': base_url
    }
    
    # Test căutare
    search_url = f"{base_url}/search?q=iPhone+14+display"
    response = requests.get(search_url, headers=headers, timeout=30)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Găsește link-uri produse
        product_links = soup.select('a[href*="/product/"], a.product-link')
        
        if product_links:
            product_url = product_links[0].get('href')
            if not product_url.startswith('http'):
                product_url = base_url + product_url
            
            # Analizează produs
            product_response = requests.get(product_url, headers=headers, timeout=30)
            if product_response.status_code == 200:
                product_soup = BeautifulSoup(product_response.content, 'html.parser')
                
                # Salvează HTML pentru analiză manuală
                with open('mobileparts_product.html', 'w', encoding='utf-8') as f:
                    f.write(product_soup.prettify())
                print(f"HTML salvat: mobileparts_product.html")
                print(f"URL produs: {product_url}")

if __name__ == '__main__':
    analyze_mobileparts()
```

---

## 2. 🇩🇪 mpsmobile.de

### Structură HTML

- **Titlu produs**: `<h1>` în header
- **Informații**: Tabel cu SKU, GTIN, preț, disponibilitate
- **Imagini**: Galerie produs
- **Descriere**: Secțiune cu tab "BESCHREIBUNG" / "DESCRIPCIÓN"

### Selectori CSS Identificați

```python
SELECTORS_MPSMOBILE = {
    'name': [
        'h1',  # Titlul principal
        '.product-title',
        'h1.product-name',
        '#product-title'
    ],
    'price': [
        # ⚠️ NECESITĂ LOGIN - apare text "Preis anzeigen"
        'td:contains("Preis") + td',  # XPath-like, nu CSS standard
        '.price',
        '.product-price',
        # Trebuie verificat în HTML după login
    ],
    'description': [
        '.product-description',
        '#description',
        '.tab-content',  # În tab-ul "BESCHREIBUNG"
    ],
    'images': [
        '.product-image img',
        '.product-gallery img',
        'img.product-image',
        '.product-main-image'
    ],
    'sku': [
        # În tabel: "Art-Nr." / "Artículo Nro."
        'td:contains("Art-Nr.") + td',  # XPath-like
        '.product-sku',
        # Trebuie extras din tabel după text "Art-Nr."
    ],
    'ean': [
        # În tabel: "GTIN:"
        'td:contains("GTIN:") + td',  # XPath-like
        '.product-ean',
        # Trebuie extras din tabel după text "GTIN:"
    ],
    'availability': [
        'td:contains("Verfügbar")',  # XPath-like
        '.availability',
    ],
    'brand': [
        'td:contains("Hersteller") + td',  # XPath-like
        '.manufacturer',
    ]
}
```

### Format URL Produse

```
https://mpsmobile.de/{lang}/{product-name-slug}-p-{PRODUCT_ID}
```

**Exemple:**
- `https://mpsmobile.de/de/zy-hard-oled-display-unit-fur-iphone-13-pro-max-mit-ic-ersatz-p-1328D11AF6AF`
- `https://mpsmobile.de/es/display-oled-zy-hard-para-iphone-13-pro-max-con-reemplazo-de-ic-p-1328D11AF6AF`

**Pattern:**
- `{lang}`: `de`, `es`, etc.
- `{product-name-slug}`: nume produs slug-uit
- `-p-`: separator fix
- `{PRODUCT_ID}`: ID hexazecimal

### Pagină Căutare

```
https://mpsmobile.de/{lang}/all-categories-c-0/search/{QUERY}
```

**Exemplu:**
```
https://mpsmobile.de/de/all-categories-c-0/search/iPhone%2014%20display
```

### Login Wall

✅ **DA** - Prețurile necesită login:
- Mesaj: "Bitte melden Sie sich an, um Preise zu sehen" (DE)
- Mesaj: "Por favor acceso para ver los precios" (ES)
- Link login: `/de/customer/login` sau `/es/customer/login`

**Implicații:**
- Prețurile nu pot fi extrase fără autentificare
- Necesită sesiune autentificată sau cookies de login
- Disponibilitatea stocului necesită și ea login

### Headers HTTP

```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'de-DE,de;q=0.9',  # sau 'es-ES,es;q=0.9'
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://mpsmobile.de/',
    'Cookie': 'session_id=...'  # Necesar pentru prețuri
}
```

### Observații

1. **Multi-limbă**: Site-ul suportă multiple limbi (`de`, `es`)
2. **B2B**: Site-ul vinde exclusiv către companii
3. **Prețuri dinamice**: Prețurile sunt probabil personalizate per client
4. **Structură consistentă**: Format URL și HTML consistente

### Watermark pe imagini

❓ **De verificat** pe o pagină de produs. Dacă imaginile au watermark → în config: `"skip_images": true`. Altfel `"skip_images": false`.

### Recomandări Implementare

1. **Pentru prețuri**: Necesită autentificare (session/cookies)
2. **Pentru SKU/EAN**: Disponibile fără login (extrase din tabele)
3. **Pentru imagini**: Disponibile fără login (sau skip dacă watermark)
4. **Pentru descriere**: Disponibilă fără login

---

## 3. 🇩🇪 mmsmobile.de

### Structură HTML

- **Header**: Navigare (Home, Search, Wishlist, Account)
- **Titlu produs**: `<h1>`
- **Imagine principală**: Galerie imagini
- **Informații**: Tabele cu Brand, EAN, SKU
- **Secțiuni**: Specifications, Description
- **Butoane**: Add to Cart, Compare, Wishlist, Share

### Selectori CSS Identificați

```python
SELECTORS_MMSMOBILE = {
    'name': [
        'h1',  # Titlul principal
        # Exemple: "BATTERY FOR IPHONE 14 (WITHOUT FLEX CABLE)"
    ],
    'price': [
        # ⚠️ NECESITĂ LOGIN - apare text "Login | Register to see price"
        'h4',  # Sau selector pentru preț (necesită login)
        '.price',
        '[class*="price"]',
        # Trebuie verificat în HTML după login
    ],
    'description': [
        'section[aria-labelledby*="description"]',
        '.tab-content',
        '#description',
        '.product-description'
    ],
    'images': [
        'img[src*="/web/image/product.template/"]',
        # Pattern URL: https://www.mmsmobile.de/web/image/product.template/{PRODUCT_ID}/image_1920?unique={UNIQUE_ID}
    ],
    'sku': [
        # În tabel cu header "SKU"
        'table td',  # Extrage din tabel după header "SKU"
        # Structură: | EAN | SKU | → | 8699261153215 | BATF11 |
    ],
    'ean': [
        # În tabel cu header "EAN"
        'table td',  # Extrage din tabel după header "EAN"
    ],
    'brand': [
        # În tabel cu header "Brand"
        'table td',  # Extrage din tabel după header "Brand"
    ],
    'availability': [
        'h3',  # "Not Available For Sale" sau similar
        '.availability',
    ]
}
```

### Format URL Produse

```
https://www.mmsmobile.de/shop/{PRODUCT_SLUG}-{PRODUCT_ID}
```

**Exemple:**
- `https://www.mmsmobile.de/shop/batf11-akku-fur-iph-14-without-flex-kabel-1729`
- `https://www.mmsmobile.de/shop/dd06-dd-soft-oled-fur-iphone-14-12408`
- `https://www.mmsmobile.de/shop/sd128-128-gb-micro-sd-karte-1697`

**Pattern:**
- Base: `https://www.mmsmobile.de/shop/`
- Slug: nume produs slug-uit (lowercase, cu cratime)
- ID: număr la final (ex: 1729, 12408, 1697)

### Pagină Căutare

```
https://www.mmsmobile.de/{lang}/shop?search={QUERY}
```

**Exemplu:**
```
https://www.mmsmobile.de/en/shop?search=iPhone+14+display
```

**Parametri suplimentari:**
- `order={SORT_TYPE}`: Sortare (Featured, Newest, Price, etc.)
- `attribute_value={VALUE}`: Filtrare (ex: `16-41` pentru LCD)
- `view_mode=grid`: Mod vizualizare

### Login Wall

✅ **DA** - Prețurile necesită login:
- Mesaj: "Login | Register to see price"
- Link login: `https://www.mmsmobile.de/web/login`
- Link register: `https://www.mmsmobile.de/web/signup`

**Implicații:**
- Prețurile nu pot fi extrase fără autentificare
- Necesită sesiune autentificată sau cookies de login
- Prețurile din rezultatele de căutare necesită și ele login

### Headers HTTP

```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Cache-Control': 'max-age=0',
    'Referer': 'https://www.mmsmobile.de/',
    'Cookie': 'session_id=...'  # Necesar pentru prețuri
}
```

### Watermark pe imagini

❓ **De verificat** pe o pagină de produs. Dacă imaginile au watermark → `"skip_images": true`.

### Observații

1. **Odoo-based**: Site-ul pare să folosească Odoo (pattern URL `/web/image/product.template/`)
2. **Multi-limbă**: Suportă EN și DE
3. **Prețuri dinamice**: Prețurile necesită autentificare
4. **ID în URL**: ID-ul produsului apare în URL (poate fi folosit pentru identificare)

### Recomandări Implementare

1. **Pentru prețuri**: Necesită autentificare (session/cookies)
2. **Pentru SKU/EAN**: Disponibile fără login (extrase din tabele)
3. **Pentru imagini**: Disponibile fără login (sau skip dacă watermark)
4. **Pentru descriere**: Disponibilă fără login

---

## 4. 🇮🇹 componentidigitali.com

### Structură HTML

- **Listing produse**: Produsele apar în liste de categorii
- **Breadcrumb**: categorie > subcategorie > produs
- **Container produs**: Titlu, Cod articol (SKU), Brand, Calitate, Disponibilitate, Preț, Buton "Add to cart"

### Selectori CSS Identificați

```python
SELECTORS_COMPONENTI = {
    'name': [
        'h2', 'h3',  # Titluri produse în listing
        '.product-title',
        'h1.page-title',  # Pentru pagini de detalii
        'h1[itemprop="name"]'
    ],
    'price': [
        # ✅ PREȚURI VIZIBILE FĂRĂ LOGIN
        '.price',
        '.price-wrapper .price',
        'span.price',
        'div.price',
        # Format: "€X,XX IVA inclusa" (IT) sau "€X,XX With VAT" (EN)
    ],
    'description': [
        '.product-description',
        '.product-info-description',
        '.description',
        '[itemprop="description"]'
    ],
    'images': [
        '.product-image img',
        '.product-media img',
        'img[alt*="product"]',
        '.product-gallery img',
        'img.product-image'
    ],
    'sku': [
        # ⚠️ SKU apare ca TEXT, nu atribut HTML
        # Pattern: "Item no.: XXXXX" (EN) sau "Cod. Art.: XXXXX" (IT)
        # Trebuie extras cu regex din text
        # Regex: r'Item no\.:\s*(\d+)' sau r'Cod\. Art\.:\s*(\d+)'
    ],
    'availability': [
        # Text: "Disponibile (X PZ)" (IT) sau "Available (X PZ)" (EN)
        # Sau "Non disponibile" / "Not available"
    ],
    'brand': [
        # Link către brand: "Marca: [BrandName]" (IT) sau "Brand: [BrandName]" (EN)
    ]
}
```

### Format URL Produse

**Categorii:**
```
/it/componenti-digitali-home-page/[categoria]/products.1.39.XXX.sp.uw
/en/componenti-digitali-home-page/[category]/products.2.39.XXX.sp.uw
```

**Produse:**
```
/en/.../iphone-14/display-lcd-for-iphone-14-black-incell-jk-thl-cof-.2.39.582.gp.34432.uw
/it/.../iphone-14/display-lcd-for-iphone-14-black-incell-jk-thl-cof-.2.39.582.gp.34432.uw
```

**Pattern:**
- `/it/` sau `/en/` pentru limbă
- Path categorie (slug)
- Slug produs
- `.2.39.582.gp.XXXXX.uw` (cod produs)

### Pagină Căutare

**Căutare simplă**: Câmp "Cerca" / "Search" în header

**Căutare avansată**: Formular cu filtre:
- Marca/Brand
- Tip articol
- Calitate

⚠️ **Observație**: Căutarea directă (`?cmd=search&q=...`) cere cel puțin un criteriu de filtrare.

### Login Wall

❌ **NU** - Prețurile sunt vizibile fără autentificare:
- Format: "€3,30 IVA inclusa" (IT) sau "€3,30 With VAT" (EN)
- Prețurile apar în paginile de listing și detalii

### Headers HTTP

```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.componentidigitali.com/',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}
```

### Watermark pe imagini

❓ **De verificat** pe o pagină de produs. Dacă imaginile au watermark → `"skip_images": true`.

### Observații

1. **Multi-limbă**: Site-ul suportă IT și EN
2. **Prețuri vizibile**: ✅ Prețurile sunt accesibile fără login
3. **SKU în text**: SKU-ul apare ca text ("Item no.:" sau "Cod. Art.:"), nu într-un atribut HTML dedicat
4. **Disponibilitate explicită**: Disponibilitatea este afișată explicit în listing
5. **Structură URL complexă**: URL-urile includ coduri numerice (ex: `.gp.34432.uw`)

### Recomandări Implementare

1. **Pentru prețuri**: ✅ Disponibile fără login (extrage cu regex: `€(\d+,\d+)`)
2. **Pentru SKU**: Extrage cu regex din text: `r'Item no\.:\s*(\d+)'` sau `r'Cod\. Art\.:\s*(\d+)'`
3. **Pentru imagini**: Disponibile fără login (sau skip dacă watermark)
4. **Pentru descriere**: Disponibilă fără login

---

## 5. 📱 foneday.shop

**Furnizor nou** – wholesale piese mobile (ecrane, baterii, camere, flexuri, unelte). Peste 15.000 produse, 25+ branduri (Apple, Samsung, Huawei, etc.). Mărci proprii FDX (FDX Lite, Prime, Ultra, Pro, Elite).

### Status Analiză

Site-ul este **SPA (Single Page Application)** – conținut încărcat dinamic (Vue/Alpine.js). Catalogul folosește **API** pentru prețuri și stoc:
- `POST https://foneday.shop/webshop/quick-search/fetch-article-price-info` cu `{ skus: [...] }`
- `POST https://foneday.shop/webshop/quick-search/fetch-article-stock-info` cu `{ skus: [...] }`

### Structură site

- **Base URL**: `https://foneday.shop`
- **Catalog**: `https://foneday.shop/catalog`
- **Assortiment**: `https://foneday.shop/assortment/parts`, `https://foneday.shop/assortment/brands`
- **FDX (ecrane)**: `https://foneday.shop/fdx`
- **Căutare**: quick search pe SKU (articole încărcate din API)

### Ce trebuie verificat

1. **URL pagină produs**: format exact (ex: `/article/{sku}`, `/product/...`, `/p/...`) – necesită navigare pe site sau inspecție API.
2. **Selectori HTML**: dacă există pagini produs server-rendered; altfel datele vin din API (JSON).
3. **Login pentru preț**: dacă prețurile sunt în răspunsul API fără auth sau necesită cookie/sesiune.
4. **Watermark pe imagini**: de verificat pe o pagină de produs – dacă există, setăm `skip_images: true`.

### Imagini (watermark)

❓ **De verificat**: Deschide o pagină de produs pe foneday.shop și verifică dacă imaginile au logo/watermark. Dacă da → în config: `"skip_images": true`.

### Template config (preliminar)

```json
{
  "name": "foneday",
  "display_name": "Foneday.shop",
  "base_url": "https://foneday.shop",
  "search_url_template": "{base_url}/catalog",
  "api": {
    "price_info": "https://foneday.shop/webshop/quick-search/fetch-article-price-info",
    "stock_info": "https://foneday.shop/webshop/quick-search/fetch-article-stock-info"
  },
  "headers": {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://foneday.shop/"
  },
  "selectors": {},
  "skip_images": null,
  "login": { "required": false },
  "sku_list_file": "suppliers/foneday/sku_list.txt",
  "enabled": true
}
```

**Notă**: Selectori vor fi completați după analiză pagină produs sau documentație API. Posibil scraperul să folosească doar API-ul pentru preț/stock și o altă sursă pentru nume/descriere/imagini.

---

## 🎯 Provocări Comune și Soluții

### 1. Login Wall pentru Prețuri

**Furnizori afectați:**
- ✅ mpsmobile.de
- ✅ mmsmobile.de
- ❓ mobileparts.shop (necesită verificare)
- ❌ componentidigitali.com (prețuri vizibile)

**Soluții posibile:**

#### Opțiunea A: Scraping fără preț
```python
# În product_data:
'price': None,  # Sau 0.0
'price_requires_login': True,
'meta:pret_achizitie': None,  # Sau 0.00
```

#### Opțiunea B: Autentificare programatică
```python
# În config.json:
{
    "login": {
        "required": true,
        "url": "https://mpsmobile.de/de/customer/login",
        "username": "USERNAME_FROM_ENV",
        "password": "PASSWORD_FROM_ENV"
    }
}

# În scraper:
def login(self):
    session = requests.Session()
    login_data = {
        'login[username]': self.config['login']['username'],
        'login[password]': self.config['login']['password']
    }
    response = session.post(self.config['login']['url'], data=login_data)
    return session  # Folosește session pentru request-uri ulterioare
```

#### Opțiunea C: Cookie-uri manuale
```python
# În config.json:
{
    "cookies": {
        "session_id": "COOKIE_FROM_ENV",
        "auth_token": "TOKEN_FROM_ENV"
    }
}

# În scraper:
headers = {
    'Cookie': f"session_id={self.config['cookies']['session_id']}"
}
```

### 2. SKU/EAN în Text (nu Atribut HTML)

**Furnizori afectați:**
- ✅ componentidigitali.com (SKU în text: "Item no.: 46013")

**Soluție:**
```python
import re

def extract_sku_from_text(self, soup):
    """Extrage SKU din textul paginii"""
    page_text = soup.get_text()
    
    # Pattern pentru EN: "Item no.: 46013"
    match_en = re.search(r'Item no\.:\s*(\d+)', page_text)
    if match_en:
        return match_en.group(1)
    
    # Pattern pentru IT: "Cod. Art.: 46013"
    match_it = re.search(r'Cod\. Art\.:\s*(\d+)', page_text)
    if match_it:
        return match_it.group(1)
    
    return None
```

### 3. Multi-limbă

**Furnizori afectați:**
- ✅ mpsmobile.de (DE/ES)
- ✅ mmsmobile.de (EN/DE)
- ✅ componentidigitali.com (IT/EN)

**Soluție:**
```python
# În config.json:
{
    "default_language": "en",  # sau "de", "it", "es"
    "supported_languages": ["en", "de"]
}

# În scraper:
def get_product_url(self, sku):
    lang = self.config.get('default_language', 'en')
    return f"https://site.com/{lang}/product/{sku}"
```

### 4. Selectori CSS Complexi (Tabele)

**Furnizori afectați:**
- ✅ mpsmobile.de (SKU/EAN în tabele)
- ✅ mmsmobile.de (SKU/EAN în tabele)

**Soluție:**
```python
def extract_from_table(self, soup, header_text):
    """Extrage valoare din tabel după header"""
    # Găsește toate td-urile
    tds = soup.select('table td')
    
    for i, td in enumerate(tds):
        if header_text.lower() in td.get_text().lower():
            # Următorul td conține valoarea
            if i + 1 < len(tds):
                return tds[i + 1].get_text().strip()
    
    return None

# Utilizare:
sku = self.extract_from_table(soup, "Art-Nr.")
ean = self.extract_from_table(soup, "GTIN:")
```

---

## 📝 Plan Implementare pe Furnizor

### Prioritate 1: componentidigitali.com
- ✅ Prețuri vizibile fără login
- ✅ Structură simplă
- ⚠️ SKU în text (necesită regex)

### Prioritate 2: mobileparts.shop
- ❓ Necesită analiză manuală completă
- ⚠️ Structură HTML necunoscută

### Prioritate 3: mmsmobile.de
- ⚠️ Login wall pentru prețuri
- ✅ Structură clară (Odoo-based)
- ✅ SKU/EAN în tabele

### Prioritate 4: mpsmobile.de
- ⚠️ Login wall pentru prețuri
- ⚠️ Multi-limbă (DE/ES)
- ⚠️ SKU/EAN în tabele

---

## 🔧 Template Config.json per Furnizor

**Regulă imagini**: Dacă furnizorul are watermark pe poze → `"skip_images": true` (nu preluăm imagini). Altfel `"skip_images": false`.

### mobilesentrix.eu (referință)

```json
{
  "name": "mobilesentrix",
  "display_name": "MobileSentrix.eu",
  "base_url": "https://www.mobilesentrix.eu",
  "search_url_template": "{base_url}/catalogsearch/result/?q={sku}",
  "headers": {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.mobilesentrix.eu/"
  },
  "selectors": {
    "name": [".page-title span", "h1.page-title"],
    "price": [".price-wrapper .price", ".product-info-price .price"],
    "description": [".product.attribute.description"],
    "images": [".product.media img", ".fotorama__img"],
    "product_id": "var magicToolboxProductId"
  },
  "skip_images": false,
  "login": { "required": false },
  "sku_list_file": "suppliers/mobilesentrix/sku_list.txt",
  "enabled": true
}
```

### componentidigitali.com

```json
{
  "name": "componentidigitali",
  "display_name": "Componenti Digitali",
  "base_url": "https://www.componentidigitali.com",
  "default_language": "it",
  "supported_languages": ["it", "en"],
  "search_url_template": "{base_url}/{lang}/shop?search={sku}",
  "headers": {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8"
  },
  "selectors": {
    "name": ["h2", "h3", ".product-title", "h1.page-title"],
    "price": [".price", ".price-wrapper .price"],
    "description": [".product-description", ".description"],
    "images": [".product-image img", ".product-media img"],
    "sku_regex": "Item no\\.:\\s*(\\d+)|Cod\\. Art\\.:\\s*(\\d+)",
    "availability": [".availability"]
  },
  "skip_images": false,
  "login": { "required": false },
  "sku_list_file": "suppliers/componentidigitali/sku_list.txt",
  "enabled": true
}
```

### mmsmobile.de

```json
{
  "name": "mmsmobile",
  "display_name": "MMS Mobile",
  "base_url": "https://www.mmsmobile.de",
  "default_language": "en",
  "supported_languages": ["en", "de"],
  "search_url_template": "{base_url}/{lang}/shop?search={sku}",
  "headers": {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9,de;q=0.8"
  },
  "selectors": {
    "name": ["h1"],
    "price": ["h4", ".price"],
    "description": ["section[aria-labelledby*=\"description\"]", ".tab-content"],
    "images": ["img[src*=\"/web/image/product.template/\"]"],
    "sku_table_header": "SKU",
    "ean_table_header": "EAN",
    "brand_table_header": "Brand"
  },
  "skip_images": false,
  "login": {
    "required": true,
    "url": "{base_url}/web/login",
    "username": "USERNAME_FROM_ENV",
    "password": "PASSWORD_FROM_ENV"
  },
  "sku_list_file": "suppliers/mmsmobile/sku_list.txt",
  "enabled": true
}
```

### mpsmobile.de

```json
{
  "name": "mpsmobile",
  "display_name": "MPS Mobile",
  "base_url": "https://mpsmobile.de",
  "default_language": "de",
  "supported_languages": ["de", "es"],
  "search_url_template": "{base_url}/{lang}/all-categories-c-0/search/{sku}",
  "headers": {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "de-DE,de;q=0.9"
  },
  "selectors": {
    "name": ["h1", ".product-title"],
    "price": [".price", ".product-price"],
    "description": [".product-description", ".tab-content"],
    "images": [".product-image img", ".product-gallery img"],
    "sku_table_header": "Art-Nr.",
    "ean_table_header": "GTIN:",
    "brand_table_header": "Hersteller"
  },
  "skip_images": false,
  "login": {
    "required": true,
    "url": "{base_url}/{lang}/customer/login",
    "username": "USERNAME_FROM_ENV",
    "password": "PASSWORD_FROM_ENV"
  },
  "sku_list_file": "suppliers/mpsmobile/sku_list.txt",
  "enabled": true
}
```

### foneday.shop

```json
{
  "name": "foneday",
  "display_name": "Foneday.shop",
  "base_url": "https://foneday.shop",
  "search_url_template": "{base_url}/catalog",
  "api": {
    "price_info": "https://foneday.shop/webshop/quick-search/fetch-article-price-info",
    "stock_info": "https://foneday.shop/webshop/quick-search/fetch-article-stock-info"
  },
  "headers": {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://foneday.shop/"
  },
  "selectors": {},
  "skip_images": false,
  "login": { "required": false },
  "sku_list_file": "suppliers/foneday/sku_list.txt",
  "enabled": true
}
```

---

**Template-uri config**: Fișierele `config.json` per furnizor sunt în **`suppliers/<furnizor>/config.json`** (mobilesentrix, foneday, mobileparts, mmsmobile, mpsmobile, componentidigitali). Vezi și **`suppliers/README.md`** pentru regula de watermark și `skip_images`.

**Data creare**: 19.02.2026  
**Status**: Analiză completă; Foneday.shop adăugat; politică watermark + template-uri create  
**Următorul pas**: Verificare watermark pe fiecare site și setare `skip_images` în config; implementare scraper multi-furnizor
