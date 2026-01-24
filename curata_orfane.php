<?php
/**
 * Script curățare și reparare produse orfane din WooCommerce
 * Rulează din WP Admin → Tools
 * 
 * Problema: WooCommerce creează ID în wp_posts dar eșuează la INSERT în wp_wc_product_meta_lookup
 * Asta lasă ID-uri orfane și AUTO_INCREMENT stricat
 * 
 * SOLUȚIE: Șterge orfane, resetează AUTO_INCREMENT corect, repară tabel meta_lookup
 */

// Inițializează WordPress
require_once(__DIR__ . '/../../wp-load.php');

// Verifică dacă e admin
if (!current_user_can('manage_woocommerce')) {
    wp_die('Acces refuzat! Trebuie să fii admin.');
}

global $wpdb;

// HTML styling
echo '<style>
  body { font-family: Arial, sans-serif; margin: 20px; }
  h1 { color: #0073aa; }
  h2 { color: #404040; border-bottom: 2px solid #0073aa; padding-bottom: 10px; }
  .success { color: green; font-weight: bold; }
  .error { color: red; font-weight: bold; }
  .warning { color: orange; font-weight: bold; }
  .info { color: blue; }
  .code { background: #f1f1f1; padding: 10px; border-left: 3px solid #0073aa; font-family: monospace; }
  table { border-collapse: collapse; margin: 10px 0; }
  table td, table th { border: 1px solid #ddd; padding: 8px; text-align: left; }
  table th { background: #f9f9f9; }
</style>';

echo '<h1>🧹 Reparare Produse Orfane - WooCommerce</h1>';

// ==========================================
// 0. VERIFICA STARE ACTUALA
// ==========================================
echo '<h2>0️⃣ Verificare stare actuală...</h2>';

$prefix = $wpdb->prefix;

// Verific tabelele
$posts_table = $wpdb->get_var("SELECT COUNT(*) FROM {$prefix}posts WHERE post_type = 'product'");
$meta_lookup_table = $wpdb->get_var("SELECT COUNT(*) FROM {$prefix}wc_product_meta_lookup");
$current_auto_increment = $wpdb->get_var("SELECT AUTO_INCREMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{$prefix}posts'");

echo "<p>";
echo "📊 <strong>Tabel wp_posts:</strong> $posts_table produse<br>";
echo "🏷️ <strong>Tabel wp_wc_product_meta_lookup:</strong> $meta_lookup_table înregistrări<br>";
echo "🔢 <strong>AUTO_INCREMENT current:</strong> $current_auto_increment<br>";
echo "</p>";

// ==========================================
// 1. GĂSEȘTE PRODUSE ORFANE
// ==========================================
echo '<h2>1️⃣ Gasire produse orfane...</h2>';

$orphan_query = "SELECT p.ID, p.post_title, p.post_status
                 FROM {$prefix}posts p
                 WHERE p.post_type = 'product'
                   AND NOT EXISTS (
                       SELECT 1 FROM {$prefix}wc_product_meta_lookup 
                       WHERE product_id = p.ID
                   )
                 ORDER BY p.ID DESC";

$orphan_products = $wpdb->get_results($orphan_query);

if (empty($orphan_products)) {
    echo '<p class="success">✅ Nu sunt produse orfane! Stare OK.</p>';
    $has_orphans = false;
} else {
    echo '<p class="error">⚠️ Găsite ' . count($orphan_products) . ' produse orfane!</p>';
    echo '<table><tr><th>ID</th><th>Titlu</th><th>Status</th><th>Acțiune</th></tr>';
    
    $orphan_ids = array();
    foreach ($orphan_products as $prod) {
        $orphan_ids[] = $prod->ID;
        $trash_btn = ($prod->post_status == 'trash') ? '(deja în Trash)' : '';
        echo "<tr>";
        echo "<td>{$prod->ID}</td>";
        echo "<td>{$prod->post_title}</td>";
        echo "<td>{$prod->post_status} $trash_btn</td>";
        echo "<td>Se șterge...</td>";
        echo "</tr>";
    }
    
    echo '</table>';
    $has_orphans = true;
}

// ==========================================
// 2. ȘTERGE PRODUSELE ORFANE
// ==========================================
if ($has_orphans) {
    echo '<h2>2️⃣ Stergere produse orfane...</h2>';
    
    $orphan_ids_str = implode(',', $orphan_ids);
    
    // Șterge meta_data
    $deleted_meta = $wpdb->query("DELETE FROM {$prefix}postmeta WHERE post_id IN ($orphan_ids_str)");
    echo "<p>✓ Șterse postmeta: <strong>$deleted_meta</strong> rânduri</p>";
    
    // Șterge din term_relationships
    $deleted_terms = $wpdb->query("DELETE FROM {$prefix}term_relationships WHERE object_id IN ($orphan_ids_str)");
    echo "<p>✓ Șterse term_relationships: <strong>$deleted_terms</strong> rânduri</p>";
    
    // Șterge definitiv din posts (cu WHERE pentru siguranță)
    $deleted_posts = $wpdb->query("DELETE FROM {$prefix}posts WHERE ID IN ($orphan_ids_str) AND post_type = 'product'");
    echo "<p class=\"success\">✓ Șterse din wp_posts: <strong>$deleted_posts</strong> produse</p>";
}

// ==========================================
// 3. RESETEAZĂ AUTO_INCREMENT CORECT
// ==========================================
echo '<h2>3️⃣ Resetare AUTO_INCREMENT...</h2>';

// Calculează MAX(ID) pentru produse care EXISTA în meta_lookup (produse valide)
$max_valid_id = $wpdb->get_var(
    "SELECT MAX(p.ID) 
     FROM {$prefix}posts p
     WHERE p.post_type = 'product'
       AND EXISTS (
           SELECT 1 FROM {$prefix}wc_product_meta_lookup 
           WHERE product_id = p.ID
       )"
);

if (is_null($max_valid_id)) {
    $max_valid_id = 1;
}

$next_id = $max_valid_id + 1;

// Resetează AUTO_INCREMENT
$wpdb->query("ALTER TABLE {$prefix}posts AUTO_INCREMENT = $next_id");

echo "<p>";
echo "✓ MAX(ID) valid: <strong>$max_valid_id</strong><br>";
echo "✓ AUTO_INCREMENT setat la: <strong>$next_id</strong><br>";
echo "</p>";

// Verifi
$new_auto_increment = $wpdb->get_var("SELECT AUTO_INCREMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{$prefix}posts'");
echo "<p class=\"info\">🔍 Verificare: AUTO_INCREMENT acum = <strong>$new_auto_increment</strong></p>";

// ==========================================
// 4. VERIFICA INTEGRITATE TABEL META_LOOKUP
// ==========================================
echo '<h2>4️⃣ Verificare integritate meta_lookup...</h2>';

// Căuta SKU-uri duplicate (reale duplicate, nu din orfane)
$duplicate_skus = $wpdb->get_results(
    "SELECT sku, COUNT(*) as count, GROUP_CONCAT(product_id) as products
     FROM {$prefix}wc_product_meta_lookup
     WHERE sku IS NOT NULL AND sku != ''
     GROUP BY sku
     HAVING count > 1"
);

if (empty($duplicate_skus)) {
    echo '<p class="success">✅ Nu sunt SKU-uri duplicate în meta_lookup!</p>';
} else {
    echo '<p class="warning">⚠️ Găsite ' . count($duplicate_skus) . ' SKU-uri duplicate:</p>';
    echo '<table><tr><th>SKU</th><th>Apariții</th><th>Product IDs</th></tr>';
    
    foreach ($duplicate_skus as $sku_row) {
        echo "<tr>";
        echo "<td><code>{$sku_row->sku}</code></td>";
        echo "<td>{$sku_row->count}</td>";
        echo "<td>{$sku_row->products}</td>";
        echo "</tr>";
    }
    
    echo '</table>';
}

// Verifi pentru NULL SKU-uri care nu ar trebui
$null_skus = $wpdb->get_var(
    "SELECT COUNT(*) FROM {$prefix}wc_product_meta_lookup 
     WHERE sku IS NULL OR sku = ''"
);

if ($null_skus > 0) {
    echo '<p class="warning">⚠️ Găsite ' . $null_skus . ' înregistrări cu SKU NULL/gol!</p>';
    
    // Șterge NULL SKU-uri
    $wpdb->query("DELETE FROM {$prefix}wc_product_meta_lookup WHERE sku IS NULL OR sku = ''");
    echo '<p class="success">✓ Șterse NULL SKU-uri din meta_lookup</p>';
}

// ==========================================
// 5. OPTIMIZEAZĂ TABELE
// ==========================================
echo '<h2>5️⃣ Optimizare tabele...</h2>';

$wpdb->query("OPTIMIZE TABLE {$prefix}posts");
echo '<p>✓ OPTIMIZE TABLE wp_posts</p>';

$wpdb->query("OPTIMIZE TABLE {$prefix}postmeta");
echo '<p>✓ OPTIMIZE TABLE wp_postmeta</p>';

$wpdb->query("OPTIMIZE TABLE {$prefix}wc_product_meta_lookup");
echo '<p>✓ OPTIMIZE TABLE wp_wc_product_meta_lookup</p>';

// ==========================================
// 6. RAPORT FINAL
// ==========================================
echo '<h2>6️⃣ Raport final...</h2>';

$final_product_count = $wpdb->get_var("SELECT COUNT(*) FROM {$prefix}posts WHERE post_type = 'product'");
$final_meta_lookup_count = $wpdb->get_var("SELECT COUNT(*) FROM {$prefix}wc_product_meta_lookup");
$final_orphan_count = $wpdb->get_var(
    "SELECT COUNT(*)
     FROM {$prefix}posts p
     WHERE p.post_type = 'product'
       AND NOT EXISTS (
           SELECT 1 FROM {$prefix}wc_product_meta_lookup 
           WHERE product_id = p.ID
       )"
);

$final_auto_increment = $wpdb->get_var("SELECT AUTO_INCREMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{$prefix}posts'");

echo "<table>";
echo "<tr><th>Metrică</th><th>Valoare</th></tr>";
echo "<tr><td>📊 Total produse (wp_posts)</td><td><strong>$final_product_count</strong></td></tr>";
echo "<tr><td>🏷️ Înregistrări meta_lookup</td><td><strong>$final_meta_lookup_count</strong></td></tr>";
echo "<tr><td>⚠️ Produse orfane (fără meta_lookup)</td><td class=\"error\"><strong>$final_orphan_count</strong></td></tr>";
echo "<tr><td>🔢 AUTO_INCREMENT setat la</td><td><strong>$final_auto_increment</strong></td></tr>";
echo "</table>";

// Status final
echo '<h2>Status Final:</h2>';

if ($final_orphan_count == 0 && empty($duplicate_skus)) {
    echo '<p style="font-size: 18px; padding: 15px; background: #c8e6c9; border-radius: 5px;">';
    echo '<span class="success">✅ ✅ ✅ BAZA DE DATE E CURATĂ! ✅ ✅ ✅</span><br><br>';
    echo 'Poti acum:<br>';
    echo '1. Goleşte Trash-ul din WooCommerce (Produse → Trash → Delete permanently)<br>';
    echo '2. Revino la programul import și încearcă din nou!<br>';
    echo '</p>';
} else {
    echo '<p style="font-size: 16px; padding: 15px; background: #ffccbc; border-radius: 5px;">';
    echo '<span class="warning">❌ Inca sunt probleme!</span><br>';
    if ($final_orphan_count > 0) {
        echo "Produse orfane: $final_orphan_count<br>";
    }
    if (!empty($duplicate_skus)) {
        echo "SKU-uri duplicate: " . count($duplicate_skus) . "<br>";
    }
    echo 'Contacteaza suportul sau ruleaza din nou scriptul!<br>';
    echo '</p>';
}

// Link înapoi
echo '<hr>';
echo '<p><a href="javascript:history.back()" class="button">← Înapoi</a> | ';
echo '<a href="' . admin_url('admin.php?page=wc-admin') . '" class="button">WooCommerce Dashboard</a></p>';
?>
