"""
Program Import Produse MobileSentrix → CSV (cu Imagini)
Versiune: 2.0 - cu GUI, download imagini și upload WordPress
"""

import sys
import os

# Fix encoding for Windows
try:
    if sys.platform == 'win32':
        os.environ['PYTHONIOENCODING'] = 'utf-8'
except:
    pass

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json
import threading
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv, set_key
import re
import html
import uuid
import time
from deep_translator import GoogleTranslator

class ImportProduse:
    def __init__(self, root):
        self.root = root
        self.root.title("Export Produse MobileSentrix → CSV (cu Imagini)")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # Variabile
        self.env_file = Path(".env")
        self.config = {}
        self.running = False
        
        # Creare directoare
        Path("logs").mkdir(exist_ok=True)
        Path("images").mkdir(exist_ok=True)
        Path("data").mkdir(exist_ok=True)
        
        # Load config
        self.load_config()
        
        # Load category rules (keyword → category path)
        self.category_rules = self.load_category_rules()
        
        # Setup GUI
        self.setup_gui()
        
    def setup_gui(self):
        """Creează interfața grafică"""
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Notebook (tabs)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Export CSV
        tab_import = ttk.Frame(notebook)
        notebook.add(tab_import, text='📦 Export CSV')
        
        # Tab 2: Configurare
        tab_config = ttk.Frame(notebook)
        notebook.add(tab_config, text='⚙ Configurare')
        
        # Tab 3: Log
        tab_log = ttk.Frame(notebook)
        notebook.add(tab_log, text='📋 Log')
        
        self.setup_import_tab(tab_import)
        self.setup_config_tab(tab_config)
        self.setup_log_tab(tab_log)
        
    def setup_import_tab(self, parent):
        """Setup tab Import"""
        
        # Frame SKU/LINK
        frame_sku = ttk.LabelFrame(parent, text="Selectează fișier cu link-uri sau EAN-uri", padding=10)
        frame_sku.pack(fill='x', padx=10, pady=10)
        
        # Info box despre modul CSV
        info_frame = ttk.Frame(frame_sku)
        info_frame.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(0, 10))
        info_label = ttk.Label(info_frame, text="ℹ️ MOD CSV: Pune link-uri directe din MobileSentrix în sku_list.txt (ex: https://www.mobilesentrix.eu/product-name/) SAU EAN-uri. Program extrage: Nume, Preț EUR/RON, Descriere, Pozele MARI + cont. CSV cu tot.", 
                              foreground="blue", wraplength=800)
        info_label.pack(anchor='w')
        
        self.sku_file_var = tk.StringVar(value="sku_list.txt")
        
        ttk.Label(frame_sku, text="Fișier:").grid(row=1, column=0, sticky='w', padx=5)
        ttk.Entry(frame_sku, textvariable=self.sku_file_var, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(frame_sku, text="Răsfoire...", command=self.browse_sku_file).grid(row=1, column=2, padx=5)
        
        # Opțiuni import
        frame_options = ttk.LabelFrame(parent, text="Opțiuni Import", padding=10)
        frame_options.pack(fill='x', padx=10, pady=10)
        
        self.download_images_var = tk.BooleanVar(value=True)
        self.optimize_images_var = tk.BooleanVar(value=False)  # ❌ DEZACTIVAT - descarcă pozele MARI
        self.convert_price_var = tk.BooleanVar(value=True)
        self.extract_description_var = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(frame_options, text="Descarcă toate imaginile produsului", 
                       variable=self.download_images_var).grid(row=0, column=0, sticky='w', padx=5, pady=2)
        ttk.Checkbutton(frame_options, text="Optimizează imaginile (resize)", 
                       variable=self.optimize_images_var).grid(row=1, column=0, sticky='w', padx=5, pady=2)
        ttk.Checkbutton(frame_options, text="Convertește prețul EUR → RON", 
                       variable=self.convert_price_var).grid(row=2, column=0, sticky='w', padx=5, pady=2)
        ttk.Checkbutton(frame_options, text="Extrage descriere în română", 
                       variable=self.extract_description_var).grid(row=3, column=0, sticky='w', padx=5, pady=2)
        
        # Progress
        frame_progress = ttk.Frame(parent)
        frame_progress.pack(fill='x', padx=10, pady=10)
        
        self.progress_var = tk.StringVar(value="Pregătit pentru export CSV")
        ttk.Label(frame_progress, textvariable=self.progress_var).pack(anchor='w')
        
        self.progress_bar = ttk.Progressbar(frame_progress, mode='indeterminate')
        self.progress_bar.pack(fill='x', pady=5)
        
        # Butoane
        frame_buttons = ttk.Frame(parent)
        frame_buttons.pack(fill='x', padx=10, pady=10)
        
        self.btn_start = ttk.Button(frame_buttons, text="🚀 START EXPORT CSV", 
                                     command=self.start_import, style='Accent.TButton')
        self.btn_start.pack(side='left', padx=5)
        
        self.btn_stop = ttk.Button(frame_buttons, text="⛔ STOP", 
                                    command=self.stop_import, state='disabled')
        self.btn_stop.pack(side='left', padx=5)
        
        ttk.Button(frame_buttons, text="📄 Deschide sku_list.txt", 
                  command=lambda: os.startfile("sku_list.txt")).pack(side='right', padx=5)
        
    def setup_config_tab(self, parent):
        """Setup tab Configurare"""
        
        frame = ttk.LabelFrame(parent, text="Configurare WooCommerce API", padding=20)
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # WooCommerce URL
        ttk.Label(frame, text="URL WooCommerce:").grid(row=0, column=0, sticky='w', pady=10)
        self.wc_url_var = tk.StringVar(value=self.config.get('WOOCOMMERCE_URL', 'https://webgsm.ro'))
        ttk.Entry(frame, textvariable=self.wc_url_var, width=50).grid(row=0, column=1, pady=10, padx=10)
        
        # Consumer Key
        ttk.Label(frame, text="Consumer Key:").grid(row=1, column=0, sticky='w', pady=10)
        self.wc_key_var = tk.StringVar(value=self.config.get('WOOCOMMERCE_CONSUMER_KEY', ''))
        ttk.Entry(frame, textvariable=self.wc_key_var, width=50, show='*').grid(row=1, column=1, pady=10, padx=10)
        
        # Consumer Secret
        ttk.Label(frame, text="Consumer Secret:").grid(row=2, column=0, sticky='w', pady=10)
        self.wc_secret_var = tk.StringVar(value=self.config.get('WOOCOMMERCE_CONSUMER_SECRET', ''))
        ttk.Entry(frame, textvariable=self.wc_secret_var, width=50, show='*').grid(row=2, column=1, pady=10, padx=10)
        
        # Curs EUR/RON
        ttk.Label(frame, text="Curs EUR → RON:").grid(row=3, column=0, sticky='w', pady=10)
        self.exchange_rate_var = tk.StringVar(value=self.config.get('EXCHANGE_RATE', '4.97'))
        ttk.Entry(frame, textvariable=self.exchange_rate_var, width=20).grid(row=3, column=1, sticky='w', pady=10, padx=10)
        
        # Butoane
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="💾 Salvează Configurare", 
                  command=self.save_config).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="🔍 Test Conexiune", 
                  command=self.test_connection).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="🔄 Reîncarcă Config", 
                  command=self.reload_config).pack(side='left', padx=5)
        
        # Info box
        info_frame = ttk.LabelFrame(frame, text="ℹ️ Informații", padding=10)
        info_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky='ew')
        
        info_text = """
📍 Cum obții API Keys:
   1. WordPress Admin → WooCommerce → Settings
   2. Tab "Advanced" → Sub-tab "REST API"
   3. Click "Add key"
   4. Description: "Import Produse"
   5. Permissions: "Read/Write"
   6. Generate și copiază Consumer Key și Secret

⚠️ URL fără / la final: https://webgsm.ro (corect)
        """
        ttk.Label(info_frame, text=info_text.strip(), justify='left', 
                 font=('Consolas', 8)).pack(anchor='w')
        
    def setup_log_tab(self, parent):
        """Setup tab Log"""
        
        self.log_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, 
                                                   font=('Consolas', 9))
        self.log_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Butoane
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(btn_frame, text="🗑 Șterge Log", 
                  command=lambda: self.log_text.delete(1.0, tk.END)).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="📁 Deschide Folder Logs", 
                  command=lambda: os.startfile("logs")).pack(side='left', padx=5)
        
    def log(self, message, level='INFO'):
        """Adaugă mesaj în log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.root.update()
    
    def cleanup_orphans(self):
        """Curăță produse orfane din WooCommerce (înainte de import)"""
        try:
            self.log("=" * 70, "INFO")
            self.log("🧹 CURĂȚARE ORFANE - Găsire și ștergere produse incomplete", "INFO")
            self.log("=" * 70, "INFO")
            
            if not self.wc_api:
                # Inițializează API
                self.wc_api = API(
                    url=self.config['WOOCOMMERCE_URL'],
                    consumer_key=self.config['WOOCOMMERCE_CONSUMER_KEY'],
                    consumer_secret=self.config['WOOCOMMERCE_CONSUMER_SECRET'],
                    version="wc/v3",
                    timeout=30
                )
            
            # Caută TOATE produsele (cu pagina mare)
            self.log("📊 Descarcă lista completă de produse din WooCommerce...", "INFO")
            all_products = []
            page = 1
            per_page = 100
            max_pages = 50  # Safety limit
            
            while page <= max_pages:
                try:
                    response = self.wc_api.get("products", params={"page": page, "per_page": per_page, "status": "any"})
                    
                    if response.status_code != 200:
                        self.log(f"⚠️ Status {response.status_code} la pagina {page} - Opresc descărcarea", "WARNING")
                        break
                    
                    products = response.json()
                    if not products or len(products) == 0:
                        self.log(f"  📖 Pagina {page}: 0 produse - Am ajuns la final", "INFO")
                        break
                    
                    all_products.extend(products)
                    self.log(f"  📖 Pagina {page}: {len(products)} produse", "INFO")
                    page += 1
                    
                except Exception as page_error:
                    self.log(f"⚠️ Eroare la pagina {page}: {page_error}", "WARNING")
                    break
            
            if len(all_products) == 0:
                self.log("⚠️ API-ul returnează 0 produse! Posibil probleme cu API sau autentificare.", "WARNING")
                self.log("🔍 Voi incerca să identific orfane prin alt metod...", "INFO")
                
                # Fallback: Încearcă o cerere simplă
                try:
                    simple_response = self.wc_api.get("products")
                    simple_products = simple_response.json()
                    if simple_products and len(simple_products) > 0:
                        all_products = simple_products
                        self.log(f"✓ Am găsit {len(all_products)} produse cu metoda alternativă", "INFO")
                except:
                    pass
            
            # Dacă inca nu au produse, încearcă fără parametri
            if len(all_products) == 0:
                self.log("⚠️ Curățare orfane nu a putut descărca produse. Continuez importul...", "WARNING")
                self.log("💡 Dacă apare 'Duplicate entry', programul va curăța automat.", "INFO")
                return
            
            self.log(f"✓ Total descărcat: {len(all_products)} produse", "INFO")
            
            # Identifică produse problematice (fără SKU valid sau cu meta_data incompletă)
            orphans_to_delete = []
            
            for prod in all_products:
                product_id = prod.get('id')
                product_sku = prod.get('sku', '')
                product_status = prod.get('status', '')
                product_name = prod.get('name', 'N/A')
                
                # Verifică dacă e produs incomplet:
                has_ean = any(m.get('key') == '_ean' for m in prod.get('meta_data', []))
                
                if product_sku.startswith('WEBGSM-') and (product_status in ['trash', 'draft'] or not has_ean):
                    orphans_to_delete.append({
                        'id': product_id,
                        'sku': product_sku,
                        'status': product_status,
                        'name': product_name
                    })
            
            if not orphans_to_delete:
                self.log("✅ Nu sunt orfane! Baza de date e curată.", "SUCCESS")
                return
            
            self.log(f"⚠️ Găsite {len(orphans_to_delete)} produse incomplete/orfane:", "WARNING")
            
            for orphan in orphans_to_delete:
                self.log(f"   ID: {orphan['id']} | SKU: {orphan['sku']} | Status: {orphan['status']}", "WARNING")
            
            # Șterge orfanele
            deleted_count = 0
            for orphan in orphans_to_delete:
                try:
                    response = self.wc_api.delete(f"products/{orphan['id']}", params={"force": True})
                    if response.status_code in [200, 204]:
                        deleted_count += 1
                        self.log(f"   ✓ Șters ID {orphan['id']}", "SUCCESS")
                    else:
                        self.log(f"   ✗ Nu s-a putut șterge ID {orphan['id']} (status {response.status_code})", "ERROR")
                except Exception as e:
                    self.log(f"   ✗ Eroare la ștergere ID {orphan['id']}: {e}", "ERROR")
            
            self.log(f"🧹 Curățare completă: {deleted_count}/{len(orphans_to_delete)} orfane șterse", "INFO")
            self.log("=" * 70, "INFO")
            
        except Exception as e:
            self.log(f"❌ Eroare curățare: {e}", "ERROR")
    
    def load_config(self):
        """Încarcă configurația din .env"""
        # Setări default
        self.config = {
            'WOOCOMMERCE_URL': 'https://webgsm.ro',
            'WOOCOMMERCE_CONSUMER_KEY': '',
            'WOOCOMMERCE_CONSUMER_SECRET': '',
            'EXCHANGE_RATE': '4.97'
        }
        
        # Încarcă din .env dacă există
        if self.env_file.exists():
            try:
                load_dotenv(self.env_file)
                self.config = {
                    'WOOCOMMERCE_URL': os.getenv('WOOCOMMERCE_URL', 'https://webgsm.ro'),
                    'WOOCOMMERCE_CONSUMER_KEY': os.getenv('WOOCOMMERCE_CONSUMER_KEY', ''),
                    'WOOCOMMERCE_CONSUMER_SECRET': os.getenv('WOOCOMMERCE_CONSUMER_SECRET', ''),
                    'EXCHANGE_RATE': os.getenv('EXCHANGE_RATE', '4.97')
                }
                print(f"✓ Config încărcat din .env: {self.config}")
            except Exception as e:
                print(f"✗ Eroare la încărcarea config: {e}")
        else:
            print("ℹ Fișierul .env nu există, folosim valori default")
        
    def save_config(self):
        """Salvează configurația în .env"""
        try:
            # Validare date
            url = self.wc_url_var.get().strip()
            key = self.wc_key_var.get().strip()
            secret = self.wc_secret_var.get().strip()
            rate = self.exchange_rate_var.get().strip()
            
            if not url:
                messagebox.showwarning("Atenție", "URL-ul WooCommerce este obligatoriu!")
                return
            
            if not key or not secret:
                messagebox.showwarning("Atenție", "Consumer Key și Secret sunt obligatorii!")
                return
            
            # Verifică URL (elimină / de la final dacă există)
            if url.endswith('/'):
                url = url[:-1]
                self.wc_url_var.set(url)
            
            # Validare curs valutar
            try:
                float(rate)
            except ValueError:
                messagebox.showwarning("Atenție", "Cursul valutar trebuie să fie un număr valid!")
                return
            
            # Crează sau actualizează .env
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.write(f"WOOCOMMERCE_URL={url}\n")
                f.write(f"WOOCOMMERCE_CONSUMER_KEY={key}\n")
                f.write(f"WOOCOMMERCE_CONSUMER_SECRET={secret}\n")
                f.write(f"EXCHANGE_RATE={rate}\n")
            
            # Actualizează config intern
            self.config = {
                'WOOCOMMERCE_URL': url,
                'WOOCOMMERCE_CONSUMER_KEY': key,
                'WOOCOMMERCE_CONSUMER_SECRET': secret,
                'EXCHANGE_RATE': rate
            }
            
            # Resetează API pentru a folosi noile credențiale
            self.wc_api = None
            
            self.log("✓ Configurație salvată cu succes!", "SUCCESS")
            self.log(f"   URL: {url}", "INFO")
            self.log(f"   Curs: {rate} RON/EUR", "INFO")
            messagebox.showinfo("Succes", "Configurația a fost salvată!\n\nPoți testa conexiunea acum.")
            
        except Exception as e:
            self.log(f"✗ Eroare salvare configurație: {e}", "ERROR")
            import traceback
            self.log(f"   Traceback: {traceback.format_exc()}", "ERROR")
            messagebox.showerror("Eroare", f"Nu s-a putut salva configurația:\n{e}")
    
    def reload_config(self):
        """Reîncarcă configurația din .env"""
        try:
            self.load_config()
            
            # Actualizează câmpurile GUI
            self.wc_url_var.set(self.config.get('WOOCOMMERCE_URL', 'https://webgsm.ro'))
            self.wc_key_var.set(self.config.get('WOOCOMMERCE_CONSUMER_KEY', ''))
            self.wc_secret_var.set(self.config.get('WOOCOMMERCE_CONSUMER_SECRET', ''))
            self.exchange_rate_var.set(self.config.get('EXCHANGE_RATE', '4.97'))
            
            self.log("🔄 Configurație reîncărcată din .env", "INFO")
            messagebox.showinfo("Succes", "Configurația a fost reîncărcată din fișier!")
            
        except Exception as e:
            self.log(f"✗ Eroare reîncarcare config: {e}", "ERROR")
            messagebox.showerror("Eroare", f"Nu s-a putut reîncărca configurația:\n{e}")
    
    def generate_unique_sku(self, ean):
        """Generează SKU secvențial în format EAN-13 cu prefix 890"""
        # Format: 890 + [ID 5 cifre secvențial] + 00000 = 13 cifre (EAN-13)
        # Prefix 890 = GS1 standard pentru utilizare internă
        # Ușor de scris și memorat
        
        # Folosește ultima parte din EAN ca ID secvențial (0-99999)
        ean_int = int(ean) if ean.isdigit() else int(''.join(c for c in ean if c.isdigit()))
        sequential_id = (ean_int % 100000)  # Obține 5 cifre din EAN
        
        # Format: 890 + ID (5 cifre) + 00000
        sku = f"890{sequential_id:05d}00000"
        
        return sku
    
    def test_connection(self):
        """Testează conexiunea la WooCommerce"""
        try:
            self.log("Testez conexiunea la WooCommerce...", "INFO")
            
            wcapi = API(
                url=self.wc_url_var.get(),
                consumer_key=self.wc_key_var.get(),
                consumer_secret=self.wc_secret_var.get(),
                version="wc/v3",
                timeout=30
            )
            
            # Test request
            response = wcapi.get("products", params={"per_page": 1})
            
            if response.status_code == 200:
                self.log("✓ Conexiune reușită la WooCommerce!", "SUCCESS")
                messagebox.showinfo("Succes", "Conexiunea la WooCommerce este funcțională!")
                self.wc_api = wcapi
            else:
                self.log(f"✗ Eroare conexiune: Status {response.status_code}", "ERROR")
                messagebox.showerror("Eroare", f"Status Code: {response.status_code}\n{response.text}")
                
        except Exception as e:
            self.log(f"✗ Eroare conexiune: {e}", "ERROR")
            messagebox.showerror("Eroare", f"Nu s-a putut conecta la WooCommerce:\n{e}")
    
    def browse_sku_file(self):
        """Selectează fișier SKU"""
        filename = filedialog.askopenfilename(
            title="Selectează fișierul cu SKU-uri",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if filename:
            self.sku_file_var.set(filename)
    
    def start_import(self):
        """Pornește importul"""
        if not Path(self.sku_file_var.get()).exists():
            messagebox.showerror("Eroare", f"Fișierul {self.sku_file_var.get()} nu există!")
            return
        
        self.running = True
        self.btn_start.config(state='disabled')
        self.btn_stop.config(state='normal')
        self.progress_bar.start()
        
        # Rulează import în thread separat
        thread = threading.Thread(target=self.run_import, daemon=True)
        thread.start()
    
    def stop_import(self):
        """Oprește importul"""
        self.running = False
        self.log("⛔ Import oprit de utilizator", "WARNING")
        self.progress_bar.stop()
        self.btn_start.config(state='normal')
        self.btn_stop.config(state='disabled')
        self.progress_var.set("Import oprit")
    
    def run_import(self):
        """Execută exportul în CSV cu upload imagini pe WordPress"""
        try:
            self.log("=" * 70, "INFO")
            self.log(f"🚀 START PROCESARE PRODUSE (Mod: CSV + Upload Imagini)", "INFO")
            self.log("=" * 70, "INFO")
            
            # Citește SKU-uri
            skus = self.read_sku_file(self.sku_file_var.get())
            self.log(f"📋 Găsite {len(skus)} SKU-uri pentru procesare", "INFO")
            
            success_count = 0
            error_count = 0
            woo_success = 0
            woo_errors = 0
            products_data = []  # Lista pentru CSV
            
            for idx, sku in enumerate(skus, 1):
                if not self.running:
                    break
                
                self.progress_var.set(f"Procesez produs {idx}/{len(skus)}: {sku}")
                self.log(f"\n" + "="*70, "INFO")
                self.log(f"[{idx}/{len(skus)}] 🔵 START procesare EAN: {sku}", "INFO")
                self.log(f"="*70, "INFO")
                
                try:
                    # Scraping produs de pe MobileSentrix
                    product_data = self.scrape_product(sku)
                    
                    if product_data:
                        # Salvează SKU-ul furnizor înainte de a fi suprascris
                        supplier_sku = product_data.get('sku', '')  # SKU de la furnizor (107182127516)
                        
                        # Adaugă date suplimentare
                        product_data['sku_generated'] = self.generate_unique_sku(sku)  # SKU generat WEBGSM
                        product_data['supplier_sku'] = supplier_sku  # SKU furnizor (pentru EAN în CSV)
                        product_data['ean'] = sku
                        
                        success_count += 1
                        self.log(f"✓ Produs procesat cu succes!", "SUCCESS")
                        
                        # Salvează în listă pentru CSV
                        products_data.append(product_data)
                    else:
                        error_count += 1
                        self.log(f"✗ Nu s-au putut extrage datele produsului", "ERROR")
                        
                except Exception as e:
                    error_count += 1
                    self.log(f"✗ Eroare: {e}", "ERROR")
            
            # CREARE CSV
            csv_filename = None
            csv_path = None
            if products_data:
                self.log("\n" + "=" * 70, "INFO")
                self.log("📝 CREARE FIȘIER CSV...", "INFO")
                self.log("=" * 70, "INFO")
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_filename = f"export_produse_{timestamp}.csv"
                csv_path = self.export_to_csv(products_data, csv_filename)
                
                if csv_path:
                    self.log(f"\n✅ CSV creat: {csv_path}", "SUCCESS")
            
            # Sumar final
            self.log("\n" + "=" * 70, "INFO")
            self.log(f"📊 SUMAR PROCESARE:", "INFO")
            self.log(f"   ✓ Produse procesate cu succes: {success_count}", "SUCCESS")
            self.log(f"   ✗ Erori scraping: {error_count}", "ERROR")
            self.log(f"   📦 Total SKU-uri: {len(skus)}", "INFO")
            self.log(f"   📁 Imagini salvate în: images/", "INFO")
            self.log("=" * 70, "INFO")
            
            csv_info = f"\nFișier CSV: {csv_filename}" if csv_filename else ""
            messagebox.showinfo("Finalizat", 
                f"Procesare finalizată!\n\nProduse procesate: {success_count}\nErori: {error_count}{csv_info}\nFolderul imagini: images/")
            
            # Deschide folderul data cu CSV-ul
            if csv_path:
                os.startfile(Path("data"))
            
        except Exception as e:
            self.log(f"✗ Eroare critică: {e}", "ERROR")
            messagebox.showerror("Eroare", f"Eroare critică:\n{e}")
            
        finally:
            self.progress_bar.stop()
            self.btn_start.config(state='normal')
            self.btn_stop.config(state='disabled')
            self.progress_var.set("Export finalizat")
            self.running = False
    
    def read_sku_file(self, filepath):
        """Citește link-uri, EAN-uri sau SKU-uri din fișier
        Acceptă:
        - URL direct: https://www.mobilesentrix.eu/...
        - SKU: 107182127516 (12-13 cifre)
        - EAN: 888888888888 (12-13 cifre - mai rar)
        """
        items = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    items.append(line)
        return items

    def load_category_rules(self, filepath="category_rules.txt"):
        """Încarcă reguli de categorii (keyword | categorie) din fișier configurabil."""
        rules = []
        path = Path(filepath)
        if not path.exists():
            return rules
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('|')
                if len(parts) >= 2:
                    keyword = parts[0].strip().lower()
                    category_path = parts[1].strip()
                    if keyword and category_path:
                        rules.append((keyword, category_path))
        return rules

    def detect_category(self, product_name, tags):
        """Returnează categoria pe baza keyword-urilor din nume + tag-uri."""
        haystack = f"{product_name} {' '.join(tags)}".lower()
        for keyword, category_path in self.category_rules:
            if keyword in haystack:
                return category_path
        return "Uncategorized"
    
    def detect_warranty(self, product_name, category):
        """Detectează perioada de garanție pe baza categoriei și numelui produsului"""
        text = f"{product_name} {category}".lower()
        
        # 12 luni - Display/LCD
        if any(x in text for x in ['display', 'lcd', 'ecran', 'screen']):
            return "12 luni"
        
        # 6 luni - Acumulatori/Baterii
        if any(x in text for x in ['acumulator', 'baterie', 'battery', 'baterija']):
            return "6 luni"
        
        # 6 luni - Cabluri Flex
        if any(x in text for x in ['cablu', 'flex', 'cable', 'ribbon']):
            return "6 luni"
        
        # 3 luni - Carcase
        if any(x in text for x in ['carcasa', 'casing', 'housing', 'case back']):
            return "3 luni"
        
        # 1-3 luni - Accesorii (default)
        if any(x in text for x in ['accesoriu', 'accessory', 'protector', 'folie']):
            return "1-3 luni"
        
        # Default pentru alte categorii
        return "12 luni"
    
    def build_longtail_title(self, product_name, description=""):
        """Construiește titlu Long Tail SEO optimizat: [Piesa] [Model] [Calitate] [Culoare]"""
        # Extrage componentele titlului
        import re
        
        # 1. NUME PIESA - cauta în titlu
        piece_names = {
            'display': ['display', 'lcd', 'ecran', 'screen', 'amoled', 'oled'],
            'baterie': ['baterie', 'battery', 'acumulator', 'baterija'],
            'carcasa': ['carcasa', 'casing', 'housing', 'case', 'back'],
            'cablu': ['cablu', 'cable', 'flex', 'ribbon'],
            'incarcator': ['incarcator', 'charger', 'power'],
            'difuzor': ['difuzor', 'speaker', 'audio'],
            'buton': ['buton', 'button', 'key'],
            'folie': ['folie', 'folie', 'protektor', 'tempered'],
        }
        
        piece_name = 'Piesa'
        text_lower = f"{product_name} {description}".lower()
        for piece, keywords in piece_names.items():
            if any(kw in text_lower for kw in keywords):
                piece_name = piece.capitalize()
                break
        
        # 2. MODEL TELEFON - extrage din titlu
        phone_models = [
            'iPhone 17', 'iPhone 16', 'iPhone 15', 'iPhone 14', 'iPhone 13', 'iPhone 12', 'iPhone 11',
            'Samsung Galaxy S24', 'Samsung Galaxy S23', 'Samsung Galaxy S22', 'Samsung Galaxy S21', 'Samsung Galaxy A54',
            'Google Pixel 8', 'Google Pixel 7', 'Google Pixel 6',
            'OnePlus 12', 'OnePlus 11',
            'Xiaomi 14', 'Xiaomi 13',
            'Huawei P60', 'Huawei P50'
        ]
        
        phone_model = 'Telefon'
        for model in phone_models:
            if model.lower() in text_lower:
                phone_model = model
                break
        
        # 3. CALITATE - extrage din titlu
        quality_map = {
            'original': ['original', 'oem', 'genuin'],
            'premium': ['premium', 'high quality', 'de calitate'],
            'compatible': ['compatible', 'compatibil', 'aftermarket'],
            'standard': []
        }
        
        quality = 'Standard'
        for qual, keywords in quality_map.items():
            if keywords and any(kw in text_lower for kw in keywords):
                quality = qual.capitalize()
                break
        
        # 4. CULOARE - cauta în titlu
        color_map = {
            'Negru': ['negru', 'black', 'noir'],
            'Alb': ['alb', 'white', 'blanc'],
            'Gri': ['gri', 'gray', 'grey'],
            'Argintiu': ['argintiu', 'silver', 'argent'],
            'Auriu': ['auriu', 'gold', 'or'],
            'Albastru': ['albastru', 'blue', 'bleu'],
            'Rosu': ['rosu', 'red', 'rouge'],
            'Verde': ['verde', 'green', 'vert'],
            'Roz': ['roz', 'pink', 'rose'],
        }
        
        color = 'Standard'
        for col, keywords in color_map.items():
            if any(kw in text_lower for kw in keywords):
                color = col
                break
        
        # Construiește titlu Long Tail
        longtail = f"{piece_name} {phone_model} {quality} {color}"
        
        return longtail
        """Elimina diacriticele din text (ă→a, ț→t, ș→s, î→i, etc.)"""
        import unicodedata
        if not text:
            return text
        
        # Normalizează textul și separă caracterele de diacritice
        nfkd_form = unicodedata.normalize('NFKD', text)
        return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])
    
    def translate_text(self, text, source='en', target='ro'):
        """Traduce text folosind Google Translate (fara diacritice pentru romana)."""
        if not text or not text.strip():
            return text
        
        try:
            translator = GoogleTranslator(source=source, target=target)
            # Împarte text în bucăți dacă e prea lung (max 5000 caractere)
            max_length = 4500
            if len(text) <= max_length:
                translated = translator.translate(text)
            else:
                # Împarte în paragrafe și traduce separat
                chunks = []
                current_chunk = ""
                
                for paragraph in text.split('\n'):
                    if len(current_chunk) + len(paragraph) + 1 <= max_length:
                        current_chunk += paragraph + '\n'
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = paragraph + '\n'
                
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Traduce fiecare bucată
                translated_chunks = []
                for chunk in chunks:
                    translated_chunks.append(translator.translate(chunk))
                
                translated = '\n'.join(translated_chunks)
            
            # Elimina diacriticele dacă traducem în română
            if target == 'ro':
                translated = self.remove_diacritics(translated)
            
            return translated
        
        except Exception as e:
            self.log(f"⚠ Eroare traducere: {e}", "WARNING")
            return text  # Returnează textul original dacă traducerea eșuează
    
    def export_to_csv(self, products_data, filename="export_produse.csv"):
        """Exportă produsele în CSV cu toate informațiile inclusiv pozele uploadate pe WordPress"""
        import csv
        
        try:
            csv_path = Path("data") / filename
            self.log(f"📄 Creez fișier CSV: {csv_path}", "INFO")
            self.log(f"⏳ Procesez {len(products_data)} produse cu upload imagini pe WordPress...", "INFO")
            
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['ID', 'Type', 'SKU', 'EAN', 'Name', 'Published', 'Is featured?', 'Visibility in catalog',
                             'Short description', 'Description', 'Tax status', 'Tax class', 'In stock?', 'Stock',
                             'Regular price', 'Categories', 'Tags', 'Images', 'Parent', 'meta:_warranty_period']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                
                for idx, product in enumerate(products_data, 1):
                    self.log(f"🔄 Proceseaza produs {idx}/{len(products_data)}: {product.get('name', 'N/A')}", "INFO")
                    
                    # Colectează URL-urile imaginilor cu upload pe WordPress
                    image_urls = []
                    if product.get('images'):
                        for img_idx, img in enumerate(product['images']):
                            img_path = None
                            
                            if isinstance(img, dict):
                                # Preferă local_path (deja descărcat) pentru upload
                                if 'local_path' in img:
                                    img_path = img['local_path']
                            else:
                                # E string direct (local path)
                                img_path = str(img)
                            
                            if img_path and Path(img_path).exists():
                                # UPLOAD imaginea pe WordPress
                                self.log(f"   📤 Upload imagine {img_idx + 1}/{len(product['images'])}: {Path(img_path).name}", "INFO")
                                upload_result = self.upload_image_to_wordpress(img_path)
                                
                                if upload_result:
                                    # upload_result este dict cu {'id', 'src', 'name'}
                                    wp_url = upload_result.get('src') if isinstance(upload_result, dict) else upload_result
                                    image_urls.append(wp_url)
                                    self.log(f"   ✓ Imagine uploadată pe WordPress: {wp_url}", "SUCCESS")
                                else:
                                    # Fallback: foloseşte URL original de pe MobileSentrix
                                    if isinstance(img, dict) and 'src' in img:
                                        image_urls.append(img['src'])
                                        self.log(f"   ⚠ Upload eșuat, folosesc URL original", "WARNING")
                            elif isinstance(img, dict) and 'src' in img:
                                # Nu avem local path, folosim URL original MobileSentrix
                                image_urls.append(img['src'])
                    
                    # Calculează preț RON
                    price_ron = product['price']
                    if self.convert_price_var.get():
                        exchange_rate = float(self.exchange_rate_var.get())
                        price_ron = product['price'] * exchange_rate
                    
                    # Curăță numele (elimină " Copy" de la sfârșit)
                    clean_name = product.get('name', 'N/A')
                    if clean_name.endswith(' Copy'):
                        clean_name = clean_name[:-5]  # Elimină ultimele 5 caractere (" Copy")
                    
                    # Traduce numele în română
                    clean_name_ro = self.translate_text(clean_name, source='en', target='ro')
                    self.log(f"   🌍 Titlu tradus: {clean_name} → {clean_name_ro}", "INFO")
                    
                    # Construiește titlu Long Tail SEO optimizat
                    description_for_longtail = product.get('description', '')
                    longtail_title = self.build_longtail_title(clean_name_ro, description_for_longtail)
                    self.log(f"   📝 Titlu Long Tail: {longtail_title}", "INFO")
                    
                    # Curăță descrierea (elimină URL-uri)
                    clean_desc = product.get('description', '')[:500]
                    import re
                    clean_desc = re.sub(r'https?://\S+', '', clean_desc).strip()  # Elimină toate URL-urile
                    
                    # Traduce descrierea în română
                    clean_desc_ro = self.translate_text(clean_desc, source='en', target='ro')
                    self.log(f"   🌍 Descriere tradusă: {len(clean_desc)} → {len(clean_desc_ro)} caractere", "INFO")
                    
                    # EAN: folosește supplier_sku (SKU furnizor 107182127516)
                    ean_value = product.get('supplier_sku', '') or product.get('sku', '')
                    
                    # SKU: folosește SKU-ul generat WEBGSM
                    sku_value = product.get('sku_generated', product.get('sku', 'N/A'))
                    
                    # Detectează garantia pe baza categoriei și numelui
                    warranty = self.detect_warranty(clean_name_ro, product.get('category_path', ''))
                    self.log(f"   ⏱️ Garantie detectată: {warranty}", "INFO")
                    
                    # Combină toate imaginile în format WooCommerce (separare cu virgulă)
                    all_images = ', '.join(image_urls) if image_urls else ''
                    
                    row = {
                        'ID': '',  # Gol pentru produse noi
                        'Type': 'simple',  # Tip produs: simple
                        'SKU': sku_value,  # SKU generat (doar cifre pentru cod de bare)
                        'EAN': ean_value,  # EAN/UPC (SKU furnizor 107182127516)
                        'Name': longtail_title,  # Titlu Long Tail SEO optimizat
                        'Published': '1',  # Publicat automat
                        'Is featured?': '0',  # Nu e featured
                        'Visibility in catalog': 'visible',  # Vizibil în catalog
                        'Short description': clean_desc_ro[:160],  # Descriere scurtă (max 160 char)
                        'Description': clean_desc_ro,  # Descriere completă tradusă în română
                        'Tax status': 'taxable',  # Taxabil
                        'Tax class': '',  # Clasă TVA standard
                        'In stock?': '1',  # În stoc
                        'Stock': product.get('stock', '100'),  # Stock default 100
                        'Regular price': f"{price_ron:.2f}",  # Preț în RON
                        'Categories': product.get('category_path', ''),  # WooCommerce: Parent > Child
                        'Tags': product.get('tags', ''),  # Tags
                        'Images': all_images,  # Toate imaginile separate prin virgulă
                        'Parent': '',  # Gol pentru produse simple
                        'meta:_warranty_period': warranty  # Meta data: perioada de garantie
                    }
                    writer.writerow(row)
            
            self.log(f"✓ CSV creat cu succes: {csv_path}", "SUCCESS")
            self.log(f"   📊 Total produse exportate: {len(products_data)}", "INFO")
            return str(csv_path)
            
        except Exception as e:
            self.log(f"✗ Eroare creare CSV: {e}", "ERROR")
            import traceback
            self.log(f"   Traceback: {traceback.format_exc()}", "ERROR")
            return None
    
    def scrape_product(self, ean):
        """Extrage date produs de pe MobileSentrix și descarcă imagini local
        Acceptă: EAN, SKU sau LINK DIRECT la produs"""
        try:
            import re  # ⬅️ IMPORTANT: Import la ÎNCEPUTUL funcției!
            
            product_link = None
            product_id = ean  # Va fi folosit pentru nume fișiere
            
            # Headers pentru toate request-urile
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ro-RO,ro;q=0.9,en;q=0.8',
                'Referer': 'https://www.mobilesentrix.eu/'
            }
            
            # PASUL 1: Detectează dacă input-ul e link direct
            if ean.startswith('http://') or ean.startswith('https://'):
                # E link direct! 🎯
                product_link = ean
                # Extrage un ID simplu din URL pentru nume fișiere (ultimul segment URL)
                product_id = ean.rstrip('/').split('/')[-1][:50]  # Max 50 caractere
                # Curăță caracterele invalide pentru Windows filenames
                product_id = re.sub(r'[<>:"/\\|?*]', '_', product_id)
                self.log(f"   ✓ Link direct detectat!", "INFO")
                self.log(f"      URL: {product_link[:80]}...", "INFO")
                self.log(f"      ID produs: {product_id}", "INFO")
                
                # ⬇️ IMPORTANT: Descarcă pagina produsului!
                self.log(f"   🔄 Se descarcă pagina produsului...", "INFO")
                response = requests.get(product_link, headers=headers, timeout=30)
                response.raise_for_status()
                product_soup = BeautifulSoup(response.content, 'html.parser')
            # PASUL 1b: Detectează dacă e SKU (12-13 cifre consecutive)
            elif re.match(r'^\d{10,14}$', ean.strip()):
                # E SKU/EAN - MobileSentrix acceptă SKU în URL direct!
                # Caută produsul pe baza SKU în pagina de căutare
                search_sku = ean.strip()
                search_url = f"https://www.mobilesentrix.eu/catalogsearch/result/?q={search_sku}"
                self.log(f"   🔍 Căutare produs cu SKU: {search_sku}", "INFO")
                
                response = requests.get(search_url, headers=headers, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # ===== DEBUG: Salvează HTML pentru inspecție =====
                debug_file = Path("logs") / f"debug_search_{search_sku}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(soup.prettify())
                self.log(f"   📝 HTML căutare salvat: {debug_file}", "INFO")
                
                # Găsește primul produs valid din rezultate
                product_links = soup.select('a.product-item-link')
                
                if not product_links:
                    self.log(f"   ✗ Nu am găsit produse pentru SKU {search_sku}", "ERROR")
                    return None
                
                # Folosește primul link
                product_link = product_links[0].get('href')
                product_id = search_sku  # Folosim SKU-ul ca ID pentru fișiere
                
                if not product_link:
                    self.log(f"   ✗ Link produs invalid", "ERROR")
                    return None
                
                self.log(f"   ✓ Produs găsit! Link: {product_link[:80]}...", "INFO")
                
                # ⬇️ IMPORTANT: Descarcă pagina produsului!
                self.log(f"   🔄 Se descarcă pagina produsului...", "INFO")
                response = requests.get(product_link, headers=headers, timeout=30)
                response.raise_for_status()
                product_soup = BeautifulSoup(response.content, 'html.parser')
            else:
                # E text generic EAN/SKU - trebuie să căutam
                
                response = requests.get(search_url, headers=headers, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # ===== DEBUG: Salvează HTML pentru inspecție =====
                debug_file = Path("logs") / f"debug_search_{ean}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(soup.prettify())
                self.log(f"   📝 HTML salvat în: {debug_file}", "INFO")
                
                # Căuta orice link-uri de produs
                all_product_links = []
                
                # Căută cu selectorii specifici pentru produse
                product_selectors = [
                    'a.product-item-link',
                    'a.product.photo',
                    'a[data-product-id]',
                    'a[href*="/product/"]',
                    'a[href*="/catalogsearch/result/"]'
                ]
                
                for selector in product_selectors:
                    found = soup.select(selector)
                    if found:
                        self.log(f"   Selector '{selector}' a găsit {len(found)} link-uri", "INFO")
                        all_product_links.extend(found)
                
                # Elimină duplicatele și filtrează
                unique_links = []
                seen_hrefs = set()
                for link in all_product_links:
                    href = link.get('href', '')
                    if href and href not in seen_hrefs and 'mobilesentrix.eu' in href:
                        seen_hrefs.add(href)
                        unique_links.append(link)
                
                self.log(f"   🔎 Total link-uri găsite: {len(unique_links)}", "INFO")
                
                if not unique_links:
                    # ❌ NU am găsit nimic
                    self.log(f"   ⚠️ NU AM GĂSIT PRODUSUL cu EAN/SKU {ean} pe MobileSentrix!", "WARNING")
                    self.log(f"   💡 SOLUȚII:", "INFO")
                    self.log(f"      1. Copiază LINK DIRECT din MobileSentrix", "INFO")
                    self.log(f"      2. Pune link-ul în sku_list.txt (în loc de EAN)", "INFO")
                    self.log(f"      3. Programul va extrage datele direct!", "INFO")
                    return None
                
                # Folosește primul link valid
                product_link = unique_links[0]['href']
                self.log(f"   ✓ Link produs găsit: {product_link}", "INFO")
                
                # ⬇️ IMPORTANT: Descarcă pagina produsului!
                self.log(f"   🔄 Se descarcă pagina produsului...", "INFO")
                response = requests.get(product_link, headers=headers, timeout=30)
                response.raise_for_status()
                product_soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extrage ID produs intern (230473) - unic pe MobileSentrix
            product_id_internal = None
            # Caută în variabila JavaScript: var magicToolboxProductId = 230473;
            script_content = str(product_soup)
            id_match = re.search(r'var\s+magicToolboxProductId\s*=\s*(\d+)', script_content)
            if id_match:
                product_id_internal = id_match.group(1)
                self.log(f"   ✓ ID produs intern găsit: {product_id_internal}", "INFO")
            
            # Căută și în atribut data-product-id
            if not product_id_internal:
                id_elem = product_soup.select_one('[data-product-id], input[name="product"][value]')
                if id_elem:
                    product_id_internal = id_elem.get('value') or id_elem.get('data-product-id')
                    if product_id_internal:
                        self.log(f"   ✓ ID produs din atribut: {product_id_internal}", "INFO")
            
            # Salvează HTML pentru SKU extraction din JavaScript
            product_page_html = str(product_soup)
            
            # ===== DEBUG: Salvează HTML produsului =====
            debug_product_file = Path("logs") / f"debug_product_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(debug_product_file, 'w', encoding='utf-8') as f:
                f.write(product_soup.prettify())
            self.log(f"   📝 HTML produs salvat: {debug_product_file}", "INFO")
            
            # Extrage nume produs - MULTIPLI SELECTORII
            product_name = None
            name_selectors = [
                '.page-title span',
                'h1.page-title',
                'h1[itemprop="name"]',
                '.product-name',
                'h1',
                '.product-info-main h1'
            ]
            
            for selector in name_selectors:
                name_elem = product_soup.select_one(selector)
                if name_elem:
                    product_name = name_elem.text.strip()
                    self.log(f"   ✓ Nume găsit cu: {selector}", "INFO")
                    break
            
            if not product_name:
                product_name = f"Produs {ean}"
                self.log(f"   ⚠️ NU am găsit nume produs - folosesc placeholder", "WARNING")
            
            # Curăță numele de text garbage și caractere nevalide
            import re
            # Elimină "Copy", "EAN:", și alte text nevrut
            product_name = re.sub(r'\s*\bCopy\b\s*', '', product_name)
            product_name = re.sub(r'\s*\bEAN:.*', '', product_name)
            product_name = re.sub(r'\s*\bSKU:.*', '', product_name)
            product_name = re.sub(r'\s+', ' ', product_name)  # Normalizează spații multiple
            product_name = product_name.strip()
            
            # Extrage preț (EUR) - MULTIPLI SELECTORII
            price = 0.0
            price_selectors = [
                '.price-wrapper .price',
                '.product-info-price .price',
                'span[data-price-type="finalPrice"]',
                '.price-box .price',
                '.product-price .price',
                'span.price',
                '[itemprop="price"]'
            ]
            
            for selector in price_selectors:
                price_elem = product_soup.select_one(selector)
                if price_elem:
                    price_text = price_elem.text.strip()
                    # Extrage doar numerele și convertește la float
                    import re
                    price_match = re.search(r'[\d,\.]+', price_text.replace(',', '.'))
                    if price_match:
                        price = float(price_match.group(0))
                        self.log(f"   ✓ Preț găsit cu: {selector}", "INFO")
                        break
            
            if price == 0.0:
                self.log(f"   ⚠️ NU am găsit preț - folosesc 0.00", "WARNING")
            
            self.log(f"   📦 Nume: {product_name}", "INFO")
            self.log(f"   💶 Preț: {price:.2f} EUR", "INFO")
            
            # Extrage descriere
            description = ""
            desc_selectors = [
                '.product.attribute.description .value',
                '.product-description',
                '[itemprop="description"]',
                '.product-info-description'
            ]
            
            for desc_sel in desc_selectors:
                desc_elem = product_soup.select_one(desc_sel)
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                    if description:
                        break
            
            # Curăță descrierea de text garbage
            import re
            # Elimină liniile cu "Copy", "EAN", "SKU", "Share" și alte gunoaie
            lines = description.split('\n')
            clean_lines = []
            for line in lines:
                line = line.strip()
                # Sări linii care conțin cuvinte de ignorat
                if any(skip in line for skip in ['Copy', 'Share', 'Email', 'WhatsApp', 'FAQ', 'Contact', 'EAN:', 'SKU:', 'Add to']):
                    continue
                # Sări linii prea scurte (probably UI text)
                if len(line) < 3:
                    continue
                clean_lines.append(line)
            
            description = ' '.join(clean_lines)[:1000]  # Max 1000 caractere
            
            # Elimină URL-uri și alte caractere speciale
            description = re.sub(r'https?://\S+', '', description).strip()
            description = re.sub(r'\s+', ' ', description)  # Normalizează whitespace
            
            if not description:
                description = f"Produs {product_name}"
            
            # Extrage imagini
            images_data = []
            
            if self.download_images_var.get():
                self.log(f"   🖼️ Descarc imagini MARI...", "INFO")
                
                # 🎯 CAUTĂ IMAGINILE ÎN META TAGS + GALERIE COMPLETĂ
                img_urls = set()
                
                # 1. Meta tags Open Graph (imaginea principală)
                og_images = product_soup.find_all('meta', property='og:image')
                for og_img in og_images:
                    if og_img.get('content'):
                        img_urls.add(og_img['content'])
                        self.log(f"      ✓ Găsită imagine în og:image", "INFO")
                
                # 2. JSON-LD structured data (poate conține array de imagini)
                json_ld_scripts = product_soup.find_all('script', type='application/ld+json')
                for script in json_ld_scripts:
                    try:
                        import json
                        data = json.loads(script.string)
                        if isinstance(data, dict) and 'image' in data:
                            images = data['image']
                            if isinstance(images, str):
                                img_urls.add(images)
                            elif isinstance(images, list):
                                for img in images:
                                    if isinstance(img, str):
                                        img_urls.add(img)
                                    elif isinstance(img, dict) and 'url' in img:
                                        img_urls.add(img['url'])
                                self.log(f"      ✓ Găsite {len(images) if isinstance(images, list) else 1} imagini în JSON-LD", "INFO")
                    except:
                        pass
                
                # 3. 🔥 GALERIA MAGICZOOM - aici sunt TOATE imaginile!
                magic_zoom_links = product_soup.find_all('a', {'data-zoom-id': True})
                for link in magic_zoom_links:
                    href = link.get('href')
                    if href and '/catalog/product/' in href:
                        img_urls.add(href)
                self.log(f"      ✓ Găsite {len(magic_zoom_links)} imagini în galeria MagicZoom", "INFO")
                
                # 4. Link-uri cu atribut data-image (thumbnail gallery)
                data_image_links = product_soup.find_all('a', {'data-image': True})
                for link in data_image_links:
                    href = link.get('href')
                    if href and '/catalog/product/' in href:
                        img_urls.add(href)
                
                # 5. Fallback: caută imagini în elemente img standard
                img_selectors = [
                    '.product-image-photo',
                    'img[data-role="image"]',
                    '.product-photo img',
                    '.gallery-placeholder img'
                ]
                for selector in img_selectors:
                    for img_elem in product_soup.select(selector):
                        src = img_elem.get('src') or img_elem.get('data-src')
                        if src and 'catalog/product' in src:
                            img_urls.add(src)
                
                if not img_urls:
                    self.log(f"   ⚠️ Nu am găsit imagini pe pagina produsului", "WARNING")
                else:
                    self.log(f"   🔍 Total imagini găsite: {len(img_urls)}", "INFO")
                
                for idx, img_url in enumerate(list(img_urls)[:10], 1):  # Max 10 imagini
                    # Dacă URL e relativ, fă-l absolut
                    if img_url.startswith('/'):
                        img_url = 'https://www.mobilesentrix.eu' + img_url
                    elif not img_url.startswith('http'):
                        img_url = 'https://www.mobilesentrix.eu/' + img_url
                    
                    # Convertește thumbnail în imagine MARE
                    # De exemplu: /thumbnail/ -> /image/ sau /small_image/ -> /image/
                    img_url = img_url.replace('/thumbnail/', '/image/').replace('/small_image/', '/image/')
                    
                    try:
                        # Descarcă imaginea în dimensiunea MARE (originală)
                        self.log(f"      📷 [{idx}] Descarc: {img_url[:80]}...", "INFO")
                        img_response = requests.get(img_url, headers=headers, timeout=30)
                        img_response.raise_for_status()
                        
                        # Deschide imagine cu PIL
                        img = Image.open(BytesIO(img_response.content))
                        
                        # ❌ NU optimizezi - salvează original MARE
                        # (comentat codul de resize)
                        # if self.optimize_images_var.get():
                        #     max_size = (1200, 1200)
                        #     img.thumbnail(max_size, Image.Resampling.LANCZOS)
                        
                        # Generează nume fișier unic
                        img_extension = img.format.lower() if img.format else 'jpg'
                        img_filename = f"{product_id}_{idx}.{img_extension}"
                        img_path = Path("images") / img_filename
                        
                        # Salvează imaginea local - dimensiunea ORIGINALĂ
                        img.save(img_path, quality=95)  # Max quality
                        file_size = img_path.stat().st_size / (1024 * 1024)  # Size în MB
                        self.log(f"         ✓ Salvat: {img_filename} ({file_size:.2f} MB)", "SUCCESS")
                        
                        # Adaugă în lista de imagini cu path local
                        images_data.append({
                            'src': img_url,  # URL original (pentru referință)
                            'local_path': str(img_path),  # Path local pentru CSV
                            'name': img_filename,
                            'size': f"{file_size:.2f} MB"
                        })
                        
                        # Rate limit - pauză între descărcări
                        time.sleep(0.5)
                        
                    except Exception as img_error:
                        self.log(f"         ⚠️ Eroare descarcare imagine {idx}: {img_error}", "WARNING")
                
                self.log(f"   ✓ Total imagini descarcate: {len(images_data)}", "SUCCESS")
            
            # Extrage brand din nume (de obicei primul cuvânt sau "iPhone", "Samsung" etc)
            brand = 'MobileSentrix'  # Default
            if 'iPhone' in product_name or 'Apple' in product_name:
                brand = 'Apple'
            elif 'Samsung' in product_name or 'Galaxy' in product_name:
                brand = 'Samsung'
            elif 'Google' in product_name or 'Pixel' in product_name:
                brand = 'Google'
            
            # 🎯 EXTRAGE SKU-UL REAL DE LA MOBILESENTRIX DIN JAVASCRIPT
            extracted_sku = None
            try:
                import re
                # Caută variabila ecommerce.items.item_id în JavaScript
                # Pattern: var ecommerce = {...,"item_id":"107182127516",...}
                ecommerce_pattern = r'var ecommerce\s*=\s*{[^}]*"item_id"\s*:\s*"(\d+)"'
                ecommerce_match = re.search(ecommerce_pattern, product_page_html)
                
                if ecommerce_match:
                    extracted_sku = ecommerce_match.group(1)
                    self.log(f"   ✓ SKU MobileSentrix extras din JavaScript: {extracted_sku}", "SUCCESS")
            except Exception as sku_extract_error:
                self.log(f"   ⚠️ Nu am putut extrage SKU din JavaScript: {sku_extract_error}", "WARNING")
            
            # Generează SKU din ID produsului intern sau folosește cel extras
            if extracted_sku:
                # Dacă am extras SKU-ul de la MobileSentrix, îl folosim direct!
                generated_sku = extracted_sku
                self.log(f"   ✓ SKU folosit: {generated_sku} (de la MobileSentrix)", "INFO")
            elif product_id_internal:
                # Fallback: SKU generat din ID intern - DOAR CIFRE
                generated_sku = product_id_internal
                self.log(f"   ✓ SKU generat din ID produs: {generated_sku}", "INFO")
            else:
                # Fallback: din URL slug - DOAR CIFRE
                import re
                import time
                # Extrage doar numerele din URL, dacă nu găsește nimic, folosește timestamp
                sku_base = re.sub(r'[^0-9]', '', product_id[:20])
                if not sku_base:
                    # Dacă nu am găsit cifre în URL, generez din timestamp
                    sku_base = str(int(time.time()))[-8:]
                generated_sku = sku_base
                self.log(f"   ✓ SKU generat din URL: {generated_sku}", "INFO")
            
            # Tag-uri din categorii (extrage din nume și descriere)
            tags = []
            
            # Informații din titlu
            product_name_lower = product_name.lower()
            
            # Brand
            if 'apple' in product_name_lower:
                tags.append('Apple')
            if 'samsung' in product_name_lower:
                tags.append('Samsung')
            if 'motorola' in product_name_lower:
                tags.append('Motorola')
            if 'google' in product_name_lower or 'pixel' in product_name_lower:
                tags.append('Google Pixel')
            if 'oneplus' in product_name_lower:
                tags.append('OnePlus')
            if 'xiaomi' in product_name_lower:
                tags.append('Xiaomi')
            if 'huawei' in product_name_lower:
                tags.append('Huawei')
            
            # Tip dispozitiv
            if 'iphone' in product_name_lower:
                tags.append('iPhone')
            if 'ipad' in product_name_lower:
                tags.append('iPad')
            if 'watch' in product_name_lower or 'apple watch' in product_name_lower:
                tags.append('Apple Watch')
            if 'macbook' in product_name_lower:
                tags.append('MacBook')
            if 'galaxy' in product_name_lower:
                tags.append('Samsung Galaxy')
            
            # Model specific
            if 'pro max' in product_name_lower:
                tags.append('Pro Max')
            if 'pro' in product_name_lower and 'pro max' not in product_name_lower:
                tags.append('Pro')
            if 'air' in product_name_lower:
                tags.append('Air')
            if 'mini' in product_name_lower:
                tags.append('Mini')
            if 'ultra' in product_name_lower:
                tags.append('Ultra')
            if 'plus' in product_name_lower:
                tags.append('Plus')
            
            # Versiuni iOS
            if 'iphone 17' in product_name_lower:
                tags.append('iPhone 17')
            if 'iphone 16' in product_name_lower:
                tags.append('iPhone 16')
            if 'iphone 15' in product_name_lower:
                tags.append('iPhone 15')
            if 'iphone 14' in product_name_lower:
                tags.append('iPhone 14')
            if 'iphone 13' in product_name_lower:
                tags.append('iPhone 13')
            
            # Specificații
            if 'oled' in product_name_lower:
                tags.append('OLED')
            if 'lcd' in product_name_lower or 'ips' in product_name_lower:
                tags.append('LCD')
            if '120hz' in product_name_lower or '120 hz' in product_name_lower:
                tags.append('120Hz')
            if '90hz' in product_name_lower or '90 hz' in product_name_lower:
                tags.append('90Hz')
            if '60hz' in product_name_lower or '60 hz' in product_name_lower:
                tags.append('60Hz')
            
            # Tip component
            if 'assembly' in product_name_lower or 'display' in product_name_lower:
                tags.append('Display Assembly')
            if 'screen' in product_name_lower:
                tags.append('Screen')
            if 'battery' in product_name_lower:
                tags.append('Battery')
            if 'charging' in product_name_lower or 'charger' in product_name_lower:
                tags.append('Charging')
            if 'port' in product_name_lower:
                tags.append('Port')
            if 'camera' in product_name_lower:
                tags.append('Camera')
            if 'speaker' in product_name_lower:
                tags.append('Speaker')
            if 'microphone' in product_name_lower:
                tags.append('Microphone')
            if 'button' in product_name_lower:
                tags.append('Button')
            if 'cable' in product_name_lower:
                tags.append('Cable')
            if 'adapter' in product_name_lower:
                tags.append('Adapter')
            if 'glass' in product_name_lower:
                tags.append('Glass')
            
            # Calitate
            if 'genuine' in product_name_lower or 'oem' in product_name_lower:
                tags.append('Genuine OEM')
            if 'aftermarket' in product_name_lower:
                tags.append('Aftermarket')
            if 'compatible' in product_name_lower:
                tags.append('Compatible')
            if 'replacement' in product_name_lower:
                tags.append('Replacement')
            if 'original' in product_name_lower:
                tags.append('Original')
            if 'premium' in product_name_lower:
                tags.append('Premium')
            if 'quality' in product_name_lower:
                tags.append('Quality')
            
            # Elimină duplicatele și ordonează alfabetic
            tags = list(dict.fromkeys(tags))  # Elimină duplicatele păstrând ordinea
            tags = sorted(set(tags))  # Apoi sortează alfabetic și elimină orice duplicat rămas
            
            category_path = self.detect_category(product_name, tags)
            
            product_data = {
                'ean': ean if not ean.startswith('http') else product_link,  # Pentru logging
                'ean_real': '',  # MobileSentrix NU expune EAN public
                'sku': generated_sku,  # SKU generat din ID intern
                'name': product_name,
                'price': price,
                'description': description,
                'stock': '100',  # Stock default
                'brand': brand,
                'tags': ', '.join(tags),
                'category_path': category_path,
                'images': images_data
            }
            
            self.log(f"   ✓ Date extrase cu succes!", "SUCCESS")
            
            return product_data
            
        except requests.exceptions.RequestException as req_error:
            self.log(f"   ✗ Eroare conexiune: {req_error}", "ERROR")
            return None
        except Exception as e:
            self.log(f"   ✗ Eroare scraping: {e}", "ERROR")
            import traceback
            self.log(f"   📝 Traceback: {traceback.format_exc()}", "ERROR")
            return None
    
    def cleanup_phantom_from_mysql(self, product_id):
        """Șterge phantom product direct din MySQL (dacă API nu funcționează)"""
        try:
            # Extrage credentialele MySQL din .env sau config
            db_host = os.getenv('DB_HOST', 'localhost')
            db_user = os.getenv('DB_USER', 'root')
            db_pass = os.getenv('DB_PASSWORD', '')
            db_name = os.getenv('DB_NAME', 'wordpress')
            
            # Încearcă import - MySQL nu e instalat pe client deci NU merge
            # Alternativă: Șterge prin WordPress CLI API
            # Pentru moment: Raportează și cere manual cleanup
            self.log(f"   ⚠️ Phantom ID {product_id} va fi șters manual din phpMyAdmin", "WARNING")
            return False
            
        except Exception as e:
            self.log(f"   ⚠️ Nu am putut șterge phantom ID {product_id}: {e}", "WARNING")
            return False

    def upload_image_to_wordpress(self, local_image_path):
        """Uploadează imagine din folder local pe server WordPress/WooCommerce"""
        try:
            local_path = Path(local_image_path)
            
            if not local_path.exists():
                self.log(f"   ⚠️ Imagine nu există: {local_image_path}", "WARNING")
                return None
            
            # Citește fișierul
            with open(local_path, 'rb') as f:
                file_data = f.read()
            
            # Headers pentru upload - WordPress media endpoint
            headers = {
                'Content-Disposition': f'attachment; filename="{local_path.name}"'
            }
            
            # Detectează MIME type
            mime_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            mime_type = mime_types.get(local_path.suffix.lower(), 'image/jpeg')
            headers['Content-Type'] = mime_type
            
            # URL media upload endpoint
            media_url = f"{self.config['WOOCOMMERCE_URL']}/wp-json/wp/v2/media"
            
            # WordPress Application Password (diferit de WooCommerce API keys!)
            wp_username = os.getenv('WP_USERNAME', 'admin')
            wp_app_password = os.getenv('WP_APP_PASSWORD', '')
            
            if not wp_app_password:
                self.log(f"         ⚠️ WP_APP_PASSWORD lipsă din .env!", "WARNING")
                return None
            
            # Încearcă upload cu Application Password
            self.log(f"      📤 Upload: {local_path.name} ({len(file_data)/1024:.1f}KB)...", "INFO")
            
            response = requests.post(
                media_url,
                data=file_data,
                headers=headers,
                auth=(wp_username, wp_app_password.replace(' ', '')),  # Remove spaces din password
                timeout=60
            )
            
            if response.status_code in [200, 201]:
                media_data = response.json()
                media_id = media_data.get('id')
                media_url_result = media_data.get('source_url')
                self.log(f"         ✓ ID={media_id}", "SUCCESS")
                return {
                    'id': media_id,
                    'src': media_url_result,
                    'name': local_path.name
                }
            else:
                error_msg = response.text[:200] if response.text else f"Status {response.status_code}"
                self.log(f"         ✗ Upload eșuat: {error_msg}", "WARNING")
                return None
                
        except Exception as e:
            self.log(f"   ⚠️ Eroare upload imagine: {e}", "WARNING")
            return None


# Main
if __name__ == "__main__":
    root = tk.Tk()
    app = ImportProduse(root)
    root.mainloop()
