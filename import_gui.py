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
        """LEGACY - păstrat pentru compatibilitate. Folosește generate_webgsm_sku() pentru SKU-uri noi."""
        ean_int = int(ean) if ean.isdigit() else int(''.join(c for c in ean if c.isdigit()))
        sequential_id = (ean_int % 100000)
        sku = f"890{sequential_id:05d}00000"
        return sku

    def generate_webgsm_sku(self, product_name, brand_piesa, counter):
        """
        Generează SKU unic format: WG-{TIP}-{MODEL}-{BRAND}-{NR}
        Exemple: WG-ECR-IP13-JK-01, WG-BAT-S24U-SO-02, WG-CRC-IP14P-XX-01

        Formatul include TIPUL PIESEI pentru a diferenția produse diferite
        pentru același model (ecran vs baterie vs carcasă etc.)
        """
        # CODURI TIP PIESA (3 litere) - ORDINEA CONTEAZĂ (cele mai specifice primele)
        type_map = {
            'ECR': ['display', 'screen', 'oled', 'lcd', 'digitizer', 'ecran'],
            'BAT': ['battery', 'baterie', 'acumulator'],
            'CAM': ['camera', 'lens'],
            'CRC': ['housing', 'back glass', 'frame', 'back cover', 'rear glass', 'carcasa'],
            'DIF': ['speaker', 'earpiece', 'buzzer', 'difuzor'],
            'BTN': ['button', 'power button', 'volume', 'buton'],
            'SNZ': ['sensor', 'proximity', 'face id'],
            'TAP': ['taptic', 'vibrator', 'motor'],
            'SIM': ['sim tray', 'sim card'],
            'ANT': ['antenna', 'wifi', 'gps'],
            'FOL': ['folie', 'tempered', 'screen protector'],
            'FLX': ['flex', 'cable', 'connector', 'charging port', 'dock'],
        }

        name_lower = product_name.lower()

        # Detectează tipul piesei
        type_code = 'PIS'  # default = Piesă
        for code, keywords in type_map.items():
            if any(kw in name_lower for kw in keywords):
                type_code = code
                break

        # CODURI MODEL TELEFON
        model_map = {
            'iphone 17 pro max': 'IP17PM',
            'iphone 17 pro': 'IP17P',
            'iphone 17 plus': 'IP17PL',
            'iphone 17 air': 'IP17A',
            'iphone 17': 'IP17',
            'iphone 16 pro max': 'IP16PM',
            'iphone 16 pro': 'IP16P',
            'iphone 16 plus': 'IP16PL',
            'iphone 16': 'IP16',
            'iphone 15 pro max': 'IP15PM',
            'iphone 15 pro': 'IP15P',
            'iphone 15 plus': 'IP15PL',
            'iphone 15': 'IP15',
            'iphone 14 pro max': 'IP14PM',
            'iphone 14 pro': 'IP14P',
            'iphone 14 plus': 'IP14PL',
            'iphone 14': 'IP14',
            'iphone 13 pro max': 'IP13PM',
            'iphone 13 pro': 'IP13P',
            'iphone 13 mini': 'IP13M',
            'iphone 13': 'IP13',
            'iphone 12 pro max': 'IP12PM',
            'iphone 12 pro': 'IP12P',
            'iphone 12 mini': 'IP12M',
            'iphone 12': 'IP12',
            'iphone 11 pro max': 'IP11PM',
            'iphone 11 pro': 'IP11P',
            'iphone 11': 'IP11',
            'iphone xs max': 'IPXSM',
            'iphone xs': 'IPXS',
            'iphone xr': 'IPXR',
            'iphone x': 'IPX',
            'iphone se': 'IPSE',
            'iphone 8 plus': 'IP8P',
            'iphone 8': 'IP8',
            'iphone 7 plus': 'IP7P',
            'iphone 7': 'IP7',
            'galaxy s24 ultra': 'S24U',
            'galaxy s24+': 'S24P',
            'galaxy s24 plus': 'S24P',
            'galaxy s24': 'S24',
            'galaxy s23 ultra': 'S23U',
            'galaxy s23+': 'S23P',
            'galaxy s23 plus': 'S23P',
            'galaxy s23': 'S23',
            'galaxy s22 ultra': 'S22U',
            'galaxy s22+': 'S22P',
            'galaxy s22': 'S22',
            'galaxy s21 ultra': 'S21U',
            'galaxy s21+': 'S21P',
            'galaxy s21': 'S21',
            'galaxy z fold 5': 'ZF5',
            'galaxy z fold 4': 'ZF4',
            'galaxy z flip 5': 'ZFL5',
            'galaxy z flip 4': 'ZFL4',
            'galaxy a54': 'A54',
            'galaxy a53': 'A53',
            'galaxy a52': 'A52',
            'galaxy a51': 'A51',
            'galaxy a34': 'A34',
            'galaxy a33': 'A33',
            'galaxy a14': 'A14',
            'pixel 8 pro': 'PX8P',
            'pixel 8': 'PX8',
            'pixel 7 pro': 'PX7P',
            'pixel 7': 'PX7',
        }

        model_code = 'UNK'
        for model, code in model_map.items():
            if model in name_lower:
                model_code = code
                break

        brand_code = brand_piesa.upper()[:2] if brand_piesa else 'XX'

        return f"WG-{type_code}-{model_code}-{brand_code}-{counter:02d}"

    def extract_product_attributes(self, product_name, description='', product_url=''):
        """
        Extrage atributele WooCommerce din titlul produsului (și opțional din URL slug).
        Returnează: pa_model, pa_calitate, pa_brand-piesa, pa_tehnologie
        """
        text = f"{product_name} {description}".lower()

        # MODEL COMPATIBIL (ordinea contează - cele mai specifice primele)
        model = ''
        model_patterns = [
            ('iphone 17 pro max', 'iPhone 17 Pro Max'),
            ('iphone 17 pro', 'iPhone 17 Pro'),
            ('iphone 17 plus', 'iPhone 17 Plus'),
            ('iphone 17 air', 'iPhone 17 Air'),
            ('iphone 17', 'iPhone 17'),
            ('iphone 16 pro max', 'iPhone 16 Pro Max'),
            ('iphone 16 pro', 'iPhone 16 Pro'),
            ('iphone 16 plus', 'iPhone 16 Plus'),
            ('iphone 16', 'iPhone 16'),
            ('iphone 15 pro max', 'iPhone 15 Pro Max'),
            ('iphone 15 pro', 'iPhone 15 Pro'),
            ('iphone 15 plus', 'iPhone 15 Plus'),
            ('iphone 15', 'iPhone 15'),
            ('iphone 14 pro max', 'iPhone 14 Pro Max'),
            ('iphone 14 pro', 'iPhone 14 Pro'),
            ('iphone 14 plus', 'iPhone 14 Plus'),
            ('iphone 14', 'iPhone 14'),
            ('iphone 13 pro max', 'iPhone 13 Pro Max'),
            ('iphone 13 pro', 'iPhone 13 Pro'),
            ('iphone 13 mini', 'iPhone 13 Mini'),
            ('iphone 13', 'iPhone 13'),
            ('iphone 12 pro max', 'iPhone 12 Pro Max'),
            ('iphone 12 pro', 'iPhone 12 Pro'),
            ('iphone 12 mini', 'iPhone 12 Mini'),
            ('iphone 12', 'iPhone 12'),
            ('iphone 11 pro max', 'iPhone 11 Pro Max'),
            ('iphone 11 pro', 'iPhone 11 Pro'),
            ('iphone 11', 'iPhone 11'),
            ('iphone xs max', 'iPhone XS Max'),
            ('iphone xs', 'iPhone XS'),
            ('iphone xr', 'iPhone XR'),
            ('iphone x', 'iPhone X'),
            ('iphone se', 'iPhone SE'),
            ('galaxy s24 ultra', 'Galaxy S24 Ultra'),
            ('galaxy s24+', 'Galaxy S24+'),
            ('galaxy s24', 'Galaxy S24'),
            ('galaxy s23 ultra', 'Galaxy S23 Ultra'),
            ('galaxy s23+', 'Galaxy S23+'),
            ('galaxy s23', 'Galaxy S23'),
            ('galaxy s22 ultra', 'Galaxy S22 Ultra'),
            ('galaxy s22', 'Galaxy S22'),
            ('galaxy s21 ultra', 'Galaxy S21 Ultra'),
            ('galaxy s21', 'Galaxy S21'),
            ('galaxy z fold 5', 'Galaxy Z Fold 5'),
            ('galaxy z fold 4', 'Galaxy Z Fold 4'),
            ('galaxy z flip 5', 'Galaxy Z Flip 5'),
            ('galaxy z flip 4', 'Galaxy Z Flip 4'),
            ('galaxy a54', 'Galaxy A54'),
            ('galaxy a53', 'Galaxy A53'),
            ('galaxy a52', 'Galaxy A52'),
            ('galaxy a51', 'Galaxy A51'),
            ('galaxy a34', 'Galaxy A34'),
            ('galaxy a14', 'Galaxy A14'),
            ('pixel 8 pro', 'Pixel 8 Pro'),
            ('pixel 8', 'Pixel 8'),
            ('pixel 7 pro', 'Pixel 7 Pro'),
            ('pixel 7', 'Pixel 7'),
        ]
        for pattern, value in model_patterns:
            if pattern in text:
                model = value
                break

        # Fallback: extrage model din URL slug (ex: .../iphone-17-aftermarket-plus-soft...)
        if not model and product_url:
            slug_lower = product_url.rstrip('/').split('/')[-1].replace('-', ' ')
            for pattern, value in model_patterns:
                if pattern in slug_lower:
                    model = value
                    break

        # CALITATE (ordinea contează - cele mai specifice primele)
        calitate = 'Aftermarket'
        if 'service pack' in text or ('original' in text and 'genuine' in text):
            calitate = 'Service Pack'
        elif 'genuine' in text:
            calitate = 'Service Pack'
        elif 'aftermarket plus' in text:
            calitate = 'Aftermarket Plus'
        elif 'premium' in text or ('oem' in text and 'premium' in text):
            calitate = 'Premium OEM'
        elif 'oem' in text:
            calitate = 'Premium OEM'
        elif 'refurbished' in text or 'refurb' in text:
            calitate = 'Refurbished'

        # BRAND PIESA (Aftermarket Plus = calitate premium, poate apărea și ca brand)
        brand_piesa = ''
        brand_patterns = [
            ('JK', [' jk ', ' jk-', '(jk)', 'jk incell', 'jk soft']),
            ('GX', [' gx ', ' gx-', '(gx)', 'gx soft', 'gx hard']),
            ('ZY', [' zy ', ' zy-', '(zy)', 'zy soft']),
            ('RJ', [' rj ', ' rj-', '(rj)', 'rj incell']),
            ('HEX', [' hex ', ' hex-', '(hex)']),
            ('Foxconn', ['foxconn']),
            ('BOE', [' boe ', '(boe)']),
            ('Tianma', ['tianma']),
        ]
        padded_name = f' {product_name} '.lower()
        padded_text = f' {product_name} {description} '.lower()
        for brand, keywords in brand_patterns:
            if any(kw in padded_text for kw in keywords):
                brand_piesa = brand
                break
        if not brand_piesa:
            if 'apple' in text and ('original' in text or 'genuine' in text or 'service pack' in text):
                brand_piesa = 'Apple Original'
            elif 'samsung' in text and ('original' in text or 'genuine' in text or 'service pack' in text):
                brand_piesa = 'Samsung Original'
            elif calitate == 'Aftermarket Plus':
                brand_piesa = 'Aftermarket Plus'

        # TEHNOLOGIE (doar pentru ecrane)
        tehnologie = ''
        if any(x in text for x in ['display', 'screen', 'lcd', 'oled', 'ecran', 'assembly']):
            if 'soft' in text and 'oled' in text:
                tehnologie = 'Soft OLED'
            elif 'soft oled' in text:
                tehnologie = 'Soft OLED'
            elif ': soft)' in text or ': soft ' in text or ': soft' in text or ':soft' in text:
                # Pattern MobileSentrix: "(Aftermarket Plus: Soft)"
                tehnologie = 'Soft OLED'
            elif 'hard oled' in text:
                tehnologie = 'Hard OLED'
            elif ': hard)' in text or ': hard ' in text or ':hard' in text:
                # Pattern MobileSentrix: "(Aftermarket Plus: Hard)"
                tehnologie = 'Hard OLED'
            elif 'amoled' in text:
                tehnologie = 'AMOLED'
            elif 'oled' in text and ('original' in text or 'genuine' in text):
                tehnologie = 'OLED Original'
            elif 'oled' in text:
                tehnologie = 'OLED'
            elif 'incell' in text or 'in-cell' in text:
                tehnologie = 'Incell'
            elif 'tft' in text:
                tehnologie = 'TFT'
            elif 'lcd' in text:
                tehnologie = 'LCD'

        # 🎯 Detectare 120Hz / 90Hz din titlu
        self._detected_refresh_rate = ''
        if '120hz' in text or '120 hz' in text:
            self._detected_refresh_rate = '120Hz'
        elif '90hz' in text or '90 hz' in text:
            self._detected_refresh_rate = '90Hz'

        return {
            'pa_model': model,
            'pa_calitate': calitate,
            'pa_brand_piesa': brand_piesa,
            'pa_tehnologie': tehnologie
        }

    def get_webgsm_category(self, product_name, product_type=''):
        """
        Returnează categoria WooCommerce cu slug corect.
        Format: slug-categorie (ex: ecrane-iphone, baterii-samsung)
        """
        text = product_name.lower()

        # Detectare tip produs
        tip = ''
        if any(x in text for x in ['display', 'screen', 'lcd', 'oled', 'ecran', 'amoled']):
            tip = 'ecrane'
        elif any(x in text for x in ['battery', 'baterie', 'acumulator']):
            tip = 'baterii'
        elif any(x in text for x in ['camera', 'cameră', 'lens']):
            tip = 'camere'
        elif any(x in text for x in ['flex', 'cable', 'conector', 'connector', 'charging port', 'dock']):
            tip = 'flex-uri'
        elif any(x in text for x in ['housing', 'back glass', 'carcas', 'frame', 'back cover', 'rear glass']):
            tip = 'carcase'
        elif any(x in text for x in ['speaker', 'earpiece', 'difuzor', 'buzzer']):
            tip = 'difuzoare'
        elif any(x in text for x in ['button', 'buton', 'power button', 'volume']):
            tip = 'butoane'
        elif any(x in text for x in ['tempered glass', 'screen protector', 'folie']):
            tip = 'folii-protectie'
        elif any(x in text for x in ['charger', 'incarcator', 'adapter']):
            tip = 'incarcatoare'
        else:
            tip = 'accesorii-service'

        # Detectare brand telefon
        brand = ''
        if 'iphone' in text or 'ipad' in text:
            brand = 'iphone'
        elif 'galaxy' in text or 'samsung' in text:
            brand = 'samsung'
        elif 'huawei' in text or 'honor' in text:
            brand = 'huawei'
        elif 'xiaomi' in text or 'redmi' in text or 'poco' in text:
            brand = 'xiaomi'
        elif 'pixel' in text or 'google' in text:
            brand = 'google'
        elif 'motorola' in text or 'moto ' in text:
            brand = 'motorola'
        elif 'oneplus' in text:
            brand = 'oneplus'

        if brand:
            return f"{tip}-{brand}"
        return tip

    def extract_compatibility_codes(self, description):
        """
        Extrage coduri Apple (A####) din descriere.
        Returnează string cu coduri separate prin virgulă.
        """
        pattern = r'\bA\d{4}\b'
        codes = re.findall(pattern, description)
        return ', '.join(sorted(set(codes))) if codes else ''

    def detect_screen_features(self, product_name, description=''):
        """
        Detectează caracteristici ecran: IC Movable, TrueTone support.
        """
        text = f"{product_name} {description}".lower()

        ic_movable = 'true' if any(x in text for x in [
            'with ic', 'ic installed', 'ic included', 'movable ic',
            'transplant ic', 'ic transferabil', 'ic chip', 'flex with ic'
        ]) else 'false'

        truetone = 'true' if any(x in text for x in [
            'true tone', 'truetone', 'true-tone', 'supports true tone',
            'support truetone', 'true tone supported'
        ]) else 'false'

        return {
            'ic_movable': ic_movable,
            'truetone_support': truetone
        }

    def _detect_tip_produs_ro(self, product_name):
        """Detectează tipul produsului în română din titlul EN."""
        text = product_name.lower()
        if any(x in text for x in ['display', 'screen', 'oled', 'lcd', 'digitizer']):
            return 'Ecran'
        if any(x in text for x in ['battery', 'baterie', 'acumulator']):
            return 'Baterie'
        if any(x in text for x in ['camera', 'cameră', 'lens']):
            return 'Cameră'
        if any(x in text for x in ['flex', 'cable', 'connector', 'charging port', 'dock']):
            return 'Flex'
        if any(x in text for x in ['housing', 'back glass', 'frame', 'back cover', 'rear glass']):
            return 'Carcasă'
        if any(x in text for x in ['speaker', 'earpiece', 'buzzer']):
            return 'Difuzor'
        if any(x in text for x in ['button', 'power button', 'volume']):
            return 'Buton'
        return 'Piesă'

    def generate_seo_title(self, product_name, model, brand_piesa, tehnologie):
        """
        Generează titlu SEO optimizat (max 60 chars pentru Google).
        Format: "{Tip} {Model} {Tehnologie} {Brand} {120Hz} - Garanție | WebGSM"
        Exemplu: "Ecran iPhone 17 Soft OLED 120Hz - Garanție | WebGSM"
        """
        tip_ro = self._detect_tip_produs_ro(product_name)

        parts = [tip_ro]
        if model:
            parts.append(model)
        if tehnologie:
            parts.append(tehnologie)
        if brand_piesa:
            parts.append(brand_piesa)

        # Detectează 120Hz din titlul original
        name_lower = product_name.lower()
        if '120hz' in name_lower or '120 hz' in name_lower:
            parts.append('120Hz')

        title = ' '.join(parts)
        seo = f"{title} - Garanție | WebGSM"

        # Dacă e prea lung (>60 chars), scurtăm sufixul
        if len(seo) > 60:
            seo = f"{title} | WebGSM"
        if len(seo) > 60:
            seo = title[:57] + "..."

        return self.fix_romanian_diacritics(seo)

    def generate_seo_description(self, product_name, model, brand_piesa, tehnologie, calitate):
        """
        Generează meta description SEO (max 155 caractere).
        Exemplu: "Ecran iPhone 17 Soft OLED calitate Aftermarket Plus 120Hz. Garanție 24 luni. Livrare rapidă România."
        """
        tip_ro = self._detect_tip_produs_ro(product_name)

        desc = f"{tip_ro} {model or ''}"
        if tehnologie:
            desc += f" {tehnologie}"
        if brand_piesa:
            desc += f" {brand_piesa}"
        if calitate:
            desc += f" calitate {calitate}"

        # Detectează 120Hz din titlul original
        name_lower = product_name.lower()
        if '120hz' in name_lower or '120 hz' in name_lower:
            desc += " 120Hz"

        desc += ". Garanție 24 luni. Livrare rapidă România."

        # Curăță spații duble
        desc = ' '.join(desc.split())

        if len(desc) > 155:
            desc = desc[:152] + "..."

        return self.fix_romanian_diacritics(desc)

    def generate_focus_keyword(self, product_name, model):
        """
        Generează focus keyword pentru Rank Math SEO.
        Exemplu: "ecran iphone 17 oled"
        """
        tip_map = {
            'display': 'ecran', 'screen': 'ecran', 'oled': 'ecran',
            'lcd': 'ecran', 'digitizer': 'ecran', 'assembly': 'ecran',
            'battery': 'baterie', 'acumulator': 'baterie',
            'camera': 'camera', 'lens': 'camera',
            'flex': 'flex', 'cable': 'flex', 'connector': 'flex',
            'charging port': 'port incarcare',
            'housing': 'carcasa', 'back glass': 'carcasa', 'frame': 'carcasa',
            'speaker': 'difuzor', 'earpiece': 'difuzor',
            'button': 'buton',
        }
        text = product_name.lower()
        tip_ro = 'piesa'
        for en, ro in tip_map.items():
            if en in text:
                tip_ro = ro
                break

        parts = [tip_ro]
        if model:
            parts.append(model.lower())

        # Adaugă tehnologia principală pentru keyword mai precis
        if 'oled' in text:
            parts.append('oled')
        elif 'lcd' in text:
            parts.append('lcd')

        return ' '.join(parts)

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
        """Execută exportul în CSV format WebGSM cu upload imagini pe WordPress"""
        try:
            self.log("=" * 70, "INFO")
            self.log(f"🚀 START PROCESARE PRODUSE (Mod: CSV WebGSM + Upload Imagini)", "INFO")
            self.log("=" * 70, "INFO")

            # Citește SKU-uri
            skus = self.read_sku_file(self.sku_file_var.get())
            self.log(f"📋 Găsite {len(skus)} SKU-uri pentru procesare", "INFO")

            success_count = 0
            error_count = 0
            sku_counter = 0  # Counter global pentru SKU-uri WebGSM
            products_data = []  # Lista pentru CSV

            for idx, sku in enumerate(skus, 1):
                if not self.running:
                    break

                self.progress_var.set(f"Procesez produs {idx}/{len(skus)}: {sku}")
                self.log(f"\n" + "="*70, "INFO")
                self.log(f"[{idx}/{len(skus)}] 🔵 START procesare: {sku}", "INFO")
                self.log(f"="*70, "INFO")

                try:
                    # Scraping produs de pe MobileSentrix
                    product_data = self.scrape_product(sku)

                    if product_data:
                        # Generează WebGSM SKU (format: WG-TIP-MODEL-BRAND-NR)
                        sku_counter += 1
                        brand_piesa = product_data.get('pa_brand_piesa', '')
                        webgsm_sku = self.generate_webgsm_sku(
                            product_data.get('name', ''),
                            brand_piesa,
                            sku_counter
                        )

                        # Adaugă date suplimentare
                        product_data['webgsm_sku'] = webgsm_sku
                        # sku_furnizor e deja setat corect în scrape_product()
                        # ean_real e deja setat corect în scrape_product()

                        success_count += 1
                        self.log(f"✓ Produs procesat! SKU: {webgsm_sku}", "SUCCESS")

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
                self.log("📝 CREARE FIȘIER CSV WEBGSM...", "INFO")
                self.log("=" * 70, "INFO")

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_filename = f"export_webgsm_{timestamp}.csv"
                csv_path = self.export_to_csv(products_data, csv_filename)

                if csv_path:
                    self.log(f"\n✅ CSV WebGSM creat: {csv_path}", "SUCCESS")

            # Sumar final
            self.log("\n" + "=" * 70, "INFO")
            self.log(f"📊 SUMAR PROCESARE WEBGSM:", "INFO")
            self.log(f"   ✓ Produse procesate cu succes: {success_count}", "SUCCESS")
            self.log(f"   ✗ Erori scraping: {error_count}", "ERROR")
            self.log(f"   📦 Total SKU-uri: {len(skus)}", "INFO")
            self.log(f"   📁 Imagini salvate în: images/", "INFO")
            if products_data:
                self.log(f"   🏷️ SKU-uri generate: WG-...-01 pana la WG-...-{sku_counter:02d}", "INFO")
            self.log("=" * 70, "INFO")

            csv_info = f"\nFișier CSV: {csv_filename}" if csv_filename else ""
            messagebox.showinfo("Finalizat",
                f"Procesare WebGSM finalizată!\n\nProduse procesate: {success_count}\nErori: {error_count}{csv_info}\nFolderul imagini: images/")

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
    
    def build_longtail_title(self, translated_name, description="", attributes=None):
        """
        Construiește titlu Long Tail SEO optimizat.

        STRATEGIE: Folosește numele tradus (RO) ca bază principală,
        îmbogățit cu atributele deja extrase de extract_product_attributes().

        Format: "{Tip} {Model} {Tehnologie} {Brand} {Culoare} - {Calitate}"
        Exemplu: "Ecran iPhone 13 OLED JK Negru - Premium OEM"

        Args:
            translated_name: Numele produsului tradus în română
            description: Descrierea produsului (EN sau RO)
            attributes: Dict cu pa_model, pa_calitate, pa_brand_piesa, pa_tehnologie
                       (din extract_product_attributes, disponibil ca product dict keys)
        """
        import re

        if not attributes:
            attributes = {}

        # Folosește atributele deja extrase (sunt corecte, testate)
        pa_model = attributes.get('pa_model', '')
        pa_calitate = attributes.get('pa_calitate', '')
        pa_brand_piesa = attributes.get('pa_brand_piesa', '')
        pa_tehnologie = attributes.get('pa_tehnologie', '')

        # 1. TIP PRODUS (RO) - din titlul original EN, deja testat în _detect_tip_produs_ro
        original_name = attributes.get('original_name', translated_name)
        tip_ro = self._detect_tip_produs_ro(original_name)

        # 2. CULOARE - detectare cu word boundaries (previne false positives)
        color_map = {
            'Negru': [r'\bnegru\b', r'\bblack\b', r'\bnoir\b'],
            'Alb': [r'\balb\b', r'\bwhite\b', r'\bblanc\b'],
            'Gri': [r'\bgri\b', r'\bgray\b', r'\bgrey\b'],
            'Argintiu': [r'\bargintiu\b', r'\bsilver\b', r'\bargent\b'],
            'Auriu': [r'\bauriu\b', r'\bgold\b', r'\bgolden\b'],
            'Albastru': [r'\balbastru\b', r'\bblue\b', r'\bbleu\b'],
            'Roșu': [r'\brosu\b', r'\broșu\b', r'\bred\b', r'\brouge\b'],
            'Verde': [r'\bverde\b', r'\bgreen\b', r'\bvert\b'],
            'Roz': [r'\broz\b', r'\bpink\b', r'\brose\b'],
            'Violet': [r'\bviolet\b', r'\bpurple\b', r'\bdeep purple\b'],
            'Portocaliu': [r'\bportocaliu\b', r'\borange\b'],
            'Coral': [r'\bcoral\b'],
            'Miezul Nopții': [r'\bmidnight\b'],
            'Stelar': [r'\bstarlight\b'],
        }

        text_lower = f"{translated_name} {description}".lower()
        color = ''
        for col, patterns in color_map.items():
            if any(re.search(p, text_lower) for p in patterns):
                color = col
                break

        # 3. Detectare 120Hz/90Hz din titlu original + descriere
        refresh_rate = ''
        combined_lower = f"{original_name} {description}".lower()
        if '120hz' in combined_lower or '120 hz' in combined_lower:
            refresh_rate = '120Hz'
        elif '90hz' in combined_lower or '90 hz' in combined_lower:
            refresh_rate = '90Hz'

        # 4. Construiește titlul: Tip + Model + Tehnologie + RefreshRate + Brand + Culoare - Calitate
        parts = [tip_ro]

        if pa_model:
            parts.append(pa_model)

        if pa_tehnologie:
            parts.append(pa_tehnologie)

        if refresh_rate:
            parts.append(refresh_rate)

        if pa_brand_piesa:
            parts.append(pa_brand_piesa)

        if color:
            parts.append(color)

        longtail = ' '.join(parts)

        # Adaugă calitatea ca sufix dacă nu e generic "Aftermarket"
        if pa_calitate and pa_calitate not in ('Aftermarket', ''):
            longtail += f" - {pa_calitate}"

        # Corectează diacriticele (sedilă → virgulă)
        longtail = self.fix_romanian_diacritics(longtail)

        return longtail

    def remove_diacritics(self, text):
        """DEZACTIVAT - Păstrăm diacriticele românești corecte.
        Apelează fix_romanian_diacritics() în loc să elimine diacriticele."""
        return self.fix_romanian_diacritics(text)

    def fix_romanian_diacritics(self, text):
        """
        Convertește diacriticele cu sedilă în cele corecte cu virgulă.
        Google Translate uneori returnează sedilă (ş, ţ) în loc de virgulă (ș, ț).

        Corectări:
          ş (U+015F, s with cedilla) → ș (U+0219, s with comma below)
          ţ (U+0163, t with cedilla) → ț (U+021B, t with comma below)
          Ş (U+015E) → Ș (U+0218)
          Ţ (U+0162) → Ț (U+021A)
        """
        if not text:
            return text

        # Sedilă → Virgulă (lowercase)
        text = text.replace('\u015f', '\u0219')  # ş → ș
        text = text.replace('\u0163', '\u021b')  # ţ → ț

        # Sedilă → Virgulă (uppercase)
        text = text.replace('\u015e', '\u0218')  # Ş → Ș
        text = text.replace('\u0162', '\u021a')  # Ţ → Ț

        return text

    # ⚡ Cache traduceri - evită apeluri duplicate la Google Translate
    _translation_cache = {}

    def translate_text(self, text, source='en', target='ro'):
        """Traduce text folosind Google Translate (cu cache + diacritice corecte)."""
        if not text or not text.strip():
            return text

        # Verifică cache-ul (aceleași texte nu se mai traduc de două ori)
        cache_key = f"{source}:{target}:{text.strip()[:200]}"
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key]

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

            # Corectează sedilă → virgulă (ş→ș, ţ→ț) pentru română
            if target == 'ro':
                translated = self.fix_romanian_diacritics(translated)

            # Salvează în cache pentru reutilizare
            self._translation_cache[cache_key] = translated
            return translated

        except Exception as e:
            self.log(f"⚠ Eroare traducere: {e}", "WARNING")
            return text  # Returnează textul original dacă traducerea eșuează
    
    def export_to_csv(self, products_data, filename="export_produse.csv"):
        """Exportă produsele în CSV format WebGSM cu atribute, ACF meta și SEO Rank Math"""
        import csv

        try:
            csv_path = Path("data") / filename
            self.log(f"📄 Creez fișier CSV WebGSM: {csv_path}", "INFO")
            self.log(f"⏳ Procesez {len(products_data)} produse cu upload imagini pe WordPress...", "INFO")

            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = [
                    'ID', 'Type', 'SKU', 'Name', 'Published', 'Is featured?',
                    'Visibility in catalog', 'Short description', 'Description',
                    'Tax status', 'Tax class', 'In stock?', 'Stock', 'Regular price',
                    'Categories', 'Tags', 'Images', 'Parent',
                    # ATRIBUTE WOOCOMMERCE (4 atribute x 4 coloane)
                    'Attribute 1 name', 'Attribute 1 value(s)', 'Attribute 1 visible', 'Attribute 1 global',
                    'Attribute 2 name', 'Attribute 2 value(s)', 'Attribute 2 visible', 'Attribute 2 global',
                    'Attribute 3 name', 'Attribute 3 value(s)', 'Attribute 3 visible', 'Attribute 3 global',
                    'Attribute 4 name', 'Attribute 4 value(s)', 'Attribute 4 visible', 'Attribute 4 global',
                    # ACF META
                    'meta:gtin_ean', 'meta:sku_furnizor', 'meta:furnizor_activ',
                    'meta:pret_achizitie', 'meta:locatie_stoc', 'meta:garantie_luni',
                    'meta:coduri_compatibilitate', 'meta:ic_movable', 'meta:truetone_support',
                    # SEO RANK MATH
                    'meta:rank_math_title', 'meta:rank_math_description', 'meta:rank_math_focus_keyword'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()

                for idx, product in enumerate(products_data, 1):
                    self.log(f"🔄 Proceseaza produs {idx}/{len(products_data)}: {product.get('name', 'N/A')}", "INFO")

                    # ⚡ Upload PARALEL imagini pe WordPress (de la ~2min la ~30s)
                    from concurrent.futures import ThreadPoolExecutor, as_completed
                    image_urls = []
                    if product.get('images'):
                        # Pregătește lista de imagini de uploadat
                        upload_tasks = []
                        fallback_urls = {}  # idx -> fallback URL
                        for img_idx, img in enumerate(product['images']):
                            img_path = None
                            if isinstance(img, dict):
                                if 'local_path' in img:
                                    img_path = img['local_path']
                            else:
                                img_path = str(img)

                            if img_path and Path(img_path).exists():
                                upload_tasks.append((img_idx, img_path))
                                if isinstance(img, dict) and 'src' in img:
                                    fallback_urls[img_idx] = img['src']
                            elif isinstance(img, dict) and 'src' in img:
                                # Nu există local, folosește URL direct
                                image_urls.append((img_idx, img['src']))

                        if upload_tasks:
                            self.log(f"   📤 Upload {len(upload_tasks)} imagini pe WordPress (paralel)...", "INFO")

                            def _upload_one(args):
                                img_idx, img_path = args
                                try:
                                    result = self.upload_image_to_wordpress(img_path)
                                    if result:
                                        wp_url = result.get('src') if isinstance(result, dict) else result
                                        return {'success': True, 'idx': img_idx, 'url': wp_url}
                                    else:
                                        fb = fallback_urls.get(img_idx, '')
                                        return {'success': False, 'idx': img_idx, 'url': fb}
                                except Exception as e:
                                    fb = fallback_urls.get(img_idx, '')
                                    return {'success': False, 'idx': img_idx, 'url': fb, 'error': str(e)}

                            # Upload paralel: 3 thread-uri (nu supraîncărcăm WordPress)
                            wp_results = []
                            with ThreadPoolExecutor(max_workers=3) as executor:
                                futures = {executor.submit(_upload_one, task): task for task in upload_tasks}
                                for future in as_completed(futures):
                                    res = future.result()
                                    if res['success']:
                                        wp_results.append((res['idx'], res['url']))
                                        self.log(f"   ✓ [{res['idx']+1}] Uploadat pe WordPress", "SUCCESS")
                                    elif res['url']:
                                        wp_results.append((res['idx'], res['url']))
                                        self.log(f"   ⚠ [{res['idx']+1}] Upload eșuat, URL original", "WARNING")
                                    else:
                                        self.log(f"   ✗ [{res['idx']+1}] Upload eșuat, fără fallback", "ERROR")

                            # Combină cu URL-urile directe și sortează după index
                            image_urls.extend(wp_results)

                        # Sortează după index și extrage doar URL-urile
                        image_urls.sort(key=lambda x: x[0])
                        image_urls = [url for _, url in image_urls]

                    # Calculează preț RON (păstrează EUR original)
                    price_eur = product['price']
                    price_ron = price_eur
                    if self.convert_price_var.get():
                        exchange_rate = float(self.exchange_rate_var.get())
                        price_ron = price_eur * exchange_rate

                    # Curăță numele (elimină " Copy" de la sfârșit)
                    clean_name = product.get('name', 'N/A')
                    if clean_name.endswith(' Copy'):
                        clean_name = clean_name[:-5]

                    # Traduce numele în română
                    clean_name_ro = self.translate_text(clean_name, source='en', target='ro')
                    self.log(f"   🌍 Titlu tradus: {clean_name} → {clean_name_ro}", "INFO")

                    # Atribute din produs (pre-extrase în scrape_product)
                    pa_model = product.get('pa_model', '')
                    pa_calitate = product.get('pa_calitate', 'Aftermarket')
                    pa_brand_piesa = product.get('pa_brand_piesa', '')
                    pa_tehnologie = product.get('pa_tehnologie', '')

                    # Construiește titlu Long Tail SEO optimizat
                    description_for_longtail = product.get('description', '')
                    longtail_attrs = {
                        'pa_model': pa_model,
                        'pa_calitate': pa_calitate,
                        'pa_brand_piesa': pa_brand_piesa,
                        'pa_tehnologie': pa_tehnologie,
                        'original_name': clean_name,  # titlul EN original pentru detectare tip
                    }
                    longtail_title = self.build_longtail_title(clean_name_ro, description_for_longtail, longtail_attrs)
                    self.log(f"   📝 Titlu Long Tail: {longtail_title}", "INFO")

                    # Curăță descrierea (elimină URL-uri)
                    clean_desc = product.get('description', '')[:500]
                    clean_desc = re.sub(r'https?://\S+', '', clean_desc).strip()

                    # Traduce descrierea în română
                    clean_desc_ro = self.translate_text(clean_desc, source='en', target='ro')
                    self.log(f"   🌍 Descriere tradusă: {len(clean_desc)} → {len(clean_desc_ro)} caractere", "INFO")

                    # 🔧 Generează Short Description inteligent (nu "Produs" generic)
                    tip_ro = self._detect_tip_produs_ro(clean_name)
                    short_desc_parts = [tip_ro]
                    if pa_model:
                        short_desc_parts.append(pa_model)
                    if pa_tehnologie:
                        short_desc_parts.append(pa_tehnologie)
                    if pa_calitate and pa_calitate != 'Aftermarket':
                        short_desc_parts.append(f"calitate {pa_calitate}")
                    short_desc_intro = ' '.join(short_desc_parts)
                    short_description = f"{short_desc_intro}. Garanție inclusă. Livrare rapidă în toată România."
                    short_description = self.fix_romanian_diacritics(short_description)
                    if len(short_description) > 160:
                        short_description = short_description[:157] + "..."

                    # SKU: folosește WebGSM SKU generat (WG-ECR-IP13-JK-01)
                    sku_value = product.get('webgsm_sku', product.get('sku', 'N/A'))

                    # EAN: cod de bare real extras de pe pagina furnizorului
                    ean_value = product.get('ean_real', '')

                    # SKU furnizor: codul MobileSentrix (ex: 107182127516)
                    sku_furnizor = product.get('sku_furnizor', product.get('sku', ''))

                    # Detectează garanția (număr luni)
                    warranty_text = self.detect_warranty(clean_name_ro, product.get('category_path', ''))
                    # Convertește "12 luni" -> 12, "6 luni" -> 6, etc.
                    warranty_months = re.search(r'(\d+)', warranty_text)
                    warranty_months = warranty_months.group(1) if warranty_months else '12'
                    self.log(f"   ⏱️ Garantie: {warranty_months} luni", "INFO")

                    # Combină toate imaginile
                    all_images = ', '.join(image_urls) if image_urls else ''

                    # Categorii: folosește slug WebGSM
                    category_slug = product.get('category_slug', '')
                    # Păstrează și categoria ierarhică dacă slug-ul e gol
                    categories = category_slug if category_slug else product.get('category_path', '')

                    # SEO Rank Math (funcții dedicate cu diacritice corecte)
                    original_name = product.get('name', '')
                    seo_title = self.generate_seo_title(original_name, pa_model, pa_brand_piesa, pa_tehnologie)
                    seo_description = self.generate_seo_description(original_name, pa_model, pa_brand_piesa, pa_tehnologie, pa_calitate)
                    seo_keyword = self.generate_focus_keyword(original_name, pa_model)

                    self.log(f"   🔍 SEO: {seo_title[:60]}...", "INFO")

                    row = {
                        'ID': '',
                        'Type': 'simple',
                        'SKU': sku_value,
                        'Name': longtail_title,
                        'Published': '1',
                        'Is featured?': '0',
                        'Visibility in catalog': 'visible',
                        'Short description': short_description,
                        'Description': clean_desc_ro,
                        'Tax status': 'taxable',
                        'Tax class': '',
                        'In stock?': '1',
                        'Stock': product.get('stock', '100'),
                        'Regular price': f"{price_ron:.2f}",
                        'Categories': categories,
                        'Tags': product.get('tags', ''),
                        'Images': all_images,
                        'Parent': '',
                        # ATRIBUT 1: Model Compatibil
                        'Attribute 1 name': 'Model Compatibil',
                        'Attribute 1 value(s)': pa_model,
                        'Attribute 1 visible': '1',
                        'Attribute 1 global': '1',
                        # ATRIBUT 2: Calitate
                        'Attribute 2 name': 'Calitate',
                        'Attribute 2 value(s)': pa_calitate,
                        'Attribute 2 visible': '1',
                        'Attribute 2 global': '1',
                        # ATRIBUT 3: Brand Piesa
                        'Attribute 3 name': 'Brand Piesa',
                        'Attribute 3 value(s)': pa_brand_piesa,
                        'Attribute 3 visible': '1',
                        'Attribute 3 global': '1',
                        # ATRIBUT 4: Tehnologie
                        'Attribute 4 name': 'Tehnologie',
                        'Attribute 4 value(s)': pa_tehnologie,
                        'Attribute 4 visible': '1',
                        'Attribute 4 global': '1',
                        # ACF META
                        'meta:gtin_ean': ean_value,
                        'meta:sku_furnizor': sku_furnizor,
                        'meta:furnizor_activ': product.get('furnizor_activ', 'mobilesentrix'),
                        'meta:pret_achizitie': f"{price_eur:.2f}",
                        'meta:locatie_stoc': product.get('locatie_stoc', 'depozit_central'),
                        'meta:garantie_luni': warranty_months,
                        'meta:coduri_compatibilitate': product.get('coduri_compatibilitate', ''),
                        'meta:ic_movable': product.get('ic_movable', 'false'),
                        'meta:truetone_support': product.get('truetone_support', 'false'),
                        # SEO RANK MATH
                        'meta:rank_math_title': seo_title[:60],
                        'meta:rank_math_description': seo_description[:160],
                        'meta:rank_math_focus_keyword': seo_keyword,
                    }
                    writer.writerow(row)

            self.log(f"✓ CSV WebGSM creat cu succes: {csv_path}", "SUCCESS")
            self.log(f"   📊 Total produse exportate: {len(products_data)}", "INFO")
            self.log(f"   📋 Coloane CSV: {len(fieldnames)} (atribute + ACF + SEO)", "INFO")
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

                # Pregătește URL-urile (absolut + fără thumbnail)
                prepared_urls = []
                for img_url in list(img_urls)[:10]:  # Max 10 imagini
                    if img_url.startswith('/'):
                        img_url = 'https://www.mobilesentrix.eu' + img_url
                    elif not img_url.startswith('http'):
                        img_url = 'https://www.mobilesentrix.eu/' + img_url
                    img_url = img_url.replace('/thumbnail/', '/image/').replace('/small_image/', '/image/')
                    prepared_urls.append(img_url)

                # ⚡ DOWNLOAD PARALEL - 4 imagini simultan (de la ~30s la ~8s)
                from concurrent.futures import ThreadPoolExecutor, as_completed

                def _download_one_image(args):
                    """Descarcă și optimizează o imagine (rulează în thread separat)."""
                    idx, url = args
                    try:
                        img_response = requests.get(url, headers=headers, timeout=15)
                        img_response.raise_for_status()

                        img = Image.open(BytesIO(img_response.content))

                        # 🔧 Optimizare: resize la max 1200x1200 (reduce upload time cu 60-70%)
                        max_size = (1200, 1200)
                        if img.width > max_size[0] or img.height > max_size[1]:
                            img.thumbnail(max_size, Image.Resampling.LANCZOS)

                        # 🖼️ Detectează transparență (canal alpha) - NU converti la JPEG!
                        has_transparency = img.mode in ('RGBA', 'LA') or \
                                          (img.mode == 'P' and 'transparency' in img.info)

                        if has_transparency:
                            # Păstrează transparența → salvează ca WebP (suportă alpha, fișier mic)
                            if img.mode in ('P', 'LA'):
                                img = img.convert('RGBA')
                            img_extension = 'webp'
                            img_filename = f"{product_id}_{idx}.{img_extension}"
                            img_path = Path("images") / img_filename
                            img.save(img_path, 'WEBP', quality=90)
                        else:
                            # Fără transparență → JPEG (cel mai mic)
                            if img.mode in ('RGBA', 'P', 'LA'):
                                img = img.convert('RGB')
                            img_extension = 'jpg'
                            img_filename = f"{product_id}_{idx}.{img_extension}"
                            img_path = Path("images") / img_filename
                            img.save(img_path, 'JPEG', quality=85, optimize=True)
                        file_size = img_path.stat().st_size / (1024 * 1024)

                        return {
                            'success': True,
                            'idx': idx,
                            'src': url,
                            'local_path': str(img_path),
                            'name': img_filename,
                            'size': f"{file_size:.2f} MB"
                        }
                    except Exception as e:
                        return {'success': False, 'idx': idx, 'error': str(e)}

                # Lansează download-urile în paralel (4 thread-uri)
                download_tasks = [(idx, url) for idx, url in enumerate(prepared_urls, 1)]

                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = {executor.submit(_download_one_image, task): task for task in download_tasks}

                    for future in as_completed(futures):
                        result = future.result()
                        if result['success']:
                            images_data.append({
                                'src': result['src'],
                                'local_path': result['local_path'],
                                'name': result['name'],
                                'size': result['size']
                            })
                            self.log(f"      📷 [{result['idx']}] ✓ {result['name']} ({result['size']})", "SUCCESS")
                        else:
                            self.log(f"      ⚠️ [{result['idx']}] Eroare: {result['error']}", "WARNING")

                # Sortează imaginile după index (ordinea corectă)
                images_data.sort(key=lambda x: x['name'])

                self.log(f"   ✓ Total imagini descărcate: {len(images_data)} (paralel, optimizate)", "SUCCESS")
            
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

            # 🔢 EXTRAGE EAN REAL (COD DE BARE 8-14 CIFRE) DE PE PAGINA MOBILESENTRIX
            extracted_ean = ''
            try:
                import re, json

                # 1. JSON-LD structured data: "gtin13", "gtin", "gtin14", "ean"
                json_ld_scripts = product_soup.find_all('script', type='application/ld+json')
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict):
                            for ean_key in ['gtin13', 'gtin', 'gtin14', 'gtin12', 'gtin8', 'ean', 'mpn']:
                                val = data.get(ean_key, '')
                                if val and re.match(r'^\d{8,14}$', str(val)):
                                    extracted_ean = str(val)
                                    self.log(f"   ✓ EAN extras din JSON-LD ({ean_key}): {extracted_ean}", "SUCCESS")
                                    break
                            # Caută și în offers
                            if not extracted_ean and 'offers' in data:
                                offers = data['offers']
                                if isinstance(offers, dict):
                                    offers = [offers]
                                if isinstance(offers, list):
                                    for offer in offers:
                                        for ean_key in ['gtin13', 'gtin', 'sku']:
                                            val = offer.get(ean_key, '')
                                            if val and re.match(r'^\d{8,14}$', str(val)):
                                                extracted_ean = str(val)
                                                self.log(f"   ✓ EAN extras din JSON-LD offers ({ean_key}): {extracted_ean}", "SUCCESS")
                                                break
                                        if extracted_ean:
                                            break
                        if extracted_ean:
                            break
                    except:
                        pass

                # 2. HTML: meta itemprop="gtin13", "gtin", "ean"
                if not extracted_ean:
                    for prop in ['gtin13', 'gtin', 'gtin14', 'gtin8', 'ean', 'mpn']:
                        meta_elem = product_soup.find(attrs={'itemprop': prop})
                        if meta_elem:
                            val = meta_elem.get('content', '') or meta_elem.get_text(strip=True)
                            if val and re.match(r'^\d{8,14}$', str(val)):
                                extracted_ean = str(val)
                                self.log(f"   ✓ EAN extras din HTML itemprop ({prop}): {extracted_ean}", "SUCCESS")
                                break

                # 3. HTML: text vizibil pe pagină "EAN:", "Barcode:", "UPC:"
                if not extracted_ean:
                    page_text = product_soup.get_text()
                    ean_text_match = re.search(
                        r'(?:EAN|Barcode|UPC|GTIN|ISBN)[\s:]*(\d{8,14})',
                        page_text, re.IGNORECASE
                    )
                    if ean_text_match:
                        extracted_ean = ean_text_match.group(1)
                        self.log(f"   ✓ EAN extras din text pagină: {extracted_ean}", "SUCCESS")

                # 4. JavaScript: "ean":"0195949043505" sau barcode/gtin
                if not extracted_ean:
                    js_ean_match = re.search(
                        r'["\'](?:ean|barcode|gtin|gtin13|upc)["\'][\s:]*["\'](\d{8,14})["\']',
                        product_page_html, re.IGNORECASE
                    )
                    if js_ean_match:
                        extracted_ean = js_ean_match.group(1)
                        self.log(f"   ✓ EAN extras din JavaScript: {extracted_ean}", "SUCCESS")

                # 5. Fallback: dacă input-ul original e EAN (8-14 cifre), folosim asta
                if not extracted_ean and re.match(r'^\d{8,14}$', ean.strip()):
                    extracted_ean = ean.strip()
                    self.log(f"   ℹ️ EAN: folosit input-ul original ca EAN: {extracted_ean}", "INFO")

                if not extracted_ean:
                    self.log(f"   ⚠️ Nu am găsit EAN (cod de bare) pe pagina produsului", "WARNING")

            except Exception as ean_error:
                self.log(f"   ⚠️ Eroare extragere EAN: {ean_error}", "WARNING")
            
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

            # ===== WEBGSM: Extrage atribute, categorie slug, coduri, features =====
            attributes = self.extract_product_attributes(product_name, description, product_link or '')
            category_slug = self.get_webgsm_category(product_name)
            compat_codes = self.extract_compatibility_codes(description)
            screen_features = self.detect_screen_features(product_name, description)

            self.log(f"   📋 Atribute WebGSM:", "INFO")
            self.log(f"      Model: {attributes['pa_model']}", "INFO")
            self.log(f"      Calitate: {attributes['pa_calitate']}", "INFO")
            self.log(f"      Brand piesa: {attributes['pa_brand_piesa']}", "INFO")
            self.log(f"      Tehnologie: {attributes['pa_tehnologie']}", "INFO")
            self.log(f"      Categorie slug: {category_slug}", "INFO")
            if compat_codes:
                self.log(f"      Coduri compatibilitate: {compat_codes}", "INFO")
            if screen_features['ic_movable'] == 'true':
                self.log(f"      IC Movable: DA", "INFO")
            if screen_features['truetone_support'] == 'true':
                self.log(f"      TrueTone: DA", "INFO")

            product_data = {
                'ean': ean if not ean.startswith('http') else product_link,
                'ean_real': extracted_ean,  # EAN cod de bare real (8-14 cifre)
                'sku': generated_sku,  # SKU intern MobileSentrix (ex: 230473)
                'sku_furnizor': extracted_sku or generated_sku,  # SKU furnizor (ex: 107182127516)
                'name': product_name,
                'price': price,
                'description': description,
                'stock': '100',
                'brand': brand,
                'tags': ', '.join(tags),
                'category_path': category_path,
                'images': images_data,
                # WebGSM fields
                'pa_model': attributes['pa_model'],
                'pa_calitate': attributes['pa_calitate'],
                'pa_brand_piesa': attributes['pa_brand_piesa'],
                'pa_tehnologie': attributes['pa_tehnologie'],
                'category_slug': category_slug,
                'coduri_compatibilitate': compat_codes,
                'ic_movable': screen_features['ic_movable'],
                'truetone_support': screen_features['truetone_support'],
                'furnizor_activ': 'mobilesentrix',
                'pret_achizitie_eur': price,
                'locatie_stoc': 'depozit_central',
            }

            self.log(f"   ✓ Date extrase cu succes! (format WebGSM)", "SUCCESS")

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
                timeout=30  # ⚡ Redus de la 60s (imaginile sunt deja optimizate, <1.5MB)
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
