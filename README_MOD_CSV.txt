╔═══════════════════════════════════════════════════════════════════╗
║   PROGRAM EXPORT PRODUSE → CSV (Versiune Modificată)             ║
║   Data modificării: 17 ianuarie 2026                              ║
╚═══════════════════════════════════════════════════════════════════╝

🔄 CE S-A MODIFICAT:
═══════════════════════

✅ Programul NU mai introduce produse în WooCommerce
✅ Creează un fișier CSV cu toate produsele procesate
✅ Descarcă și salvează toate imaginile LOCAL în folderul "images/"
✅ CSV-ul include path-urile către imaginile salvate

📋 STRUCTURA CSV-ULUI:
═══════════════════════

Fișierul CSV creat va avea următoarele coloane:

1. EAN                     - Codul EAN de pe MobileSentrix
2. SKU                     - SKU generat automat (format WEBGSM-XXXXXX-XXXX)
3. Nume                    - Numele produsului extras de pe MobileSentrix
4. Preț EUR                - Prețul în EURO de pe site
5. Preț RON                - Prețul convertit în RON (dacă opțiunea e activată)
6. Descriere               - Descrierea produsului (primele 500 caractere)
7. Imagine Principală      - Path-ul către prima imagine (ex: images/123456_1.jpg)
8. Imagini Suplimentare    - Path-uri către imaginile 2-5 (separate prin ;)
9. Total Imagini           - Numărul total de imagini descărcate


🚀 CUM UTILIZEZ PROGRAMUL:
═══════════════════════════

1. Deschide START_PROGRAM.bat (sau rulează direct import_gui.py)

2. În tab-ul "Export CSV":
   - Selectează fișierul sku_list.txt cu EAN-urile dorite
   - Bifează opțiunile:
     ✓ Descarcă toate imaginile produsului
     ✓ Optimizează imaginile (resize)
     ✓ Convertește prețul EUR → RON
     ✓ Extrage descriere în română

3. Click pe "🚀 START EXPORT CSV"

4. Programul va:
   - Accesa fiecare EAN de pe MobileSentrix
   - Extrage date produs (nume, preț, descriere)
   - Descărca TOATE imaginile și le salvează în "images/"
   - Crea un fișier CSV în folderul "data/"

5. La final vei avea:
   📁 data/export_produse_YYYYMMDD_HHMMSS.csv  ← CSV-ul cu toate datele
   📁 images/                                   ← Toate imaginile descărcate


📁 FIȘIERE GENERATE:
═══════════════════

data/export_produse_20260117_150000.csv    (exemplu)
images/840056141162_1.jpg
images/840056141162_2.jpg
images/840056141162_3.jpg
images/840056155755_1.jpg
...


⚙️ CONFIGURARE (Optional):
══════════════════════════

Tab-ul "Configurare" NU mai este necesar pentru export CSV!

Poți totuși seta:
- Cursul EUR → RON (implicit 4.97)

Credențialele WooCommerce NU mai sunt necesare - programul nu mai
accesează API-ul WooCommerce.


💡 CE FACI CU CSV-UL:
═══════════════════════

După ce programul termină exportul, poți:

1. Deschide CSV-ul în Excel/LibreOffice pentru verificare
2. Folosește CSV-ul pentru import manual în WooCommerce
3. Folosește un plugin WordPress de import CSV:
   - WP All Import
   - WooCommerce Product CSV Import Suite
   - Product Import Export for WooCommerce

4. Imaginile sunt deja descărcate local - le poți urca separat pe server


📊 EXEMPLU CSV REZULTAT:
════════════════════════

EAN,SKU,Nume,Preț EUR,Preț RON,Descriere,...,Imagine Principală,Imagini Suplimentare
840056141162,WEBGSM-141162-1234,Display iPhone 13,45.50,226.24,"Display...",images/840056141162_1.jpg,images/840056141162_2.jpg; images/840056141162_3.jpg


🆘 SUPORT ȘI PROBLEME:
═══════════════════════

❓ Nu găsește produsul?
   → Verifică că EAN-ul este corect pe MobileSentrix
   → Programul va raporta în LOG dacă produsul nu există

❓ Nu descarcă imagini?
   → Verifică conexiunea la internet
   → Verifică că opțiunea "Descarcă imagini" este bifată

❓ CSV-ul nu se deschide corect în Excel?
   → CSV-ul folosește encoding UTF-8 cu BOM
   → În Excel: Data → From Text/CSV → selectează UTF-8


📝 NOTE IMPORTANTE:
═══════════════════

⚠️ Programul NU mai inserează produse în WooCommerce automat!
⚠️ Toate imaginile sunt salvate în folderul "images/" - asigură-te
   că ai suficient spațiu pe disk.
⚠️ Pentru fiecare produs se descarcă maxim 5 imagini
⚠️ Imaginile sunt optimizate (resize la 1200x1200px) dacă opțiunea
   este activată


🔗 FLUXUL DE LUCRU RECOMANDAT:
══════════════════════════════

1. Rulează programul → Generează CSV + Imagini
2. Verifică CSV-ul în Excel
3. Corectează manual dacă e nevoie (prețuri, descrieri)
4. Urcă imaginile pe server (FTP sau Media Library)
5. Importă CSV-ul în WooCommerce cu un plugin
6. Asociază imaginile cu produsele


✅ AVANTAJE MODUL CSV:
═══════════════════════

✓ Control complet asupra datelor înainte de import
✓ Posibilitate editare manuală în Excel
✓ Fără risc de "phantom products" în baza de date
✓ Poți rula exportul de mai multe ori fără probleme
✓ Imaginile sunt salvate local (backup)
✓ Flexibilitate la import (poți alege ce produse să imporți)


═══════════════════════════════════════════════════════════════════
Programul a fost modificat la cererea utilizatorului.
Original: Import automat în WooCommerce
Modificat: Export CSV cu imagini locale
═══════════════════════════════════════════════════════════════════
