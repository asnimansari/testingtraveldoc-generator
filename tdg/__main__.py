"""CLI: python -m tdg generate --count 20 --seed 42 --out ./out"""
import argparse
import json
import random
import shutil
from datetime import date
from pathlib import Path

from . import passport, pdfs
from .generate import Generator, pax_counts


def generate(count: int, seed: int, ref_date: date, error_rate: float, out: Path) -> dict:
    g = Generator(seed, ref_date, error_rate)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"seed": seed, "ref_date": ref_date.isoformat(), "error_rate": error_rate,
                "test_documents": True, "passports": [], "bookings": []}
    for i, size in enumerate(pax_counts(count, random.Random(seed))):
        b, passports = g.booking(size)
        pnr = b["pnr"]
        first_dir = None
        for p, pax in zip(passports, b["passengers"]):
            d = out / p["passport_no"]
            d.mkdir(exist_ok=True)
            p["booking_pnr"] = pnr
            passport.data_page(p, d / f"{p['passport_no']}-01.png", seed + i * 10)
            passport.address_page(p, d / f"{p['passport_no']}-02.png", seed + i * 10)
            (d / "passport.json").write_text(json.dumps(p, indent=2))
            pdfs.eticket(b, pax, d / f"eticket_{pnr}.pdf")
            if first_dir is None:
                pdfs.hotel(b, d / f"hotel_{pnr}.pdf", layout=i % 2)
                first_dir = d
            else:
                shutil.copy(first_dir / f"hotel_{pnr}.pdf", d / f"hotel_{pnr}.pdf")
            (d / f"booking_{pnr}.json").write_text(json.dumps(b, indent=2))
            manifest["passports"].append({"passport_no": p["passport_no"], "dir": p["passport_no"],
                                          "pnr": pnr, "expected_valid": p["expected_valid"]})
        manifest["bookings"].append({"pnr": pnr, "passports": [p["passport_no"] for p in passports],
                                     "airline": b["airline"]["name"], "group_type": b["group_type"]})
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main():
    ap = argparse.ArgumentParser(prog="tdg", description="Generate SPECIMEN passports and TEST travel bookings.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    gp = sub.add_parser("generate")
    gp.add_argument("--count", type=int, default=10, help="number of passports (identities)")
    gp.add_argument("--seed", type=int, default=42)
    gp.add_argument("--ref-date", type=date.fromisoformat, default=date.today(), help="YYYY-MM-DD; trips fall in the following year")
    gp.add_argument("--error-rate", type=float, default=0.0, help="fraction of passports with an injected defect")
    gp.add_argument("--out", type=Path, default=Path("out"))
    a = ap.parse_args()
    if a.count < 1 or not 0 <= a.error_rate <= 1:
        ap.error("--count must be >= 1 and --error-rate in [0, 1]")
    m = generate(a.count, a.seed, a.ref_date, a.error_rate, a.out)
    print(f"Wrote {len(m['passports'])} passports in {len(m['bookings'])} bookings to {a.out}/ (ref-date {m['ref_date']})")


if __name__ == "__main__":
    main()
