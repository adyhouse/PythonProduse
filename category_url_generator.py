#!/usr/bin/env python3
"""
Category URL Generator
Generează URL-uri pe baza categor anilor cu pattern-uri comune

Util pentru:
1. Obținerea rapidă a URL-urilor categoriilor
2. Testarea URL-urilor pentru a vedea care sunt valide
3. Generarea de noi URL-uri pe baza pattern-urilor
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
from pathlib import Path
import time


def test_url(url, headers=None):
    """Testează dacă o URL este validă (răspunde cu 200)"""
    if headers is None:
        headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
        return response.status_code == 200
    except:
        return False


def generate_category_urls():
    """Generează URL-uri pentru categorii comune pe MobileSentrix"""
    
    base = "https://www.mobilesentrix.eu/accessories"
    
    # Categorii de generat
    categories_patterns = [
        # Apple
        ("Apple - iPhone", ["apple-iphone", "iphone"]),
        ("Apple - iPad", ["apple-ipad", "ipad"]),
        ("Apple - Watch", ["apple-watch", "apple watch", "watch"]),
        ("Apple - AirPods", ["apple-airpods", "airpods"]),
        ("Apple - MacBook", ["apple-macbook", "macbook"]),
        ("Apple - iPod", ["apple-ipod", "ipod"]),
        
        # Samsung
        ("Samsung - Galaxy S", ["samsung-galaxy-s", "galaxy-s"]),
        ("Samsung - Galaxy Note", ["samsung-galaxy-note", "galaxy-note"]),
        ("Samsung - Galaxy A", ["samsung-galaxy-a", "galaxy-a"]),
        ("Samsung - Galaxy Z", ["samsung-galaxy-z", "galaxy-z"]),
        ("Samsung - Galaxy Tab", ["samsung-galaxy-tab", "galaxy-tab"]),
        
        # Motorola
        ("Motorola - Razr", ["motorola-razr", "motorola razr"]),
        ("Motorola - Edge", ["motorola-edge", "motorola edge"]),
        ("Motorola - Moto G", ["motorola-moto-g", "moto-g"]),
        
        # Google
        ("Google - Pixel", ["google-pixel", "pixel"]),
        ("Google - Pixel Fold", ["google-pixel-fold", "pixel-fold"]),
        
        # Huawei
        ("Huawei - P Series", ["huawei-p", "huawei p"]),
        ("Huawei - Mate", ["huawei-mate", "huawei mate"]),
        
        # OnePlus
        ("OnePlus", ["oneplus"]),
        
        # Xiaomi
        ("Xiaomi", ["xiaomi"]),
        
        # Sony
        ("Sony - Xperia", ["sony-xperia", "xperia"]),
        
        # Nokia
        ("Nokia", ["nokia"]),
        
        # Oppo
        ("Oppo", ["oppo"]),
        
        # Vivo
        ("Vivo", ["vivo"]),
        
        # Realme
        ("Realme", ["realme"]),
    ]
    
    print("=" * 70)
    print("CATEGORY URL GENERATOR - MOBILESENTRIX")
    print("=" * 70)
    print("\nTestez URL-uri de categorii...\n")
    
    valid_urls = {}
    
    for category_name, patterns in categories_patterns:
        found = False
        
        for pattern in patterns:
            url = f"{base}/{pattern}/"
            
            # Variații
            urls_to_test = [
                url,
                f"{base}/{pattern}",
                url.replace('-', '_'),
                url.replace('-', '%20').replace(' ', '-'),
            ]
            
            for test_url_str in urls_to_test:
                if test_url(test_url_str):
                    print(f"  [OK] {category_name:30} -> {test_url_str}")
                    valid_urls[category_name] = test_url_str
                    found = True
                    break
            
            if found:
                break
            
            time.sleep(0.3)  # Rate limit
        
        if not found:
            print(f"  [--] {category_name:30} -> Niciun URL valid")
    
    # Export
    print("\n" + "=" * 70)
    print("GENERARE CONFIG FILE")
    print("=" * 70)
    
    config_content = "# Auto-generated category URLs\n"
    config_content += "# Format: category_name | category_url\n\n"
    
    for category, url in sorted(valid_urls.items()):
        config_content += f"{category} | {url}\n"
    
    # Scrie config file
    config_path = Path("category_config_auto.txt")
    config_path.write_text(config_content, encoding='utf-8')
    
    print(f"\n[+] Config generat: {config_path}")
    print(f"[+] URL-uri valide: {len(valid_urls)}")
    
    # Copiază ca nou config dacă nu există altul
    if not Path("category_config.txt").exists():
        import shutil
        shutil.copy(config_path, "category_config.txt")
        print(f"[+] Copiat ca: category_config.txt")
    
    return valid_urls


def main():
    valid_urls = generate_category_urls()
    
    print("\n" + "=" * 70)
    print("INSTRUCȚIUNI URMĂTOARE")
    print("=" * 70)
    print("""
1. Editează category_config.txt și adaugă alte categorii dacă trebuie
2. Rulează: python extractor_category_links.py
3. După extract, fișierele CSV sunt gata pentru import_gui.py
""")


if __name__ == "__main__":
    main()
