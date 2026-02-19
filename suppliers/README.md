# Furnizori – config și liste SKU

Fiecare furnizor are un folder cu:
- **config.json** – configurare scraper (URL-uri, selectori, `skip_images`, login)
- **sku_list.txt** – listă URL-uri sau SKU-uri de importat (opțional)

## Regulă imagini (watermark)

La fiecare furnizor se verifică dacă **imaginile produselor au watermark**.

- **Dacă imaginile au watermark** → în `config.json` setăm **`"skip_images": true`**. Scriptul nu preluăm imagini; preluăm doar restul datelor (nume, preț, descriere, SKU/EAN, etc.).
- **Dacă imaginile nu au watermark** → **`"skip_images": false`**. Preluăm și imaginile.

După verificare pe site, actualizează `skip_images` în fișierul `config.json` al furnizorului.

## Structură config.json

Câmpuri importante:
- **name** – identificator intern (ex: `mobilesentrix`, `foneday`)
- **display_name** – nume afișat în GUI
- **base_url** – URL de bază al site-ului
- **skip_images** – `true` = nu preluăm poze (watermark), `false` = preluăm poze
- **login.required** – `true` dacă prețurile necesită login
- **selectors** – selectori CSS pentru nume, preț, descriere, imagini, SKU/EAN

Template-uri complete sunt în **ANALIZA_FURNIZORI.md** (secțiunea „Template Config.json per Furnizor”).
