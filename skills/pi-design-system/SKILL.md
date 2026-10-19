---
name: pi-design-system
description: Apply the Pilot Institute brand design system. Use when creating PI-branded assets — thumbnails, course UI, social graphics, print materials, ads, landing pages, emails, or any Pilot Institute output. Triggers on requests mentioning PI branding, Pilot Institute design, or specific output types.
---

You are applying the Pilot Institute (PI) brand design system. The user's request is: $ARGUMENTS

---

## Step 1 — Load the design system instructions

Fetch and read the master instructions file:
https://raw.githubusercontent.com/Pilot-Institute/pi-design-system/main/Instructions.md

This file defines the Mandatory Reading Order. Follow it exactly. Use the base URL below to construct paths for each file it references:
https://raw.githubusercontent.com/Pilot-Institute/pi-design-system/main/

The two core files you will always need are:
- `reference/PI-Colour-Palette.csv` — the only authoritative source for all color values
- `design-system/DESIGN.md` — the complete 13-section design specification

---

## Step 2 — Load segment overrides (if applicable)

If the request specifies a brand segment, fetch the corresponding file:

| Segment | URL |
|---------|-----|
| Airplanes | https://raw.githubusercontent.com/Pilot-Institute/pi-design-system/main/segments/airplanes.md |
| Drones | https://raw.githubusercontent.com/Pilot-Institute/pi-design-system/main/segments/drones.md |
| Helicopters | https://raw.githubusercontent.com/Pilot-Institute/pi-design-system/main/segments/helicopters.md |
| Flight Attendant | https://raw.githubusercontent.com/Pilot-Institute/pi-design-system/main/segments/flight-attendant.md |

If no segment is specified, default to Airplanes.

---

## Step 3 — Load the relevant module (if applicable)

If the request specifies an output type, fetch the corresponding module file. Common paths:

- YouTube thumbnails: `modules/graphics/social-media/yt-thumbnails.md`
- Instagram images: `modules/graphics/social-media/ig-images.md`
- Blog graphics: `modules/graphics/social-media/blog.md`
- Emails: `modules/graphics/editorial/emails.md`
- Whitepapers: `modules/graphics/editorial/whitepapers.md`
- Lead magnets: `modules/graphics/editorial/lead-magnets.md`
- Google Slides: `modules/graphics/editorial/google-slides.md`
- Training materials: `modules/graphics/editorial/training.md`
- Webinar handouts: `modules/graphics/editorial/webinar-handouts.md`
- Trade show materials: `modules/graphics/events/tradeshow.md`
- Landing pages: `modules/graphics/events/landing-pages.md`
- Static ads: `modules/ads/static-ads.md`
- Video ads: `modules/ads/video-ads.md`
- Organic video: `modules/video/organic.md`
- Course videos: `modules/video/courses.md`
- Troubleshooting guides: `modules/troubleshooting-guides.md`

Base URL: `https://raw.githubusercontent.com/Pilot-Institute/pi-design-system/main/`

---

## Step 4 — Execute the request

If this request edits an Adobe Illustrator (.ai) file via script, read
[[illustrator-scripting]] first — its Rule 2 (apply only the changes asked
for) wins over this design system when the two disagree, and its Rule 3
is how colors from `PI-Colour-Palette.csv` get applied as global swatches
in a script, not loose CMYK; flag a color conflict instead of silently
restyling.

Apply the design system to produce the requested output.

- Every color must trace back to a row in `PI-Colour-Palette.csv` — no exceptions
- Every decision must feel distinctively Pilot Institute, not a generic brand
- Reference semantic token names, never vague descriptors like "blue" or "dark"
- If the output reads like a generic UI kit, it has failed
