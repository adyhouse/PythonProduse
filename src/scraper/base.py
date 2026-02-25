"""
Clasă de bază pentru scraper-uri furnizori.
Fiecare furnizor implementează scrape_product(sku_or_url) și returnează
un dict compatibil cu pipeline-ul WebGSM (product_data).
"""
import re
from abc import ABC, abstractmethod
from urllib.parse import urlparse
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

    def _login_odoo_json_rpc(self, base_url: str, username: str, password: str, db: str = "") -> bool:
        """
        Login Odoo prin JSON-RPC la /web/session/authenticate.
        db: nume baza de date (din formularul de login); gol = default, unele instanțe cer explicit.
        """
        import json
        url = base_url.rstrip("/") + "/web/session/authenticate"
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "db": db or "",
                "login": username,
                "password": password,
            },
            "id": None,
        }
        headers = {**self._headers(), "Content-Type": "application/json"}
        try:
            self.log("   📤 Login Odoo (JSON-RPC /web/session/authenticate)...", "INFO")
            r = self.session.post(url, json=payload, headers=headers, timeout=15)
            self.log(f"   📥 Răspuns authenticate (status: {r.status_code})", "INFO")
            if r.status_code != 200:
                return False
            data = r.json()
            if data.get("error"):
                self.log(f"   ⚠️ Odoo error: {data.get('error', {}).get('data', {}).get('message', data.get('error'))}", "WARNING")
                return False
            result = data.get("result") or {}
            if result.get("uid") or result.get("session_id"):
                self.log("   ✓ Login reușit (sesiune Odoo)", "SUCCESS")
                return True
            return False
        except Exception as e:
            self.log(f"   ⚠️ Eroare login JSON-RPC: {e}", "WARNING")
            return False

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
        env_file = None
        if script_dir:
            env_file = Path(script_dir) / ".env"
            if env_file.exists():
                load_dotenv(env_file, override=True)
                self.log(f"   📄 .env încărcat: {env_file}", "INFO")
            else:
                self.log(f"   ⚠️ .env nu există la: {env_file}", "WARNING")
        
        # Construiește numele variabilelor bazat pe numele furnizorului
        supplier_name = self.name.upper()
        # Încearcă mai multe variabile de mediu posibile
        username = (
            os.getenv(f"{supplier_name}_USERNAME") or
            os.getenv(f"{supplier_name}_LOGIN") or
            os.getenv("MMSMOBILE_USERNAME") or
            os.getenv("MPSMOBILE_USERNAME") or
            os.getenv("MMS_USERNAME") or
            os.getenv("MPS_USERNAME") or
            os.getenv("SUPPLIER_USERNAME") or
            ""
        )
        password = (
            os.getenv(f"{supplier_name}_PASSWORD") or
            os.getenv(f"{supplier_name}_PASS") or
            os.getenv("MMSMOBILE_PASSWORD") or
            os.getenv("MPSMOBILE_PASSWORD") or
            os.getenv("MMS_PASSWORD") or
            os.getenv("MPS_PASSWORD") or
            os.getenv("SUPPLIER_PASSWORD") or
            ""
        )
        
        # Debug: arată ce variabile sunt căutate
        if not username or not password:
            self.log(f"   🔍 Căutare variabile: {supplier_name}_USERNAME, {supplier_name}_PASSWORD, MMSMOBILE_*, MPSMOBILE_*, SUPPLIER_*", "INFO")
            # Listă toate variabilele de mediu care conțin "MOBILE" sau "USERNAME" sau "PASSWORD" pentru debugging
            all_env_vars = {k: "***" if "PASS" in k or "PASSWORD" in k else v for k, v in os.environ.items() if "MOBILE" in k.upper() or "USERNAME" in k.upper() or "PASSWORD" in k.upper()}
            if all_env_vars:
                self.log(f"   📋 Variabile găsite în .env: {list(all_env_vars.keys())}", "INFO")
            else:
                self.log("   ⚠️ Nu s-au găsit variabile relevante în .env", "WARNING")
        
        if not username or not password:
            self.log(f"   ⚠️ Login necesar dar USERNAME/PASSWORD lipsesc din .env (username={'✓' if username else '✗'}, password={'✓' if password else '✗'})", "WARNING")
            return False
        
        self.log(f"   ✓ Credențiale găsite (username: {username[:3]}***)", "INFO")
        
        base_url = self.config.get("base_url", "").rstrip("/")
        lang = self.config.get("default_language", "en")
        login_url = login_config.get("url", "").format(base_url=base_url, lang=lang)
        
        if not login_url:
            self.log("   ⚠️ Login URL lipsă din config", "WARNING")
            return False
        
        try:
            self.log(f"   🔐 Încearcă login la: {login_url}", "INFO")
            self.session = requests.Session()
            # Obține pagina de login (cookie de sesiune, eventual CSRF)
            login_page = self.session.get(login_url, headers=self._headers(), timeout=15)
            login_page.raise_for_status()
            self.log(f"   ✓ Pagină login accesată (status: {login_page.status_code})", "INFO")

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(login_page.content, "html.parser")

            # Odoo: încearcă JSON-RPC (necesită db din formular sau .env dacă e multi-db)
            odoo_db = ""
            if "/web/login" in login_url:
                for inp in soup.find_all("input", {"name": "db"}):
                    if inp.get("value"):
                        odoo_db = inp.get("value", "").strip()
                        break
                if not odoo_db:
                    odoo_db = os.getenv(f"{supplier_name}_DB") or os.getenv("MMSMOBILE_DB") or os.getenv("MPSMOBILE_DB") or os.getenv("ODOO_DB") or ""
                if odoo_db:
                    self.log(f"   📋 DB: {odoo_db}", "INFO")
                if self._login_odoo_json_rpc(base_url, username, password, db=odoo_db):
                    return True
                self.log("   ⚠️ Login JSON-RPC eșuat, încerc cu formularul HTML...", "INFO")

            # Găsește formularul care conține câmpuri login ȘI password (MPS Mobile folosește "email", nu "login")
            login_form = None
            for form in soup.find_all("form"):
                names = [inp.get("name", "").lower() for inp in form.find_all("input") if inp.get("name")]
                has_login = any(x in n for n in names for x in ["login", "user", "email", "username"] if "password" not in n and "csrf" not in n and "token" not in n)
                has_password = any("password" in n for n in names)
                if has_login and has_password:
                    login_form = form
                    break
            if not login_form:
                login_form = soup.find("form", {"id": re.compile(r"login|auth", re.I)}) or soup.find("form")

            login_data = {}
            if login_form:
                for inp in login_form.find_all("input"):
                    name = inp.get("name")
                    value = inp.get("value", "")
                    inp_type = inp.get("type", "").lower()
                    if name and inp_type != "submit":
                        login_data[name] = value
                # Fallback CSRF din meta tags (unele site-uri PrestaShop pun token-ul acolo)
                for key in list(login_data.keys()):
                    if "csrf" in key.lower() or "token" in key.lower():
                        if not login_data[key]:
                            for meta in soup.find_all("meta", {"name": re.compile(r"csrf|token", re.I)}):
                                if meta.get("content"):
                                    login_data[key] = meta.get("content", "").strip()
                                    break
                self.log(f"   📋 Câmpuri formular: {list(login_data.keys())}", "INFO")

            # MPS Mobile, PrestaShop etc. folosesc "email" ca câmp login, nu "login"
            login_field = next((k for k in login_data if any(x in k.lower() for x in ["login", "user", "email", "username"]) and "password" not in k.lower() and "csrf" not in k.lower() and "token" not in k.lower()), None)
            if login_field:
                login_data[login_field] = username
            elif "email" in login_data:
                login_data["email"] = username
            else:
                login_data["login"] = username
            password_field = next((k for k in login_data if "password" in k.lower()), None)
            if password_field:
                login_data[password_field] = password
            else:
                login_data.setdefault("password", password)

            action_url = login_url
            if login_form and login_form.get("action"):
                action = (login_form.get("action") or "").strip()
                if action and action != "#":
                    if action.startswith("http"):
                        action_url = action
                    elif action.startswith("/"):
                        action_url = base_url + action
                    else:
                        action_url = (login_url.rstrip("/") + "/" + action.lstrip("/"))
            self.log(f"   📍 POST la: {action_url}", "INFO")

            post_headers = dict(self._headers())
            post_headers["Referer"] = login_url
            try:
                parsed = urlparse(login_url)
                post_headers["Origin"] = f"{parsed.scheme}://{parsed.netloc}"
            except Exception:
                pass

            response = self.session.post(action_url, data=login_data, headers=post_headers, timeout=15, allow_redirects=True)
            self.log(f"   📥 Răspuns login (status: {response.status_code}, final URL: {response.url[:70]}...)", "INFO")

            location = response.headers.get("Location", "")
            final_url = (response.url or "").lower()

            # Succes: redirect 302/303 către dashboard/account (Odoo /web, PrestaShop /my-account, etc.)
            success_redirects = ("/web", "/web#", "/my-account", "/customer/account", "/account", "/dashboard", "/kundenkonto")
            if response.status_code in (302, 303) and location:
                loc_lower = location.lower()
                if any(s in loc_lower for s in success_redirects) and "/login" not in loc_lower:
                    if not location.startswith("http"):
                        location = base_url + location if location.startswith("/") else base_url + "/" + location
                    self.log(f"   🔄 Redirect succes: {location[:60]}...", "INFO")
                    self.session.get(location, headers=self._headers(), timeout=15)
                    self.log("   ✓ Login reușit", "SUCCESS")
                    return True

            # Succes: după allow_redirects=True, suntem pe pagină account (nu login)
            if any(s in final_url for s in success_redirects) and "/login" not in final_url and "/customer/login" not in final_url:
                self.log("   ✓ Login reușit (redirect la account)", "SUCCESS")
                return True

            # Succes: pagină 200 conține "logout"/"abmelden" = suntem logați (PrestaShop, custom, mpsmobile.de)
            body_lower = (response.text or "").lower()
            if response.status_code == 200 and any(x in body_lower for x in ("logout", "abmelden", "ausloggen", "log out", "sign out", "abmeldung")):
                self.log("   ✓ Login reușit (pagina conține logout)", "SUCCESS")
                return True

            # Verifică răspuns JSON (unele Odoo răspund cu 200 + JSON)
            try:
                data = response.json()
                if data.get("result") and (data["result"].get("uid") or data["result"].get("session_id")):
                    self.log("   ✓ Login reușit (JSON)", "SUCCESS")
                    return True
            except Exception:
                pass

            debug_file = Path(script_dir) / "logs" / f"login_failed_{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            debug_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                debug_file.write_text(response.text, encoding="utf-8")
                self.log(f"   📝 Răspuns salvat: {debug_file}", "INFO")
            except Exception:
                pass
            # Extrage mesaje de eroare din răspuns (PrestaShop, MPS Mobile etc.)
            try:
                resp_soup = BeautifulSoup(response.text or "", "html.parser")
                for sel in (".alert-danger", ".alert.alert-danger", ".error", "[role='alert']", ".invalid-feedback"):
                    for el in resp_soup.select(sel):
                        txt = (el.get_text() or "").strip()
                        if txt and len(txt) < 200:
                            self.log(f"   📌 Mesaj eroare: {txt[:150]}", "WARNING")
                            break
            except Exception:
                pass
            self.log(f"   ⚠️ Login eșuat – verifică credențiale (status: {response.status_code})", "WARNING")
            return False
        except Exception as e:
            import traceback
            self.log(f"   ⚠️ Eroare login: {e}", "WARNING")
            self.log(f"   📋 Traceback: {traceback.format_exc()[:200]}", "DEBUG")
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
                size_bytes = len(r.content)
                size_mb = size_bytes / (1024 * 1024)
                size_kb = round(size_bytes / 1024)
                width, height = None, None
                try:
                    from PIL import Image
                    with Image.open(path) as im:
                        width, height = im.size
                except Exception:
                    pass
                entry = {
                    "src": url,
                    "local_path": str(path),
                    "name": name,
                    "size": f"{size_mb:.2f} MB",
                    "size_kb": size_kb,
                    "width": width,
                    "height": height,
                }
                out.append(entry)
                dims = f" {width}×{height}" if (width and height) else ""
                self.log(f"      📷 [{idx}] ✓ {name} ({size_kb} KB{dims})", "SUCCESS")
            except Exception as e:
                self.log(f"      ⚠️ [{idx}] Eroare: {e}", "WARNING")
        return out

    @abstractmethod
    def scrape_product(self, sku_or_url: str) -> Optional[Dict]:
        """
        Extrage date produs. Returnează dict WebGSM (product_data) sau None.
        """
        pass
