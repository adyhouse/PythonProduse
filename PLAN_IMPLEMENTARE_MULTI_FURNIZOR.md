# 🚀 PLAN IMPLEMENTARE MULTI-FURNIZOR

## 📋 Furnizori de Adăugat

1. ✅ **MobileSentrix** (mobilesentrix.eu) - **FUNCȚIONEAZĂ PERFECT** - NU MODIFICĂM
2. 🆕 **MobileParts** (mobileparts.shop) - DE ADĂUGAT
3. 🆕 **MPS Mobile** (mpsmobile.de) - DE ADĂUGAT
4. 🆕 **MMS Mobile** (mmsmobile.de) - DE ADĂUGAT
5. 🆕 **Componenti Digitali** (componentidigitali.com) - DE ADĂUGAT

---

## 🎯 Principii

✅ **MobileSentrix rămâne NESCHIMBAT** - funcționalitatea existentă nu se modifică  
✅ **Adăugăm furnizori noi** - fiecare cu propriul scraper și configurare  
✅ **Procesarea comună** - traducere, categorii, CSV, imagini rămân identice  
✅ **GUI cu selecție furnizor** - dropdown pentru a alege furnizorul  

---

## 📊 Analiză Site-uri (Observații)

### 1. MobileSentrix (mobilesentrix.eu) ✅
- **Status:** Funcționează perfect
- **Structură:** Magento-based, selectori CSS cunoscuți
- **Prețuri:** Publice (nu necesită login)
- **Imagini:** Galerie MagicZoom, JSON-LD

### 2. MobileParts (mobileparts.shop) 🆕
- **Necesită analiză:** Structură HTML, selectori CSS
- **Prețuri:** De verificat (public sau B2B)

### 3. MPS Mobile (mpsmobile.de) 🆕
- **Observație:** B2B - necesită login pentru prețuri ("Show Price" → login)
- **Structură:** Similar cu MobileSentrix (Magento?)
- **Item No.:** 17231, 17583, etc. (coduri produse)
- **Challenge:** Prețurile sunt ascunse fără login

### 4. MMS Mobile (mmsmobile.de) 🆕
- **Observație:** B2B - necesită login pentru prețuri ("Login for Price")
- **Structură:** Similar cu MobileSentrix
- **Challenge:** Prețurile sunt ascunse fără login

### 5. Componenti Digitali (componentidigitali.com) 🆕
- **Observație:** Site italian, structură diferită
- **Prețuri:** De verificat
- **Challenge:** Structură HTML diferită

---

## 🏗️ Plan Implementare Pas cu Pas

### **Faza 1: Refactorizare MobileSentrix (Fără modificări funcționale)**

**Obiectiv:** Mutăm logica MobileSentrix în modul separat, fără să schimbăm comportamentul.

#### Pas 1.1: Creare Structură Module
```
src/
├── scraper/
│   ├── __init__.py
│   ├── base.py              # Clasă abstractă BaseScraper
│   └── mobilesentrix.py     # Scraper MobileSentrix (mutat din import_gui.py)
```

#### Pas 1.2: Mutare Logică MobileSentrix
- Mutăm funcția `scrape_product()` din `import_gui.py` în `src/scraper/mobilesentrix.py`
- Creăm clasa `MobileSentrixScraper(BaseScraper)`
- Păstrăm EXACT aceeași logică (selectori, parsare, etc.)

#### Pas 1.3: Creare Configurare MobileSentrix
```
suppliers/
└── mobilesentrix/
    ├── config.json          # Configurare JSON
    └── sku_list.txt         # Mutăm sku_list.txt aici
```

#### Pas 1.4: Modificare import_gui.py
- Importăm `MobileSentrixScraper` din `src.scraper.mobilesentrix`
- Folosim scraper-ul în loc de logica directă
- **Testăm că funcționează identic**

---

### **Faza 2: Factory și GUI Multi-Furnizor**

#### Pas 2.1: Creare Factory
```
src/scraper/factory.py
```
- `ScraperFactory.get_scraper(supplier_name)` - creează scraper
- `ScraperFactory.list_available_suppliers()` - listează furnizori

#### Pas 2.2: Modificare GUI
- Adăugăm dropdown "Selectează Furnizor" în tab Import
- Când se schimbă furnizorul, se actualizează automat calea `sku_list.txt`
- Modificăm `run_import()` să folosească factory

#### Pas 2.3: Testare MobileSentrix
- Verificăm că totul funcționează identic cu versiunea veche

---

### **Faza 3: Adăugare Furnizori Noi**

Pentru fiecare furnizor nou:

#### Pas 3.1: Analiză Site
- Deschidem pagina unui produs
- Identificăm selectori CSS pentru:
  - Nume produs
  - Preț
  - Descriere
  - Imagini
  - SKU/EAN

#### Pas 3.2: Creare Config JSON
```json
{
  "name": "mobileparts",
  "display_name": "MobileParts.shop",
  "base_url": "https://mobileparts.shop",
  "search_url_template": "{base_url}/search?q={sku}",
  "selectors": {
    "name": ["h1.product-title"],
    "price": [".price"],
    "description": [".description"],
    "images": [".product-images img"]
  },
  "sku_list_file": "suppliers/mobileparts/sku_list.txt",
  "enabled": true
}
```

#### Pas 3.3: Implementare Scraper
```python
# src/scraper/mobileparts.py

class MobilePartsScraper(BaseScraper):
    def find_product_url(self, sku_or_ean):
        # Logica specifică MobileParts
        pass
    
    def extract_name(self, soup):
        # Folosește selectori din config.json
        pass
    
    # ... restul metodelor
```

