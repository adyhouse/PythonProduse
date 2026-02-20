"""
Clasă de bază pentru scraper-uri furnizori.
Fiecare furnizor implementează scrape_product(sku_or_url) și returnează
un dict compatibil cu pipeline-ul WebGSM (product_data).
"""
import re
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


class BaseScraper(ABC):
    """Interfață comună pentru toți furnizorii."""

    def __init__(self, config: Dict[str, Any], app: Any):
        """
        config: dict din suppliers/<furnizor>/config.json
        app: instanță ImportProduse (pentru log, script_dir, detect_category, etc.)
        """
        self.config = config
        self.app = app
        self.name = config.get("name", "unknown")
        self.skip_images = config.get("skip_images", False)
        self.session = None  # Session pentru login (dacă e necesar)

    def log(self, message: str, level: str = "INFO"):
        """Redirect la logger-ul aplicației."""
        if hasattr(self.app, "log"):
            self.app.log(message, level)

    def _headers(self) -> Dict[str, str]:
        """Returnează headers default pentru request-uri. Poate fi suprascrisă în subclase."""
        return {
            "User-Agent": self.config.get("headers", {}).get(
                "User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": self.config.get("headers", {}).get(
                "Accept-Language", "en-US,en;q=0.9"
            ),
        }

    @property
    def script_dir(self):
        """Directorul rădăcină al proiectului."""
        return getattr(self.app, "_script_dir", None)

    def _build_product_data(
        self,
        name: str,
        price: float,
        description: str,
        images: List[Dict],
        sku_furnizor: str,
        ean_real: str,
        source_url: str,
        tags: Optional[List[str]] = None,
        soup: Any = None,
        page_text: str = "",
    ) -> Dict:
        """
        Construiește product_data WebGSM din datele brute, folosind metodele app.
        """
        tags = tags or []
        if soup and not page_text and hasattr(soup, "get_text"):
            page_text = soup.get_text()
        availability = "in_stock"
        if hasattr(self.app, "detect_availability") and (soup is not None or page_text):
            availability = self.app.detect_availability(soup, page_text)
        if availability == "in_stock":
            locatie_stoc = "depozit_central"
        elif availability == "preorder":
            locatie_stoc = "precomanda"
        else:
            locatie_stoc = "indisponibil"

        category_path = ""
        if hasattr(self.app, "detect_category"):
            category_path = self.app.detect_category(name, tags) or ""

        attributes = {}
        if hasattr(self.app, "extract_product_attributes"):
            attributes = self.app.extract_product_attributes(name, description, source_url)

        category_slug = ""
        if hasattr(self.app, "get_webgsm_category"):
            category_slug = self.app.get_webgsm_category(name, description=description) or ""

        compat_codes = ""
        if hasattr(self.app, "extract_compatibility_codes"):
            compat_codes = self.app.extract_compatibility_codes(description) or ""

        screen_features = {"ic_movable": "0", "truetone_support": "0"}
        if hasattr(self.app, "detect_screen_features"):
            screen_features = self.app.detect_screen_features(name, description)

        brand = "Componenti Digitali"
        name_lower = (name or "").lower()
        if "iphone" in name_lower or "apple" in name_lower:
            brand = "Apple"
        elif "samsung" in name_lower or "galaxy" in name_lower:
            brand = "Samsung"
        elif "google" in name_lower or "pixel" in name_lower:
            brand = "Google"

        return {
            "ean": ean_real or sku_furnizor or source_url,
            "ean_real": ean_real,
            "sku": sku_furnizor,
            "sku_furnizor": sku_furnizor,
            "name": name or "Produs",
            "price": price if price is not None else 0.0,
            "description": description or name or "",
            "stock": "100",
            "brand": brand,
            "tags": ", ".join(tags) if isinstance(tags, list) else (tags or ""),
            "category_path": category_path,
            "images": images,
            "pa_model": attributes.get("pa_model", ""),
            "pa_calitate": attributes.get("pa_calitate", ""),
            "pa_brand_piesa": attributes.get("pa_brand_piesa", ""),
            "pa_tehnologie": attributes.get("pa_tehnologie", ""),
            "category_slug": category_slug,
            "coduri_compatibilitate": compat_codes,
            "ic_movable": screen_features.get("ic_movable", "0"),
            "truetone_support": screen_features.get("truetone_support", "0"),
            "furnizor_activ": self.name,
            "pret_achizitie_eur": price if price is not None else 0.0,
            "availability": availability,
            "locatie_stoc": locatie_stoc,
            "source_url": source_url or "",
        }

    def _table_value_by_header(self, soup: Any, header_text: str) -> str:
        """Extrage valoarea din tabel după header (ex: SKU, EAN, GTIN)."""
        if soup is None or not hasattr(soup, "select"):
            return ""
        cells = soup.select("table td, table th, [class*='table'] td, [class*='table'] th")
        for i, cell in enumerate(cells):
            if header_text.lower() in (cell.get_text(strip=True) or "").lower():
                if i + 1 < len(cells):
                    return (cells[i + 1].get_text(strip=True) or "").strip()
        return ""

    def _login_if_required(self) -> bool:
        """
        Face login dacă este necesar (config.login.required = true).
        Returnează True dacă login-ul a reușit sau nu era necesar, False dacă a eșuat.
        """
        login_config = self.config.get("login", {})
        if not login_config.get("required", False):
            return True
        
        import os
        from dotenv import load_dotenv
        
        # Încarcă .env din script_dir
        script_dir = self.script_dir
        if script_dir:
            env_file = Path(script_dir) / ".env"
            if env_file.exists():
                load_dotenv(env_file)
        
        # Extrage username și password din .env
        username_key = login_config.get("username", "").replace("USERNAME_FROM_ENV", "")
        password_key = login_config.get("password", "").replace("PASSWORD_FROM_ENV", "")
        
        # Încearcă mai multe variabile de mediu posibile
        username = os.getenv("MMSMOBILE_USERNAME") or os.getenv("MMS_USERNAME") or os.getenv("MMSMOBILE_LOGIN") or ""
        password = os.getenv("MMSMOBILE_PASSWORD") or os.getenv("MMS_PASSWORD") or os.getenv("MMSMOBILE_PASS") or ""
        
        # Dacă nu găsește, încearcă variabile generice
        if not username:
            username = os.getenv("SUPPLIER_USERNAME", "")
        if not password:
            password = os.getenv("SUPPLIER_PASSWORD", "")
        
        if not username or not password:
            self.log("   ⚠️ Login necesar dar USERNAME/PASSWORD lipsesc din .env", "WARNING")
            return False
        
        base_url = self.config.get("base_url", "").rstrip("/")
        login_url = login_config.get("url", "").format(base_url=base_url)
        
        if not login_url:
            self.log("   ⚠️ Login URL lipsă din config", "WARNING")
            return False
        
        try:
            self.session = requests.Session()
            # Obține pagina de login pentru CSRF token (dacă e necesar)
            login_page = self.session.get(login_url, headers=self._headers(), timeout=15)
            login_page.raise_for_status()
            
            # Încearcă login-ul (poate necesita CSRF token sau alte câmpuri)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(login_page.content, "html.parser")
            
            # Pentru Odoo (/web/login), câmpurile sunt de obicei "login" și "password"
            # Caută formularul de login
            login_form = soup.find("form") or soup.find("form", {"id": re.compile(r"login|auth", re.I)})
            
            login_data = {}
            
            # Extrage toate input-urile din formular (inclusiv hidden pentru CSRF)
            if login_form:
                for inp in login_form.find_all("input"):
                    name = inp.get("name")
                    value = inp.get("value", "")
                    if name:
                        login_data[name] = value
            
            # Setează username și password
            # Odoo folosește de obicei "login" pentru username
            if "login" in login_data or any("login" in k.lower() for k in login_data.keys()):
                # Găsește câmpul corect pentru login
                login_field = None
                for key in login_data.keys():
                    if "login" in key.lower() and "password" not in key.lower():
                        login_field = key
                        break
                if login_field:
                    login_data[login_field] = username
                else:
                    login_data["login"] = username
            else:
                login_data["login"] = username
            
            # Setează password
            if "password" in login_data or any("password" in k.lower() for k in login_data.keys()):
                password_field = None
                for key in login_data.keys():
                    if "password" in key.lower():
                        password_field = key
                        break
                if password_field:
                    login_data[password_field] = password
                else:
                    login_data["password"] = password
            else:
                login_data["password"] = password
            
            # Obține action URL din formular (dacă există)
            action_url = login_url
            if login_form and login_form.get("action"):
                action = login_form.get("action")
                if action.startswith("http"):
                    action_url = action
                elif action.startswith("/"):
                    action_url = base_url + action
                else:
                    action_url = login_url.rstrip("/") + "/" + action
            
            response = self.session.post(action_url, data=login_data, headers=self._headers(), timeout=15, allow_redirects=False)
            
            # Verifică dacă login-ul a reușit (redirect sau mesaj de succes)
            # Odoo de obicei redirectează la /web sau /web#home după login reușit
            if response.status_code == 302 or (response.status_code == 200 and ("/web" in response.headers.get("Location", "") or "logout" in response.text.lower() or "my account" in response.text.lower())):
                # Dacă e redirect, urmează redirect-ul
                if response.status_code == 302:
                    redirect_url = response.headers.get("Location", "")
                    if redirect_url:
                        if not redirect_url.startswith("http"):
                            redirect_url = base_url + redirect_url if redirect_url.startswith("/") else base_url + "/" + redirect_url
                        self.session.get(redirect_url, headers=self._headers(), timeout=15)
                self.log("   ✓ Login reușit", "SUCCESS")
                return True
            else:
                self.log("   ⚠️ Login eșuat - verifică credențiale în .env", "WARNING")
                return False
        except Exception as e:
            self.log(f"   ⚠️ Eroare login: {e}", "WARNING")
            return False

    def _save_debug_html(self, soup: Any, product_url: str = ""):
        """Salvează HTML-ul paginii produsului în logs/ pentru debugging."""
        if not soup or not hasattr(soup, "prettify"):
            return
        script_dir = self.script_dir
        if not script_dir:
            return
        logs_dir = Path(script_dir) / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        supplier_name = self.name or "unknown"
        debug_file = logs_dir / f"debug_product_{supplier_name}_{timestamp}.html"
        try:
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(soup.prettify())
            self.log(f"   📝 HTML produs salvat: {debug_file}", "INFO")
        except Exception as e:
            self.log(f"   ⚠️ Eroare salvare HTML: {e}", "WARNING")

    def _download_images(
        self, img_urls: List[str], product_id: str, headers: Optional[Dict] = None, max_images: int = 10
    ) -> List[Dict]:
        """
        Descarcă imaginile în script_dir/images și returnează listă dict cu src, local_path, name, size.
        Dacă skip_images=True sau img_urls goale, returnează [].
        """
        if self.skip_images or not img_urls:
            return []
        script_dir = self.script_dir
        if not script_dir:
            return []
        images_dir = Path(script_dir) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        out = []
        h = headers or {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "image/webp,image/*,*/*;q=0.8",
        }
        product_id_clean = re.sub(r'[<>:"/\\|?*]', "_", str(product_id)[:50])
        for idx, url in enumerate(list(img_urls)[:max_images], 1):
            try:
                r = requests.get(url, headers=h, timeout=15)
                r.raise_for_status()
                ext = "jpg"
                if ".webp" in url.lower() or "webp" in r.headers.get("content-type", ""):
                    ext = "webp"
                elif ".png" in url.lower() or "png" in r.headers.get("content-type", ""):
                    ext = "png"
                name = f"{product_id_clean}_{idx}.{ext}"
                path = images_dir / name
                path.write_bytes(r.content)
                size_mb = len(r.content) / (1024 * 1024)
                out.append(
                    {"src": url, "local_path": str(path), "name": name, "size": f"{size_mb:.2f} MB"}
                )
                self.log(f"      📷 [{idx}] ✓ {name}", "SUCCESS")
            except Exception as e:
                self.log(f"      ⚠️ [{idx}] Eroare: {e}", "WARNING")
        return out

    @abstractmethod
    def scrape_product(self, sku_or_url: str) -> Optional[Dict]:
        """
        Extrage date produs. Returnează dict WebGSM (product_data) sau None.
        """
        pass
