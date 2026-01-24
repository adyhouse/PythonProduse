        
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
