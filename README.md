# 📱 Program Import Produse - MobileSentrix → CSV WooCommerce

Program automat pentru export și procesare produse din MobileSentrix cu:
- Web scraping intelligent
- Download imagini + upload pe WordPress
- Traducere automată în română (fără diacritice)
- Titluri Long Tail SEO optimizate
- Generare coduri de bare (SKU EAN-13)
- Detectare automată a garanțiilor
- Export direct în CSV format WooCommerce

## ✨ Caracteristici

✅ Extrage date produse complet  
✅ Download și optimizare imagini  
✅ Traducere Google Translate  
✅ Titluri SEO Long Tail  
✅ SKU scanabil (EAN-13)  
✅ Meta data garanție automată  
✅ Export CSV WooCommerce-ready  
✅ Upload imagini pe WordPress

## 🚀 Instalare & Folosire

```bash
# 1. Clonează repo
git clone https://github.com/adyhouse/PythonProduse.git
cd PythonProduse

# 2. Instalează dependințe
pip install -r requirements.txt

# 3. Configurează .env
cp .env.example .env
# Editează .env cu credențiale WooCommerce

# 4. Rulează programul
python import_gui.py

# 5. Adaugă EAN-uri în sku_list.txt
# 6. Click "Exporta CSV"
# 7. Import în WooCommerce
```

## 📚 Documentație

- [PROGRAM_ARCHITECTURE.md](PROGRAM_ARCHITECTURE.md) - Arhitectură tech detaliată
- [GHID_RAPID_CSV.txt](GHID_RAPID_CSV.txt) - Ghid rapid de folosire
- [README_EXTRACTOARE.txt](README_EXTRACTOARE.txt) - Info extractoare

## 🔧 Configurare

Editează `.env`:
```
WOOCOMMERCE_URL=https://site-tau.com
WOOCOMMERCE_CONSUMER_KEY=ck_...
WOOCOMMERCE_CONSUMER_SECRET=cs_...
EXCHANGE_RATE=4.97
```

## 📊 Format CSV Output

Coloane generate:
- **ID, Type, SKU, EAN** - Info produs
- **Name** - Titlu Long Tail SEO (fără diacritice)
- **Price, Stock, Categories** - Vânzări
- **Images** - URL-uri imagini WordPress
- **meta:_warranty_period** - Garanție detectată automat

## 💡 Exemplu

Input: `sku_list.txt`
```
107182127516
888888888888
https://www.mobilesentrix.eu/produs-x
```

Output: `data/export_produse_20260125_120000.csv`
```csv
SKU,EAN,Name,Published,Price,Images,meta:_warranty_period
8902751600000,107182127516,Display iPhone 14 Original Negru,1,2300.00,https://...,12 luni
8908888800000,888888888888,Baterie Samsung Standard Alb,1,1500.00,https://...,6 luni
```

## 🎯 Fluxul Programului

1. **Citire EAN-uri** din `sku_list.txt`
2. **Web Scraping** de pe MobileSentrix
3. **Extragere date** - Nume, Preț, Descriere, Imagini
4. **Procesare**:
   - Genere SKU EAN-13
   - Traducere în română (fără diacritice)
   - Titlu Long Tail SEO
   - Detectare garanție automată
5. **Download & Upload** imagini pe WordPress
6. **Export CSV** cu toți parametrii
7. **Import manual** în WooCommerce

## 📋 Cerințe

- Python 3.8+
- BeautifulSoup4
- Requests
- Pillow (procesare imagini)
- deep-translator (Google Translate)
- python-dotenv (citire .env)
- WooCommerce API

## 🔐 Securitate

⚠️ **Nu commit-a niciodată:**
- `.env` cu credențiale reale
- Imagini din folder `images/`
- Fișierele CSV din `data/` cu date sensibile
- Fișierele din `logs/`

## 🤝 Contribuții

Orice AI, developer sau contributor poate face modificări pe baza [PROGRAM_ARCHITECTURE.md](PROGRAM_ARCHITECTURE.md)

Instrucțiuni detaliate despre arhitectură și cum să modifici codul se găsesc în fișierul de documentație.

## ⚠️ Disclaimer

Program pentru uz personal/comercial. Asigură-te că ai permisiune să scrapezi site-ul țintă (verifică robots.txt și terms of service).

## 📧 Contact

- Repo: https://github.com/adyhouse/PythonProduse
- Issues: Deschide issue pentru bug-uri sau feature requests

## 📅 Versiune

**v3.0** - Long Tail SEO + SKU EAN-13 + Garanție automată  
**Data:** 25.01.2026

---

**Made with ❤️ for e-commerce automation**