#### Pas 3.4: Adăugare în Factory
```python
scraper_classes = {
    'mobilesentrix': MobileSentrixScraper,
    'mobileparts': MobilePartsScraper,  # ← Adaugă aici
}
```

#### Pas 3.5: Testare
- Testăm cu câteva produse din `suppliers/mobileparts/sku_list.txt`
- Verificăm că datele extrase sunt corecte

---

## 🔧 Structură Finală Propusă

```
PythonProduse/
├── src/
│   ├── scraper/
│   │   ├── base.py              # BaseScraper (abstract)
│   │   ├── mobilesentrix.py      # ✅ EXISTENT (mutat)
│   │   ├── mobileparts.py        # 🆕 NOU
│   │   ├── mpsmobile.py          # 🆕 NOU
│   │   ├── mmsmobile.py          # 🆕 NOU
│   │   ├── componentidigitali.py # 🆕 NOU
│   │   └── factory.py            # Factory pentru creare scraper
│   │
│   ├── processors/               # NESCHIMBAT
│   ├── images/                   # NESCHIMBAT
│   ├── export/                   # NESCHIMBAT
│   ├── woocommerce/              # NESCHIMBAT
│   ├── io/                       # NESCHIMBAT
│   └── gui/                      # MODIFICAT (dropdown furnizor)
│
├── suppliers/
│   ├── mobilesentrix/
│   │   ├── config.json
│   │   └── sku_list.txt          # Mutat din root
│   ├── mobileparts/
│   │   ├── config.json           # 🆕
│   │   └── sku_list.txt          # 🆕
│   ├── mpsmobile/
│   │   ├── config.json           # 🆕
│   │   └── sku_list.txt          # 🆕
│   ├── mmsmobile/
│   │   ├── config.json           # 🆕
│   │   └── sku_list.txt          # 🆕
│   └── componentidigitali/
│       ├── config.json           # 🆕
│       └── sku_list.txt          # 🆕
│
└── import_gui.py                 # MODIFICAT (folosește factory)
```

---

## ⚠️ Provocări Identificate

### 1. Site-uri B2B (MPS Mobile, MMS Mobile)
**Problema:** Prețurile sunt ascunse fără login  
**Soluție:** 
- Opțiune 1: Scraping fără preț (preț = 0, se completează manual)
- Opțiune 2: Configurare credențiale în `.env` pentru login automat
- Opțiune 3: Utilizatorul se loghează manual în browser, scriptul folosește cookies

### 2. Structuri HTML Diferite
**Problema:** Fiecare site are selectori CSS diferiți  
**Soluție:** Configurare JSON per furnizor cu selectori specifici

### 3. Limbi Diferite
**Problema:** Componenti Digitali e în italiană  
**Soluție:** Traducerea comună (Google Translate/Ollama) funcționează pentru toți

---

## 📝 Checklist Implementare

### Faza 1: Refactorizare MobileSentrix
- [ ] Creează `src/scraper/base.py` (clasă abstractă)
- [ ] Creează `src/scraper/mobilesentrix.py` (mută logica)
- [ ] Creează `suppliers/mobilesentrix/config.json`
- [ ] Mută `sku_list.txt` → `suppliers/mobilesentrix/sku_list.txt`
- [ ] Modifică `import_gui.py` să folosească `MobileSentrixScraper`
- [ ] **TEST:** Verifică că funcționează identic cu versiunea veche

### Faza 2: Factory și GUI
- [ ] Creează `src/scraper/factory.py`
- [ ] Adaugă dropdown furnizor în GUI
- [ ] Modifică `run_import()` să folosească factory
- [ ] **TEST:** Verifică că MobileSentrix funcționează prin factory

### Faza 3: MobileParts
- [ ] Analizează structura site-ului
- [ ] Creează `suppliers/mobileparts/config.json`
- [ ] Implementează `MobilePartsScraper`
- [ ] Adaugă în factory
- [ ] **TEST:** Testează cu câteva produse

### Faza 4: MPS Mobile
- [ ] Analizează structura site-ului
- [ ] Rezolvă problema login (prețuri ascunse)
- [ ] Creează `suppliers/mpsmobile/config.json`
- [ ] Implementează `MPSMobileScraper`
- [ ] **TEST:** Testează cu câteva produse

### Faza 5: MMS Mobile
- [ ] Analizează structura site-ului
- [ ] Rezolvă problema login (prețuri ascunse)
- [ ] Creează `suppliers/mmsmobile/config.json`
- [ ] Implementează `MMSMobileScraper`
- [ ] **TEST:** Testează cu câteva produse

### Faza 6: Componenti Digitali
- [ ] Analizează structura site-ului
- [ ] Creează `suppliers/componentidigitali/config.json`
- [ ] Implementează `ComponentiDigitaliScraper`
- [ ] **TEST:** Testează cu câteva produse

---

## 🎯 Începem cu Faza 1?

Vrei să începem implementarea? Propun să:

1. **Creez structura de module** (Faza 1.1)
2. **Mut logica MobileSentrix** în modul separat (Faza 1.2)
3. **Testez că funcționează identic** (Faza 1.4)

După ce confirmăm că MobileSentrix funcționează perfect prin module, continuăm cu furnizorii noi.

**CSV-ul tău ar fi util** pentru a vedea structura exactă a datelor exportate, dar nu e obligatoriu - pot analiza și direct site-urile pentru selectori CSS.

Vrei să începem cu Faza 1?
