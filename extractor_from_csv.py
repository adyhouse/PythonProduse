#!/usr/bin/env python3
"""
Extractor From CSV
Extrage linkuri de produse dintr-un CSV existent și le organizeaza pe categorii

Util pentru:
1. Daca ai deja o lista de linkuri de produse
2. Vrei sa le clasifici pe categorii
3. Vrei sa le exporti intr-un format structurat
"""

import sys
import os

# Fix encoding for Windows
try:
    if sys.platform == 'win32':
        os.environ['PYTHONIOENCODING'] = 'utf-8'
except:
    pass

import csv
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse
import json


class CSVCategoryOrganizer:
    def __init__(self):
        self.categories = defaultdict(list)
        self.all_products = []
        
    def extract_category_from_url(self, url):
        """Extrage categoria din URL"""
        path = urlparse(url).path.lower()
        
        # Heuristic: cauta cuvinte cheie in URL
        categories_map = {
            'iphone': 'Apple - iPhone',
            'ipad': 'Apple - iPad',
            'apple-watch': 'Apple - Watch',
            'watch': 'Apple - Watch',
            'airpods': 'Apple - AirPods',
            'macbook': 'Apple - MacBook',
            'ipod': 'Apple - iPod',
            'galaxy-s': 'Samsung - Galaxy S',
            'galaxy-note': 'Samsung - Galaxy Note',
            'galaxy-a': 'Samsung - Galaxy A',
            'galaxy-z': 'Samsung - Galaxy Z',
            'galaxy-tab': 'Samsung - Galaxy Tab',
            'motorola': 'Motorola',
            'pixel': 'Google Pixel',
            'huawei': 'Huawei',
            'oneplus': 'OnePlus',
            'xiaomi': 'Xiaomi',
            'sony': 'Sony',
            'nokia': 'Nokia',
            'honor': 'Honor',
        }
        
        for keyword, category in categories_map.items():
            if keyword in path:
                return category
        
        # Fallback: extrage din URL
        segments = [s for s in path.split('/') if s]
        if segments:
            return segments[-1].replace('-', ' ').title()
        
        return "Uncategorized"
    
    def load_from_csv(self, csv_file):
        """Încarcă produse din CSV"""
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Verifica coloane
                if not reader.fieldnames:
                    print(f"[!] CSV fără header")
                    return False
                
                # Cauta coloana cu link-uri
                link_column = None
                for col in ['Link', 'URL', 'link', 'url', 'Product Link', 'product_link']:
                    if col in reader.fieldnames:
                        link_column = col
                        break
                
                if not link_column:
                    print(f"[!] Coloana link nu găsită. Coloane disponibile: {reader.fieldnames}")
                    return False
                
                count = 0
                for row in reader:
                    link = row.get(link_column, '').strip()
                    if link and link.startswith('http'):
                        category = self.extract_category_from_url(link)
                        self.categories[category].append(link)
                        self.all_products.append({
                            'url': link,
                            'category': category,
                            'raw_data': row
                        })
                        count += 1
                
                print(f"[+] Încarcate {count} produse din {csv_file}")
                return True
                
        except Exception as e:
            print(f"[!] Eroare citire CSV: {e}")
            return False
    
    def load_from_text_file(self, text_file):
        """Încarcă link-uri dintr-un fișier text (un link per linie)"""
        try:
            with open(text_file, 'r', encoding='utf-8') as f:
                count = 0
                for line in f:
                    link = line.strip()
                    if link and link.startswith('http'):
                        category = self.extract_category_from_url(link)
                        self.categories[category].append(link)
                        self.all_products.append({
                            'url': link,
                            'category': category
                        })
                        count += 1
                
                print(f"[+] Incarcate {count} link-uri din {text_file}")
                return True
                
        except Exception as e:
            print(f"[!] Eroare citire fisier: {e}")
            return False
    
    def export_to_csv(self, output_file="products_by_category.csv"):
        """Exporta link-urile organizate pe categorii"""
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Categoria', 'Link Produs'])
                
                for category in sorted(self.categories.keys()):
                    for link in self.categories[category]:
                        writer.writerow([category, link])
            
            print(f"[+] CSV creat: {output_file} ({len(self.all_products)} linkuri)")
            return True
            
        except Exception as e:
            print(f"[!] Eroare export CSV: {e}")
            return False
    
    def export_to_json(self, output_file="products_by_category.json"):
        """Exporta in JSON"""
        try:
            data = {
                'total_products': len(self.all_products),
                'total_categories': len(self.categories),
                'categories': {
                    cat: {
                        'count': len(links),
                        'links': links
                    }
                    for cat, links in sorted(self.categories.items())
                }
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"[+] JSON creat: {output_file}")
            return True
            
        except Exception as e:
            print(f"[!] Eroare export JSON: {e}")
            return False
    
    def print_statistics(self):
        """Afiseaza statistici"""
        print("\n" + "=" * 70)
        print("STATISTICI")
        print("=" * 70)
        
        for category in sorted(self.categories.keys()):
            count = len(self.categories[category])
            print(f"  {category:40} {count:4} produse")
        
        print(f"\n  {'Total':40} {len(self.all_products):4} produse din {len(self.categories)} categorii")
    
    def process(self, input_file):
        """Procesa fisierul de input"""
        input_path = Path(input_file)
        
        if not input_path.exists():
            print(f"[!] Fisier nu gasit: {input_file}")
            return False
        
        # Determina tipul de fisier
        if input_path.suffix.lower() == '.csv':
            success = self.load_from_csv(input_file)
        else:
            # Treat as text file
            success = self.load_from_text_file(input_file)
        
        if not success:
            return False
        
        # Export
        self.export_to_csv()
        self.export_to_json()
        
        # Statistici
        self.print_statistics()
        
        return True


def main():
    import sys
    
    print("=" * 70)
    print("CSV CATEGORY ORGANIZER - MOBILESENTRIX")
    print("=" * 70)
    
    if len(sys.argv) < 2:
        print("\nUsage: python extractor_from_csv.py <input_file>")
        print("\nExemple:")
        print("  python extractor_from_csv.py produse.csv")
        print("  python extractor_from_csv.py sku_list.txt")
        return
    
    input_file = sys.argv[1]
    
    organizer = CSVCategoryOrganizer()
    organizer.process(input_file)


if __name__ == "__main__":
    main()
