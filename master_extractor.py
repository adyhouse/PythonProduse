#!/usr/bin/env python3
"""
MASTER EXTRACTOR - Interfață unificată pentru extracția link-urilor pe categorii

Meniu principal care te ajută să:
1. Generezi URL-urile categoriilor (cu validare)
2. Extragi link-urile din categorii
3. Organizezi link-uri existente
4. Exportezi în format standard
5. Integrezi cu import_gui.py
"""

import os
import sys
from pathlib import Path
import csv
import json
from collections import defaultdict

# Fix encoding for Windows - use PYTHONIOENCODING instead
try:
    if sys.platform == 'win32':
        # Don't reconfigure - let Python handle it
        os.environ['PYTHONIOENCODING'] = 'utf-8'
except:
    pass


def clear_screen():
    """Clear console screen"""
    os.system('clear' if os.name == 'posix' else 'cls')


def safe_input(prompt=""):
    """Safe input that handles EOF"""
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        return ""


def print_header():
    """Print application header"""
    clear_screen()
    print("=" * 70)
    print(" " * 15 + "MASTER EXTRACTOR - MOBILESENTRIX")
    print(" " * 10 + "Extrage link-uri pe categorii din MobileSentrix.eu")
    print("=" * 70)


def print_menu():
    """Print main menu"""
    print("\nAlege o opțiune:\n")
    print("  1. Generează URL-uri de categorii (cu test)")
    print("  2. Extrage link-uri din categorii (cu paginație)")
    print("  3. Organizează link-uri din CSV/text existent")
    print("  4. Vizualizează link-uri deja extrase")
    print("  5. Exportă pentru import_gui.py")
    print("  6. Deschide GHID complet")
    print("  0. Ieșire")
    print("\n" + "-" * 70)


def option_1_generate_urls():
    """Generate category URLs"""
    print_header()
    print("\n[*] Generez URL-urile categoriilor...\n")
    
    # Import and run the generator
    try:
        from category_url_generator import generate_category_urls
        valid_urls = generate_category_urls()
        
        input("\n[+] Gata! Apasă Enter pentru a continua...")
        return True
    except Exception as e:
        print(f"[!] Eroare: {e}")
        input("Apasă Enter...")
        return False


def option_2_extract_links():
    """Extract links from categories"""
    print_header()
    print("\n[*] Extragi link-uri din categorii...\n")
    
    # Check if config exists
    config_path = Path("category_config.txt")
    if not config_path.exists():
        print("[!] Fișier category_config.txt nu găsit!")
        print("    Rulează opțiunea 1 mai întâi pentru a genera URL-uri")
        input("Apasă Enter...")
        return False
    
    try:
        from extractor_category_links import CategoryLinksExtractor
        
        # Load config
        extractor = CategoryLinksExtractor()
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
        
        if not category_urls:
            print("[!] Nu s-au putut încărca categorii din config")
            input("Apasă Enter...")
            return False
        
        print(f"[*] Categorii de extras: {len(category_urls)}\n")
        
        # Run extraction
        extractor.run(category_urls)
        
        input("\n[+] Gata! Apasă Enter pentru a continua...")
        return True
        
    except Exception as e:
        print(f"[!] Eroare: {e}")
        import traceback
        traceback.print_exc()
        input("Apasă Enter...")
        return False


def option_3_organize_links():
    """Organize links from existing CSV/text"""
    print_header()
    print("\n[*] Organizez link-uri din CSV/text existent...\n")
    
    # Find files
    print("Fișiere disponibile:")
    files = list(Path(".").glob("*.csv")) + list(Path(".").glob("*.txt"))
    csv_files = [f for f in files if f.suffix.lower() in ['.csv', '.txt']]
    
    if not csv_files:
        print("[!] Niciun fișier CSV/TXT găsit")
        input("Apasă Enter...")
        return False
    
    for i, f in enumerate(csv_files[:10], 1):
        print(f"  {i}. {f.name}")
    
    try:
        choice = input("\nAlege fișier (nr): ").strip()
        file_idx = int(choice) - 1
        if 0 <= file_idx < len(csv_files):
            selected_file = csv_files[file_idx]
            print(f"\n[*] Proceseaza: {selected_file.name}...\n")
            
            from extractor_from_csv import CSVCategoryOrganizer
            organizer = CSVCategoryOrganizer()
            organizer.process(str(selected_file))
            
            input("\n[+] Gata! Apasă Enter pentru a continua...")
            return True
        else:
            print("[!] Alegere invalidă")
            input("Apasă Enter...")
            return False
    except ValueError:
        print("[!] Alegere invalidă")
        input("Apasă Enter...")
        return False
    except Exception as e:
        print(f"[!] Eroare: {e}")
        input("Apasă Enter...")
        return False


