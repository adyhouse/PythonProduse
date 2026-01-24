#!/usr/bin/env python3
"""
Extractor avec Selenium - Pentru site-uri cu Cloudflare/JavaScript
Extrage link-urile de produse din categorii folosind Selenium (browser automat)

INSTALARE DEPENDINȚE:
  pip install selenium webdriver-manager beautifulsoup4

NOTA: Necesită Chrome/Firefox instalat
"""

import sys
import os

# Fix encoding for Windows
try:
    if sys.platform == 'win32':
        os.environ['PYTHONIOENCODING'] = 'utf-8'
except:
    pass

from pathlib import Path


def check_dependencies():
    """Verifica daca sunt instalate dependintele"""
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
        return True
    except ImportError as e:
        print(f"[!] Dependinte lipsesc: {e}")
        print("\nInstaleaza cu:")
        print("  pip install selenium webdriver-manager beautifulsoup4")
        return False


def extract_with_selenium(category_url, category_name, max_pages=5):
    """Extrage produse folosind Selenium"""
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    from bs4 import BeautifulSoup
    import time
    
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    
    # Uncomment pentru headless (fara fereastra)
    # options.add_argument("--headless")
    
    driver = None
    product_links = []
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        print(f"\n[*] Categoria: {category_name}")
        print(f"    URL: {category_url}")
        
        page = 1
        while page <= max_pages:
            # Construieste URL cu paginatie
            if '?' in category_url:
                page_url = f"{category_url}&page={page}"
            else:
                page_url = f"{category_url}?page={page}"
            
            print(f"    [*] Pagina {page}...", end='', flush=True)
            
            try:
                driver.get(page_url)
                
                # Asteapta sa se incarce elementele
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
                    )
                except:
                    pass  # Timeout, continua oricum
                
                time.sleep(2)  # Extra wait pentru JS rendering
                
                # Extrage HTML
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Cauta link-uri de produse
                all_links = soup.find_all('a', href=True)
                found_on_page = 0
                
                for link in all_links:
                    href = link['href']
                    
                    # Verifica daca e link de produs
                    if href.startswith('http'):
                        url = href
                    else:
                        from urllib.parse import urljoin
                        url = urljoin("https://www.mobilesentrix.eu", href)
                    
                    # Heuristic: e produs daca contin doar cateva segmente
                    from urllib.parse import urlparse
                    path = urlparse(url).path
                    segments = [s for s in path.split('/') if s]
                    
                    if len(segments) <= 3 and url not in product_links:
                        product_links.append(url)
                        found_on_page += 1
                
                print(f" {found_on_page} produse")
                
                if found_on_page == 0 and page > 1:
                    break
                
                page += 1
                
            except Exception as e:
                print(f" (Eroare: {e})")
                break
        
        print(f"    [+] Total: {len(product_links)} produse")
        return product_links
        
    except Exception as e:
        print(f"[!] Eroare: {e}")
        return []
        
    finally:
        if driver:
            driver.quit()


def main():
    if not check_dependencies():
        sys.exit(1)
    
    print("=" * 70)
    print("EXTRACTOR SELENIUM - MOBILESENTRIX")
    print("=" * 70)
    
    # Exemple de URL-uri
    categories = {
        "Apple - iPhone": "https://www.mobilesentrix.eu/accessories/apple-iphone/",
        "Apple - iPad": "https://www.mobilesentrix.eu/accessories/apple-ipad/",
        "Samsung - Galaxy S": "https://www.mobilesentrix.eu/accessories/samsung-galaxy-s/",
    }
    
    all_links = {}
    
    for category_name, category_url in categories.items():
        links = extract_with_selenium(category_url, category_name, max_pages=3)
        all_links[category_name] = links
    
    # Export
    print("\n[*] Export CSV...")
    with open('products_selenium.csv', 'w', newline='', encoding='utf-8') as f:
        import csv
        writer = csv.writer(f)
        writer.writerow(['Categoria', 'Link Produs'])
        
        for category, links in sorted(all_links.items()):
            for link in links:
                writer.writerow([category, link])
    
    print(f"[+] Fisier creat: products_selenium.csv")
    
    # Statistici
    total = sum(len(links) for links in all_links.values())
    print(f"\n[+] Total: {total} produse din {len(all_links)} categorii")


if __name__ == "__main__":
    main()
