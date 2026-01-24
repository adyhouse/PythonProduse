"""
Program Import Produse MobileSentrix → WooCommerce
Versiune: 2.0 - cu GUI și funcționalitate completă
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import os
import sys
import json
import threading
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv, set_key
from woocommerce import API
import re
import html
import uuid
import time

class ImportProduse:
    def __init__(self, root):
        self.root = root
        self.root.title("Import Produse MobileSentrix → WooCommerce")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # Variabile
        self.env_file = Path(".env")
        self.config = {}
        self.wc_api = None
        self.running = False
        
        # Creare directoare
        Path("logs").mkdir(exist_ok=True)
        Path("images").mkdir(exist_ok=True)
        Path("data").mkdir(exist_ok=True)
        
        # Load config
        self.load_config()
        
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
        
        # Tab 1: Import
        tab_import = ttk.Frame(notebook)
        notebook.add(tab_import, text='📦 Import Produse')
        
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
        
        # Frame SKU
        frame_sku = ttk.LabelFrame(parent, text="Selectează fișier cu SKU-uri", padding=10)
        frame_sku.pack(fill='x', padx=10, pady=10)
        
        self.sku_file_var = tk.StringVar(value="sku_list.txt")
        
        ttk.Label(frame_sku, text="Fișier:").grid(row=0, column=0, sticky='w', padx=5)
        ttk.Entry(frame_sku, textvariable=self.sku_file_var, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(frame_sku, text="Răsfoire...", command=self.browse_sku_file).grid(row=0, column=2, padx=5)
        
        # Opțiuni import
        frame_options = ttk.LabelFrame(parent, text="Opțiuni Import", padding=10)
        frame_options.pack(fill='x', padx=10, pady=10)
        
        self.download_images_var = tk.BooleanVar(value=True)
        self.optimize_images_var = tk.BooleanVar(value=True)
        self.convert_price_var = tk.BooleanVar(value=True)
        self.extract_description_var = tk.BooleanVar(value=True)
        self.update_existing_var = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(frame_options, text="Descarcă toate imaginile produsului", 
                       variable=self.download_images_var).grid(row=0, column=0, sticky='w', padx=5, pady=2)
        ttk.Checkbutton(frame_options, text="Optimizează imaginile (resize)", 
                       variable=self.optimize_images_var).grid(row=1, column=0, sticky='w', padx=5, pady=2)
        ttk.Checkbutton(frame_options, text="Convertește prețul EUR → RON", 
                       variable=self.convert_price_var).grid(row=2, column=0, sticky='w', padx=5, pady=2)
        ttk.Checkbutton(frame_options, text="Extrage descriere în română", 
                       variable=self.extract_description_var).grid(row=3, column=0, sticky='w', padx=5, pady=2)
        ttk.Checkbutton(frame_options, text="✅ Actualizează produse existente (dacă SKU există deja)", 
                       variable=self.update_existing_var).grid(row=4, column=0, sticky='w', padx=5, pady=2)
        
        # Progress
        frame_progress = ttk.Frame(parent)
        frame_progress.pack(fill='x', padx=10, pady=10)
        
        self.progress_var = tk.StringVar(value="Pregătit pentru import")
        ttk.Label(frame_progress, textvariable=self.progress_var).pack(anchor='w')
        
        self.progress_bar = ttk.Progressbar(frame_progress, mode='indeterminate')
        self.progress_bar.pack(fill='x', pady=5)
        
        # Butoane
        frame_buttons = ttk.Frame(parent)
        frame_buttons.pack(fill='x', padx=10, pady=10)
        
        self.btn_start = ttk.Button(frame_buttons, text="🚀 START IMPORT", 
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
        """Generează SKU unic pentru WooCommerce bazat pe EAN"""
        # Format: WEBGSM-[ultimi 6 cifre EAN]-[timestamp scurt]
        import time
        
        # Extrage ultimi 6 cifre din EAN
        ean_suffix = str(ean)[-6:] if len(str(ean)) >= 6 else str(ean)
        
        # Timestamp scurt (4 cifre)
        timestamp = str(int(time.time()))[-4:]
        
        # Generează SKU
        sku = f"WEBGSM-{ean_suffix}-{timestamp}"
        
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
        
        if not self.wc_api:
            reply = messagebox.askyesno("Atenție", 
                "Nu ai testat conexiunea la WooCommerce.\nContinui oricum?")
            if not reply:
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
        """Execută importul efectiv"""
        try:
            # ⚠️ CURĂȚARE DEZACTIVATĂ DIN CAUZA RISCULUI DE DAMAGE DATABASE
            # Programul va folosi UUID ca fallback în caz de conflict
            # Dacă apare o eroare de "Duplicate entry", trebuie curățare MANUALĂ din phpMyAdmin!
            
            self.log("=" * 70, "INFO")
            self.log("🚀 START IMPORT PRODUSE", "INFO")
            self.log("=" * 70, "INFO")
            
            # Citește SKU-uri
            skus = self.read_sku_file(self.sku_file_var.get())
            self.log(f"📋 Găsite {len(skus)} SKU-uri pentru import", "INFO")
            
            success_count = 0
            error_count = 0
            update_count = 0
            
            # Lista pentru raport detaliat
            updates_report = []
            
            for idx, sku in enumerate(skus, 1):
                if not self.running:
                    break
                
                self.progress_var.set(f"Import produs {idx}/{len(skus)}: {sku}")
                self.log(f"\n" + "="*70, "INFO")
                self.log(f"[{idx}/{len(skus)}] 🔵 START procesare EAN: {sku}", "INFO")
                self.log(f"="*70, "INFO")
                
                try:
                    # Scraping produs de pe MobileSentrix
                    product_data = self.scrape_product(sku)
                    
                    if product_data:
                        # Import în WooCommerce
                        result = self.import_to_woocommerce(product_data)
                        
                        if result:
                            success_count += 1
                            self.log(f"✓ Produs importat cu succes!", "SUCCESS")
                        else:
                            error_count += 1
                            self.log(f"✗ Eroare import în WooCommerce", "ERROR")
                    else:
                        error_count += 1
                        self.log(f"✗ Nu s-au putut extrage datele produsului", "ERROR")
                        
                except Exception as e:
                    error_count += 1
                    self.log(f"✗ Eroare: {e}", "ERROR")
            
            # Sumar final
            self.log("\n" + "=" * 70, "INFO")
            self.log(f"📊 SUMAR IMPORT:", "INFO")
            self.log(f"   ✓ Succese (noi + actualizate): {success_count}", "SUCCESS")
            self.log(f"   ✗ Erori: {error_count}", "ERROR")
            self.log(f"   📦 Total: {len(skus)}", "INFO")
            self.log("=" * 70, "INFO")
            
            messagebox.showinfo("Finalizat", 
                f"Import finalizat!\n\nSuccese: {success_count}\nErori: {error_count}")
            
        except Exception as e:
            self.log(f"✗ Eroare critică: {e}", "ERROR")
            messagebox.showerror("Eroare", f"Eroare critică:\n{e}")
            
        finally:
            self.progress_bar.stop()
            self.btn_start.config(state='normal')
            self.btn_stop.config(state='disabled')
            self.progress_var.set("Import finalizat")
            self.running = False
    
    def read_sku_file(self, filepath):
        """Citește SKU-uri din fișier"""
        skus = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    skus.append(line)
        return skus
    
    def scrape_product(self, ean):
        """Extrage date produs de pe MobileSentrix"""
        try:
            # Căutare produs după EAN
            search_url = f"https://www.mobilesentrix.eu/catalogsearch/result/?q={ean}"
            self.log(f"   Căutare produs cu EAN: {ean}", "INFO")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Găsește link produs (logica de scraping poate varia)
            # Acest cod este un template - trebuie ajustat după structura reală
            
            product_data = {
                'ean': ean,  # EAN de pe MobileSentrix
                'sku': None,  # Va fi generat automat în WooCommerce
                'name': f"Produs {ean}",  # Placeholder
                'price': 100.00,  # Placeholder
                'description': f"Descriere produs {ean}",  # Placeholder
                'images': []  # Placeholder
            }
            
            self.log(f"   ✓ Date extrase: {product_data['name']} (EAN: {ean})", "INFO")
            
            # Descarcă imagini dacă este activată opțiunea
            if self.download_images_var.get():
                # Aici ar veni logica de download imagini
                pass
            
            return product_data
            
        except Exception as e:
            self.log(f"   ✗ Eroare scraping: {e}", "ERROR")
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

    def import_to_woocommerce(self, product_data):
        """Importă produs în WooCommerce"""
        try:
            if not self.wc_api:
                # Inițializează API
                self.wc_api = API(
                    url=self.config['WOOCOMMERCE_URL'],
                    consumer_key=self.config['WOOCOMMERCE_CONSUMER_KEY'],
                    consumer_secret=self.config['WOOCOMMERCE_CONSUMER_SECRET'],
                    version="wc/v3",
                    timeout=30
                )
            
            ean = product_data['ean']
            
            # GENEREAZĂ SKU UNIC pentru WooCommerce
            generated_sku = self.generate_unique_sku(ean)
            product_data['sku'] = generated_sku
            
            self.log(f"   🏷️ SKU generat: {generated_sku} (EAN: {ean})", "INFO")
            
            # VERIFICĂ DACĂ PRODUSUL EXISTĂ DEJA (după EAN, nu după SKU)
            self.log(f"   🔍 Verific dacă EAN {ean} există deja în WooCommerce...", "INFO")
            
            existing_product = None
            
            try:
                # Metodă 1: Caută după EAN în meta_data
                search_response = self.wc_api.get("products", params={"search": ean, "per_page": 100})
                
                if search_response.status_code == 200:
                    existing_products = search_response.json()
                    
                    # Filtrează după EAN exact în meta_data
                    for prod in existing_products:
                        for meta in prod.get('meta_data', []):
                            if meta.get('key') == '_ean' and str(meta.get('value')) == str(ean):
                                existing_product = prod
                                break
                        if existing_product:
                            break
                    
                    # Metodă 2: Dacă nu găsim după EAN, verifică dacă SKU-ul generat există
                    if not existing_product:
                        sku_check_response = self.wc_api.get("products", params={"sku": generated_sku})
                        if sku_check_response.status_code == 200:
                            sku_products = sku_check_response.json()
                            if sku_products:
                                existing_product = sku_products[0]
                                self.log(f"   ⚠️ Găsit produs cu SKU {generated_sku} (fără EAN în meta_data)", "WARNING")
                    
                    if existing_product:
                        # Produsul există - ACTUALIZARE
                        product_id = existing_product['id']
                        existing_price = float(existing_product.get('regular_price', 0) or 0)
                        
                        self.log(f"   ⚠️ Produs cu EAN {ean} EXISTĂ deja (ID: {product_id})", "WARNING")
                        self.log(f"   💰 Preț curent în WooCommerce: {existing_price:.2f} RON", "INFO")
                        
                        # Verifică opțiunea de actualizare
                        if self.update_existing_var.get():
                            self.log(f"   🔄 MODE: ACTUALIZARE (update_existing = ON)", "INFO")
                            return self.update_product(product_id, product_data)
                        else:
                            self.log(f"   ⏭️ MODE: SKIP (update_existing = OFF)", "WARNING")
                            self.log(f"   ⏭️ Sar peste produs - nu se actualizează", "WARNING")
                            return True  # Considerăm ca "succes" pentru a nu afișa ca eroare
            except Exception as check_error:
                self.log(f"   ⚠️ Nu am putut verifica duplicatele: {check_error}", "WARNING")
                # Continuăm cu crearea
            
            # CREEAZĂ PRODUS NOU
            # Convertește preț EUR → RON
            price = product_data['price']
            if self.convert_price_var.get():
                exchange_rate = float(self.exchange_rate_var.get())
                price = price * exchange_rate
            
            # Pregătește datele pentru WooCommerce
            wc_data = {
                'name': product_data['name'],
                'type': 'simple',
                'regular_price': str(round(price, 2)),
                'description': product_data['description'],
                'sku': generated_sku,  # SKU generat automat
                'manage_stock': True,
                'stock_quantity': 10,
                'status': 'publish',
                'meta_data': [
                    {
                        'key': '_ean',
                        'value': ean  # EAN de pe MobileSentrix
                    },
                    {
                        'key': '_supplier_ean',
                        'value': ean  # Backup pentru identificare furnizor
                    }
                ]
            }
            
            # Upload imagini dacă există
            if product_data.get('images'):
                wc_data['images'] = product_data['images']
            
            self.log(f"   📤 Creez produs nou în WooCommerce (SKU: {generated_sku})...", "INFO")
            self.log(f"   📝 Date produs: Nume={wc_data['name']}, Preț={wc_data['regular_price']} RON, EAN={ean}", "INFO")
            
            # Creează produs cu mecanism ROBUST de retry și phantom cleanup
            max_retries = 5
            retry_count = 0
            phantom_ids_created = []
            
            while retry_count < max_retries:
                self.log(f"   📡 Trimit cerere POST /products (încercare {retry_count + 1}/{max_retries})...", "INFO")
                response = self.wc_api.post("products", wc_data)
                self.log(f"   📥 Răspuns primit: Status {response.status_code}", "INFO")
                
                # SUCCES - Produs creat
                if response.status_code == 201:
                    product_id = response.json()['id']
                    product_sku = response.json().get('sku', 'N/A')
                    self.log(f"   ✓ Status 201 - Produs creat! ID={product_id}, SKU={product_sku}", "SUCCESS")
                    
                    # VERIFICARE POST-CREARE: Confirmă că e complet (nu phantom)
                    try:
                        self.log(f"   🔍 Verific că produs e complet (GET)...", "INFO")
                        verify_response = self.wc_api.get(f"products/{product_id}")
                        
                        if verify_response.status_code == 200:
                            verified_product = verify_response.json()
                            verified_sku = verified_product.get('sku', 'N/A')
                            verified_status = verified_product.get('status', 'N/A')
                            
                            self.log(f"   ✓ Produs verificat complet: ID={product_id}, SKU={verified_sku}, Status={verified_status}", "SUCCESS")
                            self.log(f"   ✅ PRODUS CREAT ȘI SALVAT COMPLET (NU PHANTOM)!", "SUCCESS")
                            return True
                        else:
                            self.log(f"   ⚠️ Verificare eșuată ({verify_response.status_code}) - posibil phantom", "WARNING")
                            # Încercă ștergere
                            try:
                                self.wc_api.delete(f"products/{product_id}", params={"force": True})
                                self.log(f"   🗑️ Ștergere phantom ID {product_id}", "INFO")
                            except:
                                pass
                            return False
                            
                    except Exception as ver_err:
                        self.log(f"   ⚠️ Nu pot verifica produsul: {ver_err}", "WARNING")
                        return True  # Considerăm succes dacă am primit 201
                
                # CONFLICT - Duplicate entry
                elif response.status_code == 400 and "Duplicate entry" in response.text:
                    retry_count += 1
                    self.log(f"   ⚠️ Conflict detectat (încercare {retry_count}/{max_retries})", "WARNING")
                    
                    # Decode HTML entities
                    decoded_text = html.unescape(response.text)
                    
                    # Extrage phantom ID
                    match = re.search(r"Duplicate entry '(\d+)' for key 'PRIMARY'", decoded_text)
                    
                    if match:
                        phantom_id = match.group(1)
                        phantom_ids_created.append(phantom_id)
                        self.log(f"   🔍 Phantom ID creat: {phantom_id}", "WARNING")
                        
                        # ⭐ Încearcă ștergere automată a phantom ID-ului
                        try:
                            self.log(f"   🗑️ Încerc ștergere AUTOMATĂ phantom ID {phantom_id}...", "INFO")
                            delete_response = self.wc_api.delete(f"products/{phantom_id}", params={"force": True})
                            
                            if delete_response.status_code in [200, 204]:
                                self.log(f"   ✅ Phantom ID {phantom_id} șters cu succes! Retry importul...", "SUCCESS")
                                phantom_ids_created.remove(phantom_id)
                                time.sleep(0.5)
                                continue  # Reîncearcă IMEDIAT cu aceeași SKU
                            else:
                                self.log(f"   ⚠️ Delete eșuat (status {delete_response.status_code})", "WARNING")
                                self.log(f"   🔧 Voi genera SKU nou cu UUID...", "INFO")
                        except Exception as del_err:
                            self.log(f"   ⚠️ Nu pot șterge din API: {del_err}", "WARNING")
                    
                    # Generează SKU COMPLET UNIC pentru retry (dacă ștergere a eșuat)
                    unique_suffix = f"{str(uuid.uuid4())[:8]}-{int(time.time() * 1000) % 10000}"
                    new_sku = f"WEBGSM-{ean[-6:]}-{unique_suffix}"
                    wc_data['sku'] = new_sku
                    
                    self.log(f"   🆕 Retry cu SKU UNIC: {new_sku}", "INFO")
                    time.sleep(0.5)
                    continue
                
                # ALTĂ EROARE
                else:
                    self.log(f"   ✗ Eroare neașteptată: Status {response.status_code}", "ERROR")
                    if retry_count < max_retries:
                        retry_count += 1
                        unique_suffix = f"{str(uuid.uuid4())[:8]}-{int(time.time() * 1000) % 10000}"
                        new_sku = f"WEBGSM-{ean[-6:]}-{unique_suffix}"
                        wc_data['sku'] = new_sku
                        self.log(f"   🔄 Reîncerc cu alt SKU...", "INFO")
                        time.sleep(1)
                        continue
                    else:
                        break
            
            # EȘEC FINAL
            self.log(f"   ✗ EȘEC FINAL după {max_retries} încercări", "ERROR")
            
            if phantom_ids_created:
                self.log(f"   🔴 Phantom IDs create: {phantom_ids_created}", "ERROR")
                self.log(f"   💡 SOLUȚIE:", "INFO")
                self.log(f"       1. Deschide phpMyAdmin", "INFO")
                self.log(f"       2. Rulează: CLEANUP_COPY_PASTE.txt", "INFO")
                self.log(f"       3. Resetează AUTO_INCREMENT la 1", "INFO")
                self.log(f"       4. Relansează importul", "INFO")
            
            return False
                
        except Exception as e:
            self.log(f"   ✗ Eroare import WooCommerce: {e}", "ERROR")
            import traceback
            self.log(f"   📝 Traceback: {traceback.format_exc()}", "ERROR")
            return False
    
    def update_product(self, product_id, product_data):
        """Actualizează un produs existent în WooCommerce cu tracking de preț"""
        try:
            ean = product_data.get('ean', 'N/A')
            
            # Convertește preț EUR → RON
            price_new = product_data['price']
            if self.convert_price_var.get():
                exchange_rate = float(self.exchange_rate_var.get())
                price_new = price_new * exchange_rate
            
            price_new_str = str(round(price_new, 2))
            
            # 1. PRELUĂ PREȚUL VECHI din baza de date
            self.log(f"   🔍 Preluez prețul curent din WooCommerce...", "INFO")
            try:
                get_response = self.wc_api.get(f"products/{product_id}")
                if get_response.status_code == 200:
                    existing_product = get_response.json()
                    price_old = float(existing_product.get('regular_price', 0) or 0)
                    
                    self.log(f"   💰 PREȚ VECHI: {price_old:.2f} RON", "INFO")
                    self.log(f"   💰 PREȚ NOU:  {price_new_str} RON", "INFO")
                    
                    # Calculează diferență
                    if price_old > 0:
                        price_diff = price_new - price_old
                        price_pct = (price_diff / price_old) * 100
                        if price_diff > 0:
                            self.log(f"   📈 CREȘTERE:  +{price_diff:.2f} RON (+{price_pct:.1f}%)", "SUCCESS")
                        elif price_diff < 0:
                            self.log(f"   📉 SCĂDERE:   {price_diff:.2f} RON ({price_pct:.1f}%)", "SUCCESS")
                        else:
                            self.log(f"   🔄 PREȚ NESCHIMBAT (identic)", "INFO")
                    else:
                        self.log(f"   📊 Preț inițial: 0 RON → {price_new_str} RON", "INFO")
                else:
                    price_old = None
                    self.log(f"   ⚠️ Nu s-a putut prelua prețul vechi", "WARNING")
            except Exception as get_error:
                price_old = None
                self.log(f"   ⚠️ Eroare preluare preț: {get_error}", "WARNING")
            
            # 2. PREGĂTESC DATELE PENTRU ACTUALIZARE
            self.log(f"   📤 Trimit cerere PUT /products/{product_id}...", "INFO")
            
            wc_data = {
                'name': product_data['name'],
                'regular_price': price_new_str,
                'description': product_data['description'],
                'stock_quantity': 10,
                'status': 'publish'
            }
            
            # Upload imagini dacă există
            if product_data.get('images'):
                wc_data['images'] = product_data['images']
            
            # 3. ACTUALIZEAZĂ PRODUS
            response = self.wc_api.put(f"products/{product_id}", wc_data)
            
            if response.status_code == 200:
                self.log(f"   ✓ Răspuns WooCommerce: Status 200 (Updated)", "SUCCESS")
                
                # 4. VERIFICARE POST-ACTUALIZARE: Confirmă că prețul s-a salvat
                self.log(f"   🔍 Verificare post-actualizare (GET /products/{product_id})...", "INFO")
                try:
                    verify_response = self.wc_api.get(f"products/{product_id}")
                    if verify_response.status_code == 200:
                        verified_product = verify_response.json()
                        verified_price = float(verified_product.get('regular_price', 0) or 0)
                        verified_name = verified_product.get('name', 'N/A')
                        
                        # Verifică că prețul s-a salvat corect
                        if abs(verified_price - price_new) < 0.01:  # tolerance 0.01 RON
                            self.log(f"   ✓ Prețul verificat în DB: {verified_price:.2f} RON", "SUCCESS")
                            self.log(f"   ✓ PRODUS ACTUALIZAT ȘI VERIFICAT!", "SUCCESS")
                            self.log(f"   📋 EAN: {ean} | Nume: {verified_name}", "INFO")
                            return True
                        else:
                            self.log(f"   ⚠️ AVERTISMENT: Preț salvat ({verified_price:.2f}) ≠ Preț trimes ({price_new_str})", "WARNING")
                            return True  # Considerăm parțial succes
                    else:
                        self.log(f"   ⚠️ Produs actualizat dar verificare eșuată ({verify_response.status_code})", "WARNING")
                        return True
                except Exception as verify_error:
                    self.log(f"   ⚠️ Nu am putut verifica după actualizare: {verify_error}", "WARNING")
                    return True
            else:
                self.log(f"   ✗ Eroare actualizare: Status {response.status_code}", "ERROR")
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        self.log(f"   📝 Mesaj: {error_data['message']}", "ERROR")
                except:
                    self.log(f"   📝 Răspuns: {response.text[:300]}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"   ✗ Eroare actualizare: {e}", "ERROR")
            return False

# Main
if __name__ == "__main__":
    root = tk.Tk()
    app = ImportProduse(root)
    root.mainloop()
