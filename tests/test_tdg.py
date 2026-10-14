import json
from datetime import date, timedelta

import pytest
from pypdf import PdfReader

from tdg import mrz
from tdg.__main__ import generate

REF = date(2026, 10, 15)


def test_icao_specimen_check_digits():
    # ICAO 9303 Part 4 TD3 example
    line2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
    assert all(mrz.validate(line2).values())


@pytest.fixture(scope="module")
def clean(tmp_path_factory):
    out = tmp_path_factory.mktemp("clean")
    return out, generate(12, 7, REF, 0.0, out)


def test_passports_match_mrz_and_rules(clean):
    out, m = clean
    assert len(m["passports"]) == 12
    for entry in m["passports"]:
        p = json.loads((out / entry["dir"] / "passport.json").read_text())
        l1, l2 = p["mrz"]["line1"], p["mrz"]["line2"]
        assert len(l1) == len(l2) == 44 and p["expected_valid"]
        assert all(mrz.validate(l2).values())
        assert l2[:9].rstrip("<") == p["passport_no"]
        assert l2[13:19] == date.fromisoformat(p["date_of_birth"]).strftime("%y%m%d")
        assert l2[21:27] == date.fromisoformat(p["date_of_expiry"]).strftime("%y%m%d")
        assert l1.startswith(f"P<IND{p['surname']}<<")
        b = json.loads((out / entry["dir"] / f"booking_{entry['pnr']}.json").read_text())
        end = date.fromisoformat((b["inbound"] or b["outbound"])[-1]["arrival_local"][:10])
        assert date.fromisoformat(p["date_of_expiry"]) >= end + timedelta(days=183)
        assert p["passport_no"] in [x["passport_no"] for x in b["passengers"]]
        for f in (f"{entry['passport_no']}-01.png", f"{entry['passport_no']}-02.png", f"eticket_{entry['pnr']}.pdf", f"hotel_{entry['pnr']}.pdf"):
            assert (out / entry["dir"] / f).exists()


def test_pdf_text_layer(clean):
    out, m = clean
    for entry in m["passports"]:
        d = out / entry["dir"]
        p = json.loads((d / "passport.json").read_text())
        ticket = PdfReader(d / f"eticket_{entry['pnr']}.pdf").pages[0].extract_text()
        hotel = PdfReader(d / f"hotel_{entry['pnr']}.pdf").pages[0].extract_text()
        assert entry["pnr"] in ticket and p["surname"] in ticket and p["passport_no"] in ticket
        assert p["surname"] in hotel and "TEST DOCUMENT" in hotel


def test_deterministic(tmp_path):
    generate(5, 3, REF, 0.3, tmp_path / "a")
    generate(5, 3, REF, 0.3, tmp_path / "b")
    for f in (tmp_path / "a").rglob("*.*"):
        assert f.read_bytes() == (tmp_path / "b" / f.relative_to(tmp_path / "a")).read_bytes(), f


def test_error_injection(tmp_path):
    m = generate(20, 11, REF, 1.0, tmp_path)
    for entry in m["passports"]:
        p = json.loads((tmp_path / entry["dir"] / "passport.json").read_text())
        assert not p["expected_valid"] and p["injected_errors"]
        kind = p["injected_errors"][0]["type"]
        assert (not p["mrz_valid"]) if kind == "check_digit" else (p["mrz_valid"] and not p["validity_ok"])
