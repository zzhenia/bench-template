---
name: flight-search
description: Find flights for one of Zhenia's trips — cheapest, direct when a direct exists, one row per real flight with a link that opens that exact flight. Use before pricing any trip leg or writing flights into the trip planning sheet.
---

# Flight search

Zhenia looks at the cheapest flight, direct whenever one exists. A list with anything else
in it is a failed list. The rules and their numbers are in
`tools/on-demand/travel-planner/eval.md`; the script below applies them. Change a rule in
both or in neither.

## Run

```sh
cd ~/ZV-Bench/tools/on-demand/travel-planner
python3 flight_search.py trip_<name>.json          # writes deals_<name>.json + raw_<name>.json
python3 find_deals.py deals_<name>.json            # first time: appends to the trip planning sheet
python3 find_deals.py deals_<name>.json --at ROW --replace N   # refresh: replaces the N rows at ROW
```

`trip_<name>.json` lists the legs: a title, `from` and `to` as comma-separated airport
codes (all airports of a city together: `JFK,EWR,LGA`, `SFO,SJC,OAK`), and every date in the
window. When the order of stops is open, write each ordering as its own legs ("A: …",
"B: …") so both are priced. Copy `trip_usa3_26.json`.

Before `--replace`, read the rows you are about to delete: they must be the old list and
nothing Zhenia ticked (columns B, C).

## What the script does

- One SerpApi `google_flights` search per leg per date (one-way, max 1 stop, GBP).
  `SERPAPI_KEY` is in `config/keys.env`; the free plan has 250 searches a month, so state
  the count in your report.
- Drops 2+ stops, long or overnight layovers, and flights far slower than the leg's fastest.
  Keeps direct flights, and one-stop flights only when they are clearly cheaper than the
  cheapest direct. `raw_<name>.json` has every flight with the reason it was kept or dropped.
- Builds a Google Flights link to the exact flight and fetches it to confirm the flight
  numbers are on the page. A row whose link fails is not listed.

## Report

Per ordering: the legs with flight numbers and prices, the total (the sum of those rows,
nothing else), and one recommendation line. Then the searches used. Run `eval.md` on the
sheet before reporting.

Prices are Google Flights prices; Skyscanner may differ for the same flight, so Zhenia
matches on the flight number. Copa rejects Revolut. Never book or pay.