def option_4_view_links():
    """View already extracted links"""
    print_header()
    print("\n[*] Vizualizez link-uri extrase...\n")
    
    csv_files = [
        Path("category_links.csv"),
        Path("products_by_category.csv"),
    ]
    
    for csv_file in csv_files:
        if csv_file.exists():
            print(f"\nFișier: {csv_file.name}")
            print("-" * 70)
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                categories = defaultdict(int)
                for row in reader:
                    if 'Categoria' in row:
                        categories[row['Categoria']] += 1
                
                for category in sorted(categories.keys()):
                    print(f"  {category:40} {categories[category]:4} link-uri")
                
                print(f"\n  Total: {sum(categories.values())} link-uri din {len(categories)} categorii")
    
    input("\nApasă Enter pentru a continua...")
    return True


def option_5_export_for_import():
    """Export for import_gui.py"""
    print_header()
    print("\n[*] Export pentru import_gui.py...\n")
    
    # Check CSV files
    csv_files = [
        Path("category_links.csv"),
        Path("products_by_category.csv"),
    ]
    
    valid_file = None
    for csv_file in csv_files:
        if csv_file.exists():
            valid_file = csv_file
            break
    
    if not valid_file:
        print("[!] Niciun fișier CSV cu link-uri nu găsit")
        print("    Rulează opțiunea 2 sau 3 mai întâi")
        input("Apasă Enter...")
        return False
    
    try:
        print(f"[*] Citesc link-uri din: {valid_file.name}\n")
        
        # Read links
        links = []
        with open(valid_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'Link Produs' in row:
                    link = row['Link Produs'].strip()
                    if link and link.startswith('http'):
                        links.append(link)
        
        if not links:
            print("[!] Niciun link valid gasit")
            input("Apasă Enter...")
            return False
        
        # Export to sku_list.txt
        sku_list = Path("sku_list.txt")
        
        # Read existing content (preserve comments)
        existing_lines = []
        if sku_list.exists():
            with open(sku_list, 'r', encoding='utf-8') as f:
                existing_lines = [line for line in f.readlines() if line.strip().startswith('#')]
        
        # Write new file
        with open(sku_list, 'w', encoding='utf-8') as f:
            # Write header if needed
            if not existing_lines:
                f.write("# Lista LINK-URI pentru import\n")
                f.write("# Generat de: master_extractor.py\n\n")
            else:
                f.writelines(existing_lines[:5])
                f.write("\n# Link-uri de produse:\n")
            
            for link in links:
                f.write(f"{link}\n")
        
        print(f"[+] Exportat {len(links)} link-uri în: sku_list.txt")
        print("\n[*] Următorii pași:")
        print("  1. Rulează: python import_gui.py")
        print("  2. Click 'Importa' pentru a descărca produsele")
        print("  3. Fișier export_produse.csv va fi creat cu categorii + imagini")
        
        input("\nApasă Enter pentru a continua...")
        return True
        
    except Exception as e:
        print(f"[!] Eroare: {e}")
        input("Apasă Enter...")
        return False


def option_6_open_guide():
    """Open guide file"""
    print_header()
    print("\n[*] Ghid complet disponibil în: GHID_EXTRACTOARE.txt\n")
    
    guide_file = Path("GHID_EXTRACTOARE.txt")
    if guide_file.exists():
        with open(guide_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Show first part
        lines = content.split('\n')
        for line in lines[:40]:
            print(line)
        
        print("\n... (continuare în fisierul GHID_EXTRACTOARE.txt)\n")
    
    input("Apasă Enter pentru a continua...")
    return True


def main():
    """Main menu loop"""
    while True:
        print_header()
        print_menu()
        
        try:
            choice = input("Alegeți (0-6): ").strip()
            
            if choice == '0':
                print("\n[*] Mulțumesc! La revedere!\n")
                break
            elif choice == '1':
                option_1_generate_urls()
            elif choice == '2':
                option_2_extract_links()
            elif choice == '3':
                option_3_organize_links()
            elif choice == '4':
                option_4_view_links()
            elif choice == '5':
                option_5_export_for_import()
            elif choice == '6':
                option_6_open_guide()
            else:
                print("[!] Alegere invalidă")
                input("Apasă Enter...")
                
        except KeyboardInterrupt:
            print("\n\n[*] Întrerupt de utilizator")
            break
        except Exception as e:
            print(f"\n[!] Eroare: {e}")
            input("Apasă Enter...")


if __name__ == "__main__":
    main()
