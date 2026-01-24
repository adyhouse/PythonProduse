-- ═══════════════════════════════════════════════════════════════════════════
-- Script curățare intrări duplicate/orfane în WooCommerce
-- ═══════════════════════════════════════════════════════════════════════════
-- 
-- UTILIZARE: Rulează aceste comenzi în phpMyAdmin sau MySQL client
-- 
-- ATENȚIE: Fă backup înainte! (Tools → Export Database)
--
-- ═══════════════════════════════════════════════════════════════════════════

-- 1. VERIFICĂ produsele șterse incomplet (status 'trash' sau 'auto-draft')
-- ═══════════════════════════════════════════════════════════════════════════
SELECT ID, post_title, post_status, post_type 
FROM wp_posts 
WHERE post_type = 'product' 
  AND post_status IN ('trash', 'auto-draft', 'inherit')
ORDER BY ID DESC;

-- 2. ȘTERGE produsele din trash (ștergere permanentă)
-- ═══════════════════════════════════════════════════════════════════════════
-- UNCOMMENT linia de mai jos pentru a executa:
-- DELETE FROM wp_posts WHERE post_type = 'product' AND post_status = 'trash';

-- 3. GĂSEȘTE SKU-uri duplicate în tabelul meta_lookup
-- ═══════════════════════════════════════════════════════════════════════════
SELECT sku, COUNT(*) as count 
FROM wp_wc_product_meta_lookup 
WHERE sku IS NOT NULL 
  AND sku != '' 
GROUP BY sku 
HAVING count > 1;

-- 4. VERIFICĂ intrări orfane (produse fără înregistrare în wp_posts)
-- ═══════════════════════════════════════════════════════════════════════════
SELECT wc.product_id, wc.sku 
FROM wp_wc_product_meta_lookup AS wc
LEFT JOIN wp_posts AS p ON wc.product_id = p.ID
WHERE p.ID IS NULL;

-- 5. ȘTERGE intrările orfane din meta_lookup
-- ═══════════════════════════════════════════════════════════════════════════
-- UNCOMMENT pentru a executa:
-- DELETE wc FROM wp_wc_product_meta_lookup AS wc
-- LEFT JOIN wp_posts AS p ON wc.product_id = p.ID
-- WHERE p.ID IS NULL;

-- 6. VERIFICĂ SKU-ul specific care dă eroare (înlocuiește 'WEBGSM-005005-XXXX')
-- ═══════════════════════════════════════════════════════════════════════════
SELECT * FROM wp_wc_product_meta_lookup 
WHERE sku LIKE 'WEBGSM-%';

-- 7. ȘTERGE SKU specific (înlocuiește cu SKU-ul tău)
-- ═══════════════════════════════════════════════════════════════════════════
-- UNCOMMENT și înlocuiește SKU:
-- DELETE FROM wp_wc_product_meta_lookup WHERE sku = 'WEBGSM-005005-1234';

-- 8. CURĂȚĂ meta_data orfane
-- ═══════════════════════════════════════════════════════════════════════════
SELECT pm.meta_id, pm.post_id, pm.meta_key, pm.meta_value
FROM wp_postmeta AS pm
LEFT JOIN wp_posts AS p ON pm.post_id = p.ID
WHERE p.ID IS NULL;

-- UNCOMMENT pentru a șterge:
-- DELETE pm FROM wp_postmeta AS pm
-- LEFT JOIN wp_posts AS p ON pm.post_id = p.ID
-- WHERE p.ID IS NULL;

-- 9. RECONSTRUIEȘTE index-uri (după curățare)
-- ═══════════════════════════════════════════════════════════════════════════
-- OPTIMIZE TABLE wp_posts;
-- OPTIMIZE TABLE wp_postmeta;
-- OPTIMIZE TABLE wp_wc_product_meta_lookup;

-- ═══════════════════════════════════════════════════════════════════════════
-- PAȘI PENTRU REZOLVARE:
-- ═══════════════════════════════════════════════════════════════════════════
-- 
-- 1. Fă BACKUP la baza de date (Export în phpMyAdmin)
-- 2. Rulează comenzile SELECT pentru a vedea ce există
-- 3. Uncomment comenzile DELETE pentru a curăța
-- 4. Rulează OPTIMIZE TABLE pentru reconstruire
-- 5. Încearcă din nou importul
-- 
-- ═══════════════════════════════════════════════════════════════════════════

-- ALTERNATIVĂ: Șterge TOATE produsele (ATENȚIE!)
-- ═══════════════════════════════════════════════════════════════════════════
-- Decomentează DOAR dacă vrei să ștergi TOATE produsele din magazin:
--
-- DELETE FROM wp_posts WHERE post_type = 'product';
-- DELETE FROM wp_postmeta WHERE post_id NOT IN (SELECT ID FROM wp_posts);
-- DELETE FROM wp_wc_product_meta_lookup;
-- DELETE FROM wp_term_relationships WHERE object_id NOT IN (SELECT ID FROM wp_posts);
--
-- ═══════════════════════════════════════════════════════════════════════════
