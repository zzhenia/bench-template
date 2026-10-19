---
name: shop-browser-search
description: Browser search and screenshot on MercadoLibre Colombia and Amazon US, return file paths to Kitty.
---

# Shop Browser Search — MercadoLibre & Amazon Screenshots

Shopbot searches for items on MercadoLibre Colombia and Amazon US, captures full-page screenshots, and reports file paths to Kitty.

## Input

Work order from Kitty with:
- Item name (English)
- Search term for MercadoLibre (Spanish)
- Search term for Amazon (English)

Example: "bombillo LED E27 12W luz cálida" (ML) and "E27 LED bulb 12W warm white" (Amazon)

## Procedure

### 1. Prepare storage

Create screenshot directory:
```bash
mkdir -p ~/.openclaw/workspace/shop/screens/$(date +%y%m%d)-<slug>/
```

where `<slug>` is a short identifier for the item (e.g., `led-bulb-e27`).

### 2. MercadoLibre Colombia search

Open browser and navigate to:
```
https://listado.mercadolibre.com.co/<spanish-term>
```

Replace spaces with `+` or `%20`. Example:
```
https://listado.mercadolibre.com.co/bombillo+LED+E27+12W+luz+c%C3%A1lida
```

**Screenshots must show:**
- Product titles
- Prices in COP
- Ratings and reviews (if visible)
- At least 1000px wide, full page height

Save as: `~/.openclaw/workspace/shop/screens/yymmdd-slug/mercadolibre-01.png`

### 3. Amazon US search

Open browser and navigate to:
```
https://amazon.com/s?k=<english-term>
```

**Before searching, ensure location is set:**
- Deliver to Colombia, or
- Set zip code to 110231 (Bogotá)

This ensures USD prices display and Colombian delivery options show.

**Screenshots must show:**
- Product titles
- Prices in USD
- Star ratings
- At least 1000px wide, full page height

Save as: `~/.openclaw/workspace/shop/screens/yymmdd-slug/amazon-01.png`

### 4. Save page text sidecars

For each screenshot, save a `.txt` file with the same name:
- **Line 1:** final page URL (after any redirects)
- **Following lines:** page's visible text (snapshot of `innerText`)

Example `mercadolibre-01.txt`:
```
https://listado.mercadolibre.com.co/bombillo+LED+E27+12W+luz+c%C3%A1lida
Bombillo LED E27 12W Luz Cálida
$45.990
★★★★★ (234 reseñas)
Envío gratis
Tienda oficial
[...]
```

The eval uses this file to check host, currency, and captcha — the box has no OCR.

### 5. Report to Kitty

Send message to `agent:kitty:main` with:
- Item name
- Screenshot file paths (one per store, one line each)

Example:
```
Shop search: bombillo LED E27 12W luz cálida

MercadoLibre: ~/.openclaw/workspace/shop/screens/260930-led-bulb-e27/mercadolibre-01.png
Amazon: ~/.openclaw/workspace/shop/screens/260930-led-bulb-e27/amazon-01.png
```

## Blockers

**If MercadoLibre returns verification wall:**
- Stop. Do not fake results.
- Report exact message to Kitty.

**If Amazon lands on wrong storefront (EUR, no USD):**
- Check location settings (Colombia or zip 110231).
- Try again.
- If still wrong, report to Kitty with screenshot of the landing page.

**If screenshots are unreadable (too small, cut off, missing prices/titles):**
- Retake with proper viewport (1000px+ wide).
- If browser viewport is too small, resize and retry.

## Done

- Screenshots saved with readable prices, titles, ratings
- File paths reported to Kitty
- Skill passes eval/shop-browser-search.sh on live test

