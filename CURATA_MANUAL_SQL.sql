-- ═══════════════════════════════════════════════════════════════════════════
-- CURĂȚARE RAPIDĂ SQL - Produse Orfane în WooCommerce
-- ═══════════════════════════════════════════════════════════════════════════
-- 
-- INSTRUIRE: Copy-paste aceste comenzi direct în phpMyAdmin
-- Query tool → Rulează comenzile unu după alta
-- 
-- ⚠️ ÎNAINTE: Fă BACKUP la baza de date!
-- ═══════════════════════════════════════════════════════════════════════════


-- PASO 1: IDENTIFICĂ PREFIXUL TABELEI (fii sigur ce prefix ai!)
-- ═══════════════════════════════════════════════════════════════════════════
-- Rulează asta pentru a vedea care e prefixul:
SHOW TABLES LIKE '%posts%' LIMIT 1;
SHOW TABLES LIKE '%wc_product%' LIMIT 1;

-- Rezultat: vei vedea ceva de genul:
-- wp_posts (prefix: wp_)
-- wplt_posts (prefix: wplt_)
-- wbc_posts (prefix: wbc_)
-- 
-- IMPORTANȚA: Folosește prefixul CORECT în comenzile de mai jos!


-- PASO 2: GĂSEȘTE PRODUSE ORFANE (ID fără înregistrare în meta_lookup)
-- ═══════════════════════════════════════════════════════════════════════════
-- 
-- Înlocuiește "wp_" cu prefixul tău (wplt_, wbc_, etc.)
-- 
SELECT 
    p.ID,
    p.post_title,
    p.post_status,
    p.post_date
FROM wp_posts p
WHERE p.post_type = 'product'
  AND NOT EXISTS (
      SELECT 1 FROM wp_wc_product_meta_lookup 
      WHERE product_id = p.ID
  )
ORDER BY p.ID DESC;

-- Rezultat: vei vedea lista ID-urilor orfane (5105, 5087, etc.)


-- PASO 3: ȘTERGE TOATE REFERINȚELE ACESTOR ID-URI (3 pasuri!)
-- ═══════════════════════════════════════════════════════════════════════════

-- STEP 3.1: Șterge din postmeta
DELETE FROM wp_postmeta 
WHERE post_id IN (
    SELECT p.ID FROM wp_posts p
    WHERE p.post_type = 'product'
      AND NOT EXISTS (
          SELECT 1 FROM wp_wc_product_meta_lookup 
          WHERE product_id = p.ID
      )
);

-- STEP 3.2: Șterge din term_relationships
DELETE FROM wp_term_relationships 
WHERE object_id IN (
    SELECT p.ID FROM wp_posts p
    WHERE p.post_type = 'product'
      AND NOT EXISTS (
          SELECT 1 FROM wp_wc_product_meta_lookup 
          WHERE product_id = p.ID
      )
);

-- STEP 3.3: Șterge din wp_posts (move to trash, nu permanent)
DELETE FROM wp_posts 
WHERE post_type = 'product'
  AND NOT EXISTS (
      SELECT 1 FROM wp_wc_product_meta_lookup 
      WHERE product_id = p.ID
  );

-- Daca ai eroare "Unknown column 'p.ID'", folosește asta:
DELETE FROM wp_posts 
WHERE ID IN (
    SELECT p.ID FROM (
        SELECT p.ID FROM wp_posts p
        WHERE p.post_type = 'product'
          AND NOT EXISTS (
              SELECT 1 FROM wp_wc_product_meta_lookup 
              WHERE product_id = p.ID
          )
    ) as p
);


-- PASO 4: RESETEAZĂ AUTO_INCREMENT (IMPORTANT!)
-- ═══════════════════════════════════════════════════════════════════════════

-- Găsește MAX(ID) pentru produse VALIDE (cu înregistrare în meta_lookup)
SELECT MAX(p.ID) as max_valid_id
FROM wp_posts p
WHERE p.post_type = 'product'
  AND EXISTS (
      SELECT 1 FROM wp_wc_product_meta_lookup 
      WHERE product_id = p.ID
  );

-- Rezultat: ex: max_valid_id = 5084
-- Următorul ID ar trebui să fie: 5084 + 1 = 5085

-- Rulează asta (înlocuiește 5085 cu (MAX_ID + 1)):
ALTER TABLE wp_posts AUTO_INCREMENT = 5085;

-- Verifică că s-a schimbat:
SELECT AUTO_INCREMENT FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'wp_posts';


-- PASO 5: CURAȚĂ SKU-URI NULL (optional, dar recomandat)
-- ═══════════════════════════════════════════════════════════════════════════

-- Găsește SKU-uri NULL sau goale
SELECT COUNT(*) FROM wp_wc_product_meta_lookup 
WHERE sku IS NULL OR sku = '';

-- Șterge SKU-uri NULL
DELETE FROM wp_wc_product_meta_lookup 
WHERE sku IS NULL OR sku = '';


-- PASO 6: OPTIMIZEAZĂ TABELE (de obicei este mai rapid)
-- ═══════════════════════════════════════════════════════════════════════════

OPTIMIZE TABLE wp_posts;
OPTIMIZE TABLE wp_postmeta;
OPTIMIZE TABLE wp_wc_product_meta_lookup;
OPTIMIZE TABLE wp_term_relationships;


-- PASO 7: VERIFICARE FINALĂ
-- ═══════════════════════════════════════════════════════════════════════════

-- Ar trebui să NU aibă rezultate (0 orfane):
SELECT COUNT(*) as orphan_count FROM wp_posts p
WHERE p.post_type = 'product'
  AND NOT EXISTS (
      SELECT 1 FROM wp_wc_product_meta_lookup 
      WHERE product_id = p.ID
  );

-- Ar trebui să NU aibă SKU-uri duplicate:
SELECT sku, COUNT(*) as count 
FROM wp_wc_product_meta_lookup 
WHERE sku IS NOT NULL AND sku != ''
GROUP BY sku 
HAVING count > 1;

-- Ar trebui să se potrivească:
SELECT COUNT(*) FROM wp_posts WHERE post_type = 'product';
SELECT COUNT(*) FROM wp_wc_product_meta_lookup;

-- Daca sunt egale = baza de date e curată!


-- ═══════════════════════════════════════════════════════════════════════════
-- GHID PAȘI:
-- ═══════════════════════════════════════════════════════════════════════════
--
-- 1. Copy-paste "PASO 2" și rulează pentru a vedea ce orfane ai
-- 2. Notează MAX ID-ul (ex: 5105)
-- 3. Calculează MAX + 1 (ex: 5106)
-- 4. Copy-paste "PASO 3.1", "3.2", "3.3" - rulează pe rând
-- 5. Copy-paste "PASO 4" și setează AUTO_INCREMENT = MAX + 1
-- 6. Copy-paste "PASO 6" și optimizează
-- 7. Copy-paste "PASO 7" și verifică - ar trebui 0 orfane!
-- 8. Goleșt Trash din WooCommerce (manual)
-- 9. Relansează importul din program
--
-- ═══════════════════════════════════════════════════════════════════════════
-- IMPORTANT: PREFIXUL TABELEI!
-- ═══════════════════════════════════════════════════════════════════════════
--
-- Dacă vezi în phpMyAdmin tabele cu prefixul "wplt_" (nu "wp_")
-- Atunci înlocuiește TOATE "wp_" cu "wplt_" în comenzile de sus!
--
-- Exemplu incorect: wp_posts, wp_postmeta
-- Exemplu corect:   wplt_posts, wplt_postmeta
--
-- ═══════════════════════════════════════════════════════════════════════════
