╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                  🚀 START RAPID - IMPORT PRODUSE                           ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝


📦 Program pentru import AUTOMAT de produse MobileSentrix → WooCommerce
   cu interfață grafică, descărcare imagini multiple și funcționalitate completă


═══════════════════════════════════════════════════════════════════════════
                            PORNIRE RAPIDĂ
═══════════════════════════════════════════════════════════════════════════


PENTRU PRIMA UTILIZARE:
────────────────────────────────────────────────────────────────────────────

1. Dublu-click pe: INSTALARE_PYTHON.bat
   ⏱ Așteaptă 3-5 minute
   ⚠️ ÎNCHIDE terminalul după instalare

2. Dublu-click pe: INSTALEAZA_DEPENDINTE.bat
   ⏱ Așteaptă 2-3 minute

3. Dublu-click pe: START_PROGRAM.bat
   ✨ Se deschide interfața grafică!


PENTRU CREARE EXE (OPȚIONAL):
────────────────────────────────────────────────────────────────────────────

După pașii 1-2 de mai sus:

4. Dublu-click pe: COMPILEAZA_EXE.bat
   ⏱ Așteaptă 2-3 minute
   
   📦 EXE-ul va fi în: dist\ImportProduse.exe
   
   ✅ Poți copia acest EXE pe orice calculator Windows
   ✅ NU mai trebuie Python instalat!


UTILIZARE ZILNICĂ:
────────────────────────────────────────────────────────────────────────────

Dublu-click pe: START_PROGRAM.bat

SAU (dacă ai compilat EXE):

Dublu-click pe: dist\ImportProduse.exe


═══════════════════════════════════════════════════════════════════════════
                         CONFIGURARE INIȚIALĂ
═══════════════════════════════════════════════════════════════════════════

La prima pornire a programului:

1. Mergi la tab: ⚙ CONFIGURARE

2. Completează:
   • URL WooCommerce: https://webgsm.ro
   • Consumer Key: (obține de la WooCommerce → Setări → REST API)
   • Consumer Secret: (obține de la WooCommerce → Setări → REST API)
   • Curs EUR/RON: 4.97

3. Click: 💾 Salvează Configurare

4. Click: 🔍 Test Conexiune (verifică că merge)


═══════════════════════════════════════════════════════════════════════════
                           IMPORT PRODUSE
═══════════════════════════════════════════════════════════════════════════

1. Editează fișierul: sku_list.txt
   • Adaugă SKU-urile produselor (unul pe linie)
   • Exemplu:
     SAMSUNG-S24-128GB
     IPHONE-15-PRO-256GB
     HUSA-SAMSUNG-CLEAR

2. În program, mergi la tab: 📦 IMPORT PRODUSE

3. Verifică că sunt bifate:
   ☑ Descarcă toate imaginile produsului
   ☑ Optimizează imaginile
   ☑ Convertește prețul EUR → RON
   ☑ Extrage descriere în română

4. Click: 🚀 START IMPORT

5. Urmărește progresul în timp real!


═══════════════════════════════════════════════════════════════════════════
                              FIȘIERE
═══════════════════════════════════════════════════════════════════════════

📄 START_PROGRAM.bat ............. Pornește programul
📄 INSTALARE_PYTHON.bat .......... Instalează Python
📄 INSTALEAZA_DEPENDINTE.bat ..... Instalează pachete necesare
📄 COMPILEAZA_EXE.bat ............ Creează EXE standalone

📄 sku_list.txt .................. Lista cu SKU-uri pentru import
📄 GHID_UTILIZARE.txt ............ Documentație completă
📄 IMPORT_FISIER_GHID.txt ........ Ghid import din fișiere

📁 logs/ ......................... Log-uri importuri
📁 images/ ....................... Imagini descărcate
📁 dist/ ......................... EXE compilat (după compilare)


═══════════════════════════════════════════════════════════════════════════
                            PROBLEME?
═══════════════════════════════════════════════════════════════════════════

• Citește GHID_UTILIZARE.txt pentru detalii complete
• Verifică tab Log din program pentru erori
• Verifică fișierele din logs/ pentru detalii


═══════════════════════════════════════════════════════════════════════════

✨ FUNCȚIONALITĂȚI:

✅ Interfață grafică simplă - fără linie de comandă!
✅ Descarcă 3-5 imagini per produs la rezoluție mare
✅ Optimizare automată imagini
✅ Web scraping de pe mobilesentrix.eu
✅ Convertire EUR → RON automată
✅ Import direct în WooCommerce
✅ Se poate compila în EXE (fără Python)

════════════════════════════════════════════════════════════════════════════
Versiune 2.0 | Ianuarie 2026
════════════════════════════════════════════════════════════════════════════
