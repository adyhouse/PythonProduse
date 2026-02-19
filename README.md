# 📱 Program Import Produse - MobileSentrix → CSV WooCommerce / Supabase

Program pentru **scraping produse de pe MobileSentrix** și **export CSV** gata de import în **Supabase** / WooCommerce:
- Web scraping (URL-uri sau EAN/SKU din `sku_list.txt`)
- Download imagini + upload pe WordPress (Media)
- Traducere în română (Google Translate sau Ollama)
- Titluri Long Tail SEO, categorii WebGSM, atribute (Model, Calitate, Brand, Tip Produs, Tehnologie)
- **CSV:** SKU gol (generat în Supabase), stoc 0, preț achiziție în EUR, EAN/SKU furnizor
- Detectare garanție, optional Ollama pe rețea

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

- **[REPO_OVERVIEW.md](REPO_OVERVIEW.md)** – **Citează acest fișier** pentru context complet: ce face scriptul, logica CSV, modificări recente, index al tuturor fișierelor .txt/.md și ce se poate modifica.
- [PROGRAM_ARCHITECTURE.md](PROGRAM_ARCHITECTURE.md) – Arhitectură tehnică, flux, funcții, categorii WebGSM
- [GHID_RAPID_CSV.txt](GHID_RAPID_CSV.txt) – Ghid rapid export CSV
- [README_EXTRACTOARE.txt](README_EXTRACTOARE.txt) – Info extractoare

## 🔧 Configurare

Editează `.env` (vezi `.env.example`):
```
WOOCOMMERCE_URL=https://site-tau.com
WOOCOMMERCE_CONSUMER_KEY=ck_...
WOOCOMMERCE_CONSUMER_SECRET=cs_...
EXCHANGE_RATE=4.97
# Upload imagini (utilizator WP real + Application Password, NU Consumer Key):
WP_USERNAME=admin
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx
# Opțional – Ollama pe rețea:
OLLAMA_URL=http://IP_OLLAMA:11434
```

## 📊 Format CSV Output

- **SKU:** gol (generat în Supabase la import)
- **GTIN, UPC, EAN or ISBN** + **meta:gtin_ean** / **meta:sku_furnizor** – EAN/SKU furnizor (cifre)
- **Stock:** 0; **meta:pret_achizitie:** preț în **EUR** (furnizor)
- **Categories** – path (ex. `Piese > Piese iPhone > Ecrane`); **Images** – doar URL-uri WordPress
- **Atribute 1–5:** Model, Calitate, Brand (real), Tip Produs, Tehnologie; toate **global=0**
- Detalii complete: [REPO_OVERVIEW.md](REPO_OVERVIEW.md)

### Categorii WooCommerce (WebGSM)

Categoriile respectă arborele site-ului:
- **Piese** → Piese iPhone/Samsung/Huawei/Xiaomi → Ecrane, Baterii, Camere, Carcase, Difuzoare, Flexuri, Mufe Încărcare (slug-uri: `ecrane-iphone`, `baterii-samsung`, etc.)
- **Unelte** → Șurubelnițe, Pensete, Stații Lipit, Separatoare Ecrane, Microscoape, Programatoare, Kituri Complete
- **Accesorii** → Huse & Carcase, Folii Protecție, Cabluri & Încărcătoare, Adezivi & Consumabile
- **Dispozitive** → Telefoane Folosite, Telefoane Refurbished, Tablete, Smartwatch

La export se folosesc: **path** pentru coloana Categories (`get_woo_category`) și **slug** unde e cazul (`get_webgsm_category`). Slug-urile interzise (nu există în site) nu sunt folosite niciodată. Detalii în [PROGRAM_ARCHITECTURE.md](PROGRAM_ARCHITECTURE.md#categorii-woocommerce-webgsm).

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

**v3.1+** – CSV pentru Supabase: SKU gol, stoc 0, EAN fără apostrof, meta:pret_achizitie EUR, brand real, Atribut 4 Tip Produs / 5 Tehnologie, global=0, coloane noi; upload imagini cu WP_USERNAME/WP_APP_PASSWORD; Test Conexiune cu import woocommerce API; verificare Ollama pe rețea. Documentație: [REPO_OVERVIEW.md](REPO_OVERVIEW.md).

---

**Made with ❤️ for e-commerce automation**
