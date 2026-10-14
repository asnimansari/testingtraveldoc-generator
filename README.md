# tdg — test document generator

Generates **synthetic** passport images and travel booking PDFs for testing OCR, MRZ parsing and document-extraction pipelines. Every output comes with a ground-truth JSON file to assert against.

> **For software testing only.** Passports are an original design marked **SPECIMEN** with no national emblem or official wording. Airlines and hotels are fictional, and every PDF is watermarked **TEST DOCUMENT – NOT VALID FOR TRAVEL**. Do not use these files as, or alter them to look like, real identity or travel documents.

## What it generates

For each synthetic traveller:

| File | Contents |
|---|---|
| `<passport_no>-01.png` | Passport data page: ICAO TD3 layout, 300 DPI, two-line MRZ in OCR-B |
| `<passport_no>-02.png` | Address page: parents' and spouse's names, address, file number |
| `passport.json` | All passport fields, both MRZ lines, and the result of each check digit |
| `eticket_<PNR>.pdf` | E-ticket receipt (3 fictional-airline layouts), with a text layer |
| `hotel_<PNR>.pdf` | Hotel confirmation (2 layouts), shared by everyone on the booking |
| `booking_<PNR>.json` | Flights, fares, hotel, and every passenger's ticket and passport numbers |

The data is realistic:
- **Indian identities**: names, places of birth, and addresses where city, state and pincode agree. Passport offices and file numbers match the address.
- **Groups**: solo travellers, friend groups, and families (shared surname and address, consistent parent and spouse names, children aged 2–17) on a shared PNR.
- **Real routes** from DEL, BOM, BLR, MAA, COK, HYD and CCU to Thailand, Sri Lanka, Bali, Malaysia, Singapore, Vietnam and Dubai, direct or with one connection. Block times are typical for each route, and arrival times are in the correct time zone.
- **Date rules**: adults get 10-year passports and minors 5-year. Each passport is valid for at least 6 months past the return date. Bookings are issued 1–90 days before departure.
- **Fares in INR**, with YQ, YR, K3 (GST), P2 and IN taxes.

## Usage

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```bash
uv sync
uv run python -m tdg generate --count 20 --seed 42 --out ./out
```

| Flag | Default | Meaning |
|---|---|---|
| `--count` | 10 | Number of passports (travellers) |
| `--seed` | 42 | Random seed. The same seed and ref-date give byte-identical output |
| `--ref-date` | today | Trips are scheduled within the year after this date |
| `--error-rate` | 0.0 | Fraction of passports with a deliberate defect, for negative tests |
| `--out` | `out` | Output directory |

Output is grouped by passport, with a `manifest.json` at the top that indexes every file:

```
out/
  manifest.json
  K4612365/
    K4612365-01.png
    K4612365-02.png
    passport.json
    eticket_2FUZNE.pdf
    hotel_2FUZNE.pdf
    booking_2FUZNE.json
```

### Negative test cases

With `--error-rate`, some passports get one injected defect, recorded in `passport.json`:

- **`check_digit`**: one MRZ check digit is wrong (passport number, DOB, expiry or composite). `mrz_valid` is `false`.
- **`validity_under_6_months`**: the MRZ is valid, but the passport expires less than 6 months after the trip. `validity_ok` is `false`.

`expected_valid` is `true` only when the passport has neither defect.

## Tests

```bash
uv run pytest -q
```

The tests check the MRZ check digits against ICAO's published example, that each MRZ matches its JSON, the 6-month validity rule, that the PNR, names and passport numbers appear in each PDF's text layer, that output is reproducible, and that error injection works.

## Project layout

```
tdg/
  data.py       cities/pincodes, passport offices, airports, routes, airlines, hotels
  generate.py   identities, families, passports, flights, hotels (ground truth)
  mrz.py        ICAO 9303 TD3 MRZ build + validate
  passport.py   passport page rendering (Pillow)
  pdfs.py       e-ticket and hotel PDF rendering (ReportLab)
  __main__.py   CLI
  fonts/OCRB.otf
tests/
```

## Notes and limitations

- Passport page text uses Arial on macOS and falls back to DejaVu Sans, or Pillow's default font, elsewhere.
- Pincodes are drawn from each city's real range, but not every number in the range exists.
- Block times are approximate. Flight numbers, ticket numbers, PNRs and hotels are invented.
- The airline codes (`SF`, `MZ`, `C7`) may coincide with real IATA codes. They carry no real branding.

## Credits

The OCR-B font (`tdg/fonts/OCRB.otf`) is from the [ocr-b-outline](https://ctan.org/pkg/ocr-b-outline) package by Z. Wagner, based on METAFONT sources by Norbert Schwarz. It is free to use, modify and distribute without limitation.
