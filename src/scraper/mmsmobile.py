"""
Scraper MMS Mobile (mmsmobile.de). Odoo-based.
Prețuri necesită login (exportăm 0 dacă nu sunt vizibile). SKU/EAN din tabele.
"""
import re
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper


class MmsmobileScraper(BaseScraper):
    def _headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self.config.get("headers", {}).get(
                "User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": self.config.get("headers", {}).get(
                "Accept-Language", "en-US,en;q=0.9,de;q=0.8"
            ),
            "Referer": self.config.get("base_url", "https://www.mmsmobile.de") + "/",
        }

    def _find_product_url(self, sku_or_query: str) -> Optional[str]:
        base_url = self.config.get("base_url", "https://www.mmsmobile.de").rstrip("/")
        lang = self.config.get("default_language", "en")
        search_url = f"{base_url}/{lang}/shop?search={requests.utils.quote(sku_or_query)}"
        self.log(f"   🔍 Căutare: {search_url}", "INFO")
        try:
            # Folosește session dacă există (după login), altfel requests normal
            if self.session:
                r = self.session.get(search_url, headers=self._headers(), timeout=30)
            else:
                r = requests.get(search_url, headers=self._headers(), timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "html.parser")
            for a in soup.select('a[href*="/shop/"]'):
                href = (a.get("href") or "").strip()
                if href and "/shop/" in href and href.count("-") >= 1:
                    if not href.startswith("http"):
                        href = base_url + href if href.startswith("/") else base_url + "/" + href
                    if "search" not in href:
                        self.log(f"   ✓ Produs găsit: {href[:80]}...", "INFO")
                        return href
        except Exception as e:
            self.log(f"   ✗ Căutare eșuată: {e}", "ERROR")
        return None

    def scrape_product(self, sku_or_url: str) -> Optional[Dict]:
        if not sku_or_url or not sku_or_url.strip():
            return None
        sku_or_url = sku_or_url.strip()
        base_url = self.config.get("base_url", "https://www.mmsmobile.de").rstrip("/")

        # Login dacă e necesar
        if not self._login_if_required():
            self.log("   ⚠️ Continuă fără login (conținutul poate fi limitat)", "WARNING")

        if sku_or_url.startswith("http://") or sku_or_url.startswith("https://"):
            product_url = sku_or_url
            self.log("   ✓ Link direct detectat", "INFO")
        else:
            product_url = self._find_product_url(sku_or_url)
            if not product_url:
                self.log("   ✗ Nu s-a găsit niciun produs.", "ERROR")
                return None

        try:
            # Folosește session dacă există (după login), altfel requests normal
            if self.session:
                r = self.session.get(product_url, headers=self._headers(), timeout=30)
            else:
                r = requests.get(product_url, headers=self._headers(), timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "html.parser")
            page_text = soup.get_text(separator="\n")
            # Salvează HTML pentru debugging
            self._save_debug_html(soup, product_url)
        except Exception as e:
            self.log(f"   ✗ Eroare descărcare: {e}", "ERROR")
            return None

        selectors = self.config.get("selectors", {})

        name = ""
        for sel in selectors.get("name", ["h1", ".product-title"]):
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                name = el.get_text(strip=True)
                break
        if not name:
            name = "Produs MMS Mobile"

        price = 0.0
        for sel in selectors.get("price", ["h4", ".price", "[class*='price']"]):
            el = soup.select_one(sel)
            if el:
                txt = el.get_text(strip=True)
                if "login" in txt.lower() or "register" in txt.lower():
                    continue
                m = re.search(r"[\d.,]+", txt.replace(",", "."))
                if m:
                    try:
                        price = float(m.group(0).replace(",", "."))
                    except ValueError:
                        pass
                    if price > 0:
                        break

        description = ""
        for sel in selectors.get("description", [
            "section[aria-labelledby*='description']",
            ".tab-content",
            ".product-description",
            "#description",
        ]):
            el = soup.select_one(sel)
            if el:
                description = el.get_text(separator="\n", strip=True)[:3000]
                if len(description) > 30:
                    break
        if not description:
            description = name

        sku_furnizor = self._table_value_by_header(soup, selectors.get("sku_table_header", "SKU"))
        ean_real = self._table_value_by_header(soup, selectors.get("ean_table_header", "EAN"))
        if not sku_furnizor:
            m = re.search(r"[\d]+", product_url.split("-")[-1])
            if m:
                sku_furnizor = m.group(0)
        if not sku_furnizor:
            sku_furnizor = re.sub(r"[^a-zA-Z0-9]", "", product_url[-40:]) or "MMS-unknown"

        img_urls = []
        if not self.skip_images:
            self.log("   🖼️ Descarc imagini MARI...", "INFO")
            # Găsește blocul produsului care conține SKU-ul SAU numele produsului
            product_block = None
            product_gallery = None  # Galeria specifică a produsului
            
            # 0. Încearcă să găsească galeria produsului direct (Odoo)
            gallery_selectors = [
                "[class*='product-image']",
                "[class*='product-gallery']",
                "[class*='o_product_image']",
                "[class*='product_images']",
                ".carousel",
                "[id*='product-image']",
                "[id*='product-gallery']",
            ]
            for gallery_sel in gallery_selectors:
                gallery_elem = soup.select_one(gallery_sel)
                if gallery_elem:
                    # Verifică că galeria conține SKU sau nume produs
                    gallery_text = gallery_elem.get_text()
                    if (sku_furnizor and sku_furnizor != "MMS-unknown" and sku_furnizor.upper() in gallery_text.upper()) or \
                       (name and any(word.upper() in gallery_text.upper() for word in name.split()[:3] if len(word) > 3)):
                        product_gallery = gallery_elem
                        self.log("   ✓ Galerie produs găsită", "INFO")
                        break
            
            # 1. Caută blocul care conține SKU-ul
            if sku_furnizor and sku_furnizor != "MMS-unknown":
                for elem in soup.find_all(string=re.compile(re.escape(sku_furnizor), re.I)):
                    parent = elem.find_parent(['main', 'article', 'div', 'section'])
                    if parent:
                        # Verifică că nu e din sidebar sau related
                        parent_class = ' '.join(parent.get('class', [])).lower()
                        parent_id = (parent.get('id') or '').lower()
                        if not any(x in parent_class + parent_id for x in ['sidebar', 'related', 'recommend', 'similar', 'also', 'other']):
                            product_block = parent
                            break
            
            # 2. Dacă nu găsește SKU, caută blocul care conține numele produsului
            if not product_block and name:
                name_words = [w for w in name.split() if len(w) > 3][:3]  # Primele 3 cuvinte importante
                for word in name_words:
                    for elem in soup.find_all(string=re.compile(re.escape(word), re.I)):
                        parent = elem.find_parent(['main', 'article', 'div', 'section'])
                        if parent:
                            # Verifică că nu e din sidebar sau related
                            parent_class = ' '.join(parent.get('class', [])).lower()
                            parent_id = (parent.get('id') or '').lower()
                            if not any(x in parent_class + parent_id for x in ['sidebar', 'related', 'recommend', 'similar', 'also', 'other']):
                                product_block = parent
                                break
                    if product_block:
                        break
            
            # 3. Fallback: blocuri comune de produs (Odoo)
            if not product_block:
                product_block = (
                    soup.select_one("main.o_main_content") or
                    soup.select_one("main") or
                    soup.select_one("[class*='product-detail']") or
                    soup.select_one(".product-detail") or
                    soup.select_one("#product-detail") or
                    soup.select_one("[class*='product-content']") or
                    soup.select_one("article.product") or
                    soup.select_one(".product") or
                    soup.select_one("#product")
                )
            
            # Exclude secțiuni de produse similare
            if product_block:
                for section in product_block.find_all(['section', 'div'], class_=re.compile(r'similar|related|recommend|also|other', re.I)):
                    section.decompose()
                for sidebar in product_block.find_all(['aside', 'div'], class_=re.compile(r'sidebar|related|recommend', re.I)):
                    sidebar.decompose()
                # Exclude și secțiuni care conțin "shop" sau "catalog" în clasă (alte produse)
                for shop_section in product_block.find_all(['div', 'section'], class_=re.compile(r'shop|catalog|product-list|grid', re.I)):
                    # Păstrează doar dacă conține SKU-ul sau numele produsului
                    section_text = shop_section.get_text()
                    if sku_furnizor and sku_furnizor != "MMS-unknown" and sku_furnizor not in section_text:
                        if not (name and any(word in section_text for word in name.split()[:3] if len(word) > 3)):
                            shop_section.decompose()
            
            # Prioritizează galeria produsului dacă există
            search_soup = product_gallery if product_gallery else (product_block if product_block else soup)
            
            # Doar selectori specifici pentru imagini produs (din config)
            img_selectors = selectors.get("images", ["img[src*='/web/image/product.template/']", "img[src*='/web/image/']"])
            if isinstance(img_selectors, str):
                img_selectors = [img_selectors]
            
            seen = set()
            name_words = [w for w in name.split() if len(w) > 3][:3] if name else []
            
            for sel in img_selectors:
                for img in search_soup.select(sel):
                    # Dacă avem galerie produs, acceptă doar imagini din galerie
                    if product_gallery:
                        if img not in product_gallery.find_all('img'):
                            continue
                    
                    # Verifică dacă imaginea este în blocul produsului corect
                    img_parent = img.find_parent(['div', 'section', 'article', 'main', 'figure', 'a'])
                    
                    # Verifică dacă părintele imaginii conține SKU-ul sau numele produsului
                    is_valid = False
                    
                    if img_parent:
                        parent_text = img_parent.get_text()
                        parent_classes = ' '.join(img_parent.get('class', [])).lower()
                        parent_id = (img_parent.get('id') or '').lower()
                        
                        # Exclude secțiuni de produse similare
                        if any(x in parent_classes + parent_id for x in ['similar', 'related', 'recommend', 'also', 'other', 'sidebar', 'shop', 'catalog', 'product-list', 'grid']):
                            continue
                        
                        # Verifică dacă conține SKU-ul
                        if sku_furnizor and sku_furnizor != "MMS-unknown" and sku_furnizor.upper() in parent_text.upper():
                            is_valid = True
                        # Sau dacă conține numele produsului (primele 2-3 cuvinte importante)
                        elif name_words and any(word.upper() in parent_text.upper() for word in name_words):
                            is_valid = True
                    
                    # Dacă nu am găsit părinte valid, verifică dacă e în product_block
                    if not is_valid and product_block:
                        # Verifică dacă imaginea este descendentă directă a product_block
                        if img in product_block.find_all('img'):
                            # Verifică că nu e într-o secțiune de produse similare
                            img_container = img.find_parent(['div', 'section', 'article'])
                            if img_container:
                                container_classes = ' '.join(img_container.get('class', [])).lower()
                                container_id = (img_container.get('id') or '').lower()
                                if not any(x in container_classes + container_id for x in ['similar', 'related', 'recommend', 'also', 'other', 'sidebar', 'shop', 'catalog', 'product-list', 'grid']):
                                    # Verifică că containerul conține SKU sau nume produs
                                    container_text = img_container.get_text()
                                    if (sku_furnizor and sku_furnizor != "MMS-unknown" and sku_furnizor.upper() in container_text.upper()) or \
                                       (name_words and any(word.upper() in container_text.upper() for word in name_words)):
                                        is_valid = True
                    
                    # Dacă nu avem product_block, acceptă doar dacă e în main sau article principal
                    if not is_valid and not product_block:
                        main_elem = soup.select_one('main') or soup.select_one('article')
                        if main_elem and img in main_elem.find_all('img'):
                            # Verifică că nu e într-o secțiune de produse similare
                            img_container = img.find_parent(['div', 'section'])
                            if img_container:
                                container_classes = ' '.join(img_container.get('class', [])).lower()
                                if not any(x in container_classes for x in ['similar', 'related', 'recommend', 'also', 'other', 'sidebar']):
                                    is_valid = True
                    
                    if is_valid:
                        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                        if src:
                            if not src.startswith("http"):
                                src = base_url + src if src.startswith("/") else base_url + "/" + src
                            if src not in seen:
                                seen.add(src)
                                img_urls.append(src)
                                self.log(f"      ✓ Imagine validă găsită: {src[:80]}...", "INFO")
            
            # MMS: max 3 imagini per produs (evită imagini de la alte produse)
            img_urls = list(dict.fromkeys(img_urls))[:3]
            if img_urls:
                self.log(f"   🔍 Total imagini găsite: {len(img_urls)}", "INFO")
            else:
                self.log("   ⚠️ Nu am găsit imagini pe pagina produsului", "WARNING")

        product_id = re.sub(r"[^a-zA-Z0-9_-]", "_", (sku_furnizor or product_url)[:50])
        images_data = self._download_images(img_urls, product_id, self._headers()) if img_urls else []

        tags = []
        return self._build_product_data(
            name=name,
            price=price,
            description=description,
            images=images_data,
            sku_furnizor=sku_furnizor,
            ean_real=ean_real or sku_furnizor,
            source_url=product_url,
            tags=tags,
            soup=soup,
            page_text=page_text,
        )
