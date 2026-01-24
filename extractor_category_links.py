#!/usr/bin/env python3
"""
Extractor Category Links
Extrage toate link-urile de produse din fiecare categorie de pe MobileSentrix.eu
Suportă paginație automată

NOTA: Pentru a funcționa complet, necesită una din următoarele:
1. Site-ul să nu fie protejat cu Cloudflare JavaScript
2. Selenium/Playwright pentru JavaScript rendering
3. Accesul la API-ul site-ului

Versiunea curentă: Suportă extracția manuală din CSV-uri sau URL-uri date
"""

import sys
import os

# Fix encoding for Windows
try:
    if sys.platform == 'win32':
        os.environ['PYTHONIOENCODING'] = 'utf-8'
except:
    pass

import requests
from bs4 import BeautifulSoup
from pathlib import Path
import csv
import time
import json
from urllib.parse import urljoin, urlparse
from collections import defaultdict
import re


class CategoryLinksExtractor:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.base_url = "https://www.mobilesentrix.eu"
        self.categories = defaultdict(list)  # {category_name: [product_links]}
        self.session = requests.Session()
        # Retry logic
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
    def extract_categories(self, main_page_url):
        """Extrage toate categoriile și subcategoriile dintr-o pagină"""
        print(f"[*] Descarcă pagina categorie: {main_page_url}")
        
        try:
            response = self.session.get(main_page_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Caută link-uri care ar putea fi subcategorii
            all_links = soup.find_all('a', href=True)
            subcategory_links = []
            
            for link in all_links:
                href = link['href']
                text = link.get_text().strip()
                
                # Filtreaza pentru subcategorii (iPhone, iPad, etc.)
                if href.startswith('http'):
                    url = href
                elif href.startswith('/'):
                    url = urljoin(self.base_url, href)
                else:
                    continue
                
                # Exclude anumite tipuri de link-uri
                if any(x in url.lower() for x in ['/contact', '/about', '/login', '/cart', '/search']):
                    continue
                
                # Verifica daca are structura de categorie
                if text and len(text) > 0 and len(text) < 100:
                    subcategory_links.append({
                        'name': text,
                        'url': url
                    })
            
            return subcategory_links
            
        except Exception as e:
            print(f"[!] Eroare descarcarea pagina: {e}")
            return []
    
    def extract_products_from_category(self, category_url, category_name, max_pages=5):
        """Extrage toate produsele dintr-o categorie cu paginație"""
        print(f"\n[*] Categorie: {category_name}")
        print(f"    URL: {category_url}")
        
        product_links = []
        page = 1
        
        while page <= max_pages:
            # Construiește URL cu paginație
            if '?' in category_url:
                page_url = f"{category_url}&page={page}"
            else:
                page_url = f"{category_url}?page={page}"
            
            print(f"    [*] Pagina {page}...", end='', flush=True)
            
            try:
                response = self.session.get(page_url, headers=self.headers, timeout=15)
                
                if response.status_code == 404:
                    print(f" (404 - stop)")
                    break
                
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Caută link-urile de produse
                # Structura standard: <a href="/product-name/">
                found_on_page = 0
                
                # Metoda 1: Caută în div-uri de produs
                product_divs = soup.find_all('div', class_=['product', 'product-item', 'product-card'])
                for div in product_divs:
                    link = div.find('a', href=True)
                    if link:
                        href = link['href']
                        text = link.get_text().strip()
                        
                        if href.startswith('http'):
                            url = href
                        else:
                            url = urljoin(self.base_url, href)
                        
                        if url not in product_links:
                            product_links.append(url)
                            found_on_page += 1
                
                # Metoda 2: Caută link-uri directe cu /product/ în path
                if found_on_page == 0:
                    all_links = soup.find_all('a', href=True)
                    for link in all_links:
                        href = link['href']
                        
                        if href.startswith('http'):
                            url = href
                        else:
                            url = urljoin(self.base_url, href)
                        
                        # Heuristic: link de produs dacă conține doar 1-2 niveluri și nu e categorie
                        path = urlparse(url).path
                        segments = [s for s in path.split('/') if s]
                        
                        if len(segments) <= 2 and segments and not any(x in path.lower() for x in ['category', 'brand', 'page', 'search', 'about']):
                            if url not in product_links:
                                product_links.append(url)
                                found_on_page += 1
                
                print(f" {found_on_page} produse")
                
                # Dacă pagina e goală, stop paginație
                if found_on_page == 0 and page > 1:
                    print(f"    [*] Paginație terminată (pagina goală)")
                    break
                
                page += 1
                time.sleep(1)  # Rate limit
                
            except Exception as e:
                print(f" (Eroare: {e})")
                break
        
        print(f"    [✓] Total produse găsite: {len(product_links)}")
        self.categories[category_name] = product_links
        return product_links
    
    def export_to_csv(self, output_file="category_links.csv"):
        """Exportă link-urile pe categorii în CSV"""
        print(f"\n[*] Exportă în CSV: {output_file}")
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Categoria', 'Link Produs'])
                
                total = 0
                for category, links in sorted(self.categories.items()):
                    for link in links:
                        writer.writerow([category, link])
                        total += 1
            
            print(f"[✓] Exportat: {total} link-uri în {output_file}")
            return True
            
        except Exception as e:
            print(f"[!] Eroare export: {e}")
            return False
    
    def export_to_json(self, output_file="category_links.json"):
        """Exportă link-urile în JSON"""
        print(f"\n[*] Exportă în JSON: {output_file}")
        
        try:
            data = {
                'extracted_at': str(Path(output_file).stat().st_mtime if Path(output_file).exists() else 'N/A'),
                'total_categories': len(self.categories),
                'total_products': sum(len(links) for links in self.categories.values()),
                'categories': {cat: links for cat, links in sorted(self.categories.items())}
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"[✓] Exportat JSON: {output_file}")
            return True
            
        except Exception as e:
            print(f"[!] Eroare export JSON: {e}")
            return False
    
    def run(self, category_urls):
        """
        Pornește extracția pentru o listă de URL-uri de categorii
        
        Args:
            category_urls: Dict cu {category_name: category_url}
        """
        print("=" * 70)
        print("EXTRACTOR LINK-URI CATEGORII MOBILESENTRIX")
        print("=" * 70)
        
        for category_name, category_url in category_urls.items():
            self.extract_products_from_category(category_url, category_name, max_pages=10)
        
        # Export
        self.export_to_csv()
        self.export_to_json()
        
        # Statistici
        print("\n" + "=" * 70)
        print("STATISTICI")
        print("=" * 70)
        for category, links in sorted(self.categories.items()):
            print(f"  {category}: {len(links)} produse")
        
        total_products = sum(len(links) for links in self.categories.values())
        print(f"\nTotal: {total_products} produse din {len(self.categories)} categorii")


def create_sample_config():
    """Creează un fișier de configurare cu URL-urile categoriilor"""
    config = """# Category Links Extractor Configuration
# Format: category_name | category_url

# Apple - Subcategorii
Apple - iPhone | https://www.mobilesentrix.eu/accessories/apple-iphone/
Apple - iPad | https://www.mobilesentrix.eu/accessories/apple-ipad/
Apple - Watch | https://www.mobilesentrix.eu/accessories/apple-watch/
Apple - MacBook | https://www.mobilesentrix.eu/accessories/apple-macbook/
Apple - AirPods | https://www.mobilesentrix.eu/accessories/apple-airpods/
Apple - iPod | https://www.mobilesentrix.eu/accessories/apple-ipod/

# Samsung - Subcategorii
Samsung - Galaxy S | https://www.mobilesentrix.eu/accessories/samsung-galaxy-s/
Samsung - Galaxy Note | https://www.mobilesentrix.eu/accessories/samsung-galaxy-note/
Samsung - Galaxy A | https://www.mobilesentrix.eu/accessories/samsung-galaxy-a/
Samsung - Galaxy Z | https://www.mobilesentrix.eu/accessories/samsung-galaxy-z/
Samsung - Galaxy Tab | https://www.mobilesentrix.eu/accessories/samsung-galaxy-tab/

# Motorola
Motorola | https://www.mobilesentrix.eu/accessories/motorola/

# Google
Google Pixel | https://www.mobilesentrix.eu/accessories/google-pixel/

# Huawei
Huawei | https://www.mobilesentrix.eu/accessories/huawei/

# OnePlus
OnePlus | https://www.mobilesentrix.eu/accessories/oneplus/

# Xiaomi
Xiaomi | https://www.mobilesentrix.eu/accessories/xiaomi/

# Sony
Sony | https://www.mobilesentrix.eu/accessories/sony/

# LG
LG | https://www.mobilesentrix.eu/accessories/lg/
"""
    
    config_path = Path("category_config.txt")
    config_path.write_text(config, encoding='utf-8')
    print(f"[+] Config creat: {config_path}")
    return str(config_path)


def load_config_from_file(config_file):
    """Încarcă configurația din fișier"""
    try:
        config_path = Path(config_file)
        if not config_path.exists():
            print(f"[!] Fișier config nu găsit: {config_file}")
            return {}
        
        category_urls = {}
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) == 2:
                        category_name = parts[0].strip()
                        category_url = parts[1].strip()
                        category_urls[category_name] = category_url
        
        print(f"[+] Config încărcat: {len(category_urls)} categorii")
        return category_urls
        
    except Exception as e:
        print(f"[!] Eroare citire config: {e}")
        return {}


def main():
    print("=" * 70)
    print("EXTRACTOR LINK-URI CATEGORII MOBILESENTRIX")
    print("=" * 70)
    
    import sys
    
    # Verifica dacă s-a pasat fișier de config
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = "category_config.txt"
    
    # Dacă nu există, creează config de exemplu
    if not Path(config_file).exists():
        print("\n[!] Fișier config nu găsit. Creez example...")
        config_file = create_sample_config()
        print(f"[*] Editează {config_file} cu categoriile dorite, apoi rulează din nou")
        return
    
    # Încarcă configurația
    category_urls = load_config_from_file(config_file)
    
    if not category_urls:
        print("[!] Nu s-au putut încărca categorii")
        return
    
    # Porneste extracția
    extractor = CategoryLinksExtractor()
    
    try:
        extractor.run(category_urls)
    except KeyboardInterrupt:
        print("\n\n[!] Utilizator a întrerupt procesul")
    except Exception as e:
        print(f"\n[!] Eroare: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
