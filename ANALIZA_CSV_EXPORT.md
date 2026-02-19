# 📊 Analiză CSV Export - Structură Actuală

## 📋 Observații din CSV-ul Exportat

### Structură Coloane (din CSV)

**Coloane Principale:**
- `ID` - gol (""), corect
- `Type` - "simple", corect
- `SKU` - gol (""), corect (generat în Supabase)
- `GTIN, UPC, EAN, or ISBN` - **'107082130502** (cu apostrof la început)
- `Name` - titlu tradus în română, corect
- `Published` - "0" (draft), corect
- `In stock?` - "0", corect
- `Stock` - "0", corect
- `Regular price` - preț în RON (129.83, 8.11, etc.), corect
- `Categories` - path format ("Piese > Piese iPhone > Ecrane"), corect
- `Images` - URL-uri WordPress (nu MobileSentrix), corect

**Atribute (1-5):**
- `Attribute 1` - Model Compatibil ("iPhone 15", "iPhone 15 Pro", etc.)
- `Attribute 2` - Calitate ("Aftermarket")
- `Attribute 3` - Brand Piesa (gol sau "Samsung")
- `Attribute 4` - Tip Produs ("Ecran", "Flex")
- `Attribute 5` - Tehnologie ("Incell", "Soft OLED", etc.)
- Toate au `visible = "1"` și `global = "0"`, corect

**Meta Fields:**
- `meta:gtin_ean` - **'107082130502** (cu apostrof)
- `meta:sku_furnizor` - **'107082130502** (cu apostrof)
- `meta:furnizor_activ` - **"mobilesentrix"** (hardcodat)
- `meta:pret_achizitie` - preț în EUR (96.76, 6.05, etc.), corect
- `meta:locatie_stoc` - "indisponibil", "precomanda", corect
- `meta:garantie_luni` - "12", "6", corect
- `meta:coduri_compatibilitate` - "A1549, A1586, A1589", corect
- `meta:source_url` - link MobileSentrix, corect

**SEO Rank Math:**
- `meta:rank_math_title` - titlu SEO
- `meta:rank_math_description` - descriere SEO
- `meta:rank_math_focus_keyword` - keyword SEO

---

## ⚠️ Observații Importante

### 1. Apostrof la EAN
**CSV actual:** `'107082130502` (cu apostrof)  
**Documentație:** spune "cifre fără apostrof"  
**Concluzie:** Trebuie clarificat - probabil apostroful e necesar pentru Excel să nu convertească în științific

### 2. meta:furnizor_activ Hardcodat
**CSV actual:** `"mobilesentrix"` (hardcodat)  
**Pentru multi-furnizor:** Trebuie dinamic (din scraper)

### 3. meta:source_url Hardcodat MobileSentrix
**CSV actual:** `https://www.mobilesentrix.eu/...`  
**Pentru multi-furnizor:** Trebuie dinamic (din scraper)

---

## 🎯 Modificări Necesare pentru Multi-Furnizor

### În `export_to_csv()`:

```python
# ÎNAINTE (hardcodat):
'meta:furnizor_activ': 'mobilesentrix',
'meta:source_url': product.get('source_url', ''),  # Deja dinamic, OK

# DUPĂ (dinamic):
'meta:furnizor_activ': product.get('supplier', 'mobilesentrix'),  # Din scraper
'meta:source_url': product.get('source_url', ''),  # Rămâne dinamic
```

### În `scrape_product()` (sau în scraper-ul nou):

```python
# Scraper-ul trebuie să returneze:
{
    'name': '...',
    'price': 96.76,
    'description': '...',
    'images': [...],
    'sku_ean': {'sku': '107082130502', 'ean': '107082130502'},
    'source_url': 'https://www.mobilesentrix.eu/...',
    'supplier': 'mobilesentrix',  # ← NOU - nume furnizor
    # ... restul câmpurilor
}
```

---

## 📝 Structură Date Produs (product_data)

Din analiza CSV și cod, structura `product_data` trebuie să conțină:

```python
product_data = {
    # Date de bază
    'name': str,                    # Nume original (EN)
    'price': float,                 # Preț EUR
    'description': str,             # Descriere completă
    'images': List[Dict],          # Lista imagini (cu local_path, src, etc.)
    
    # Identificare
    'sku_furnizor': str,            # SKU de la furnizor ('107082130502)
    'ean': str,                     # EAN de la furnizor
    'source_url': str,              # URL produs pe site-ul furnizorului
    'supplier': str,                # Nume furnizor ('mobilesentrix', 'mobileparts', etc.)
    
    # Procesare (după scraping)
    'pa_model': str,                # Model compatibil (iPhone 15, etc.)
    'pa_calitate': str,             # Calitate (Aftermarket, etc.)
    'pa_brand_piesa': str,          # Brand real (Samsung, etc.)
    'pa_tehnologie': str,           # Tehnologie (Incell, OLED, etc.)
    'category_path': str,           # Path categorie (Piese > Piese iPhone > Ecrane)
    'category_slug': str,           # Slug categorie (ecrane-iphone)
    'tags': List[str],              # Tag-uri
    'warranty': str,                # Garanție (12 luni, etc.)
    
    # Altele
    'manual_category_code': str,    # Cod manual din sku_list (BAT, SCR, etc.)
    'locatie_stoc': str,            # indisponibil, precomanda, etc.
    'coduri_compatibilitate': str,  # A1549, A1586, etc.
    'ic_movable': str,              # 0 sau 1
    'truetone_support': str,        # 0 sau 1
}
```

---

## ✅ Concluzii pentru Multi-Furnizor

1. **meta:furnizor_activ** → trebuie dinamic din `product_data['supplier']`
2. **meta:source_url** → deja dinamic, OK
3. **EAN cu apostrof** → păstrăm apostroful (probabil necesar pentru Excel)
4. **Restul câmpurilor** → rămân identice pentru toți furnizorii

---

**Data analiză**: 19.02.2026  
**CSV analizat**: export_webgsm_20260214_191652.csv
