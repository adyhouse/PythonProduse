-- ⚠️ CLEANUP URGENT - RUL ASTA ÎN phpMyAdmin pentru a fixa AUTO_INCREMENT
-- Fă BACKUP ÎNAINTE DE A RULA!

-- PASUL 1: Identifica phantom products (orfani - fără entry în meta_lookup)
SELECT COUNT(*) as phantom_count FROM wplt_posts p
WHERE p.post_type = 'product'
  AND NOT EXISTS (
    SELECT 1 FROM wplt_wc_product_meta_lookup WHERE product_id = p.ID
  );

-- PASUL 2: Șterge TOTUL din postmeta pentru phantom products
DELETE FROM wplt_postmeta 
WHERE post_id IN (
  SELECT p.ID FROM wplt_posts p
  WHERE p.post_type = 'product'
    AND NOT EXISTS (
      SELECT 1 FROM wplt_wc_product_meta_lookup WHERE product_id = p.ID
    )
);

-- PASUL 3: Șterge TOTUL din term_relationships pentru phantom products
DELETE FROM wplt_term_relationships 
WHERE object_id IN (
  SELECT p.ID FROM wplt_posts p
  WHERE p.post_type = 'product'
    AND NOT EXISTS (
      SELECT 1 FROM wplt_wc_product_meta_lookup WHERE product_id = p.ID
    )
);

-- PASUL 4: ⭐ Șterge phantom products din wp_posts
DELETE FROM wplt_posts 
WHERE post_type = 'product'
  AND NOT EXISTS (
    SELECT 1 FROM wplt_wc_product_meta_lookup WHERE product_id = p.ID
  );

-- PASUL 5: ⭐ RESETEAZĂ AUTO_INCREMENT LA 1 (pentru start fresh)
ALTER TABLE wplt_posts AUTO_INCREMENT = 1;

-- PASUL 6: Verifica că e curat
SELECT COUNT(*) as total_products FROM wplt_posts WHERE post_type = 'product';
SELECT COUNT(*) as meta_lookup FROM wplt_wc_product_meta_lookup;

-- Ar trebui să arate același număr!
-- Dacă ambele = 0, baza e goală (asta e OK pentru start fresh)
-- Dacă ambele = X, baza e curată și e ready!
