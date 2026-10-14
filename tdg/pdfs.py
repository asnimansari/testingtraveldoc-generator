"""Render text-layer PDFs: e-ticket receipts (3 airline layouts) and hotel confirmations (2 layouts)."""
from datetime import date, datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from .data import AIRPORTS

PW, PH = A4
FOOTER = "TEST DOCUMENT - NOT VALID FOR TRAVEL. Fictional carrier / hotel generated for software testing."


def _dt(iso):
    return datetime.fromisoformat(iso).strftime("%d %b %Y %H:%M").upper()


def _d(iso):
    return date.fromisoformat(iso).strftime("%d %b %Y").upper()


def _canvas(path):
    c = Canvas(str(path), pagesize=A4, invariant=1)  # invariant: byte-identical output for the same seed
    c.setTitle("TEST DOCUMENT")
    c.saveState()  # watermark first so it sits under the content
    c.setFillColorRGB(0.85, 0.85, 0.85)
    c.setFont("Helvetica-Bold", 64)
    c.translate(PW / 2, PH / 2)
    c.rotate(35)
    c.drawCentredString(0, 0, "TEST DOCUMENT")
    c.restoreState()
    return c


def _finish(c):
    c.setFont("Helvetica-Oblique", 7.5)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawCentredString(PW / 2, 12 * mm, FOOTER)
    c.showPage()
    c.save()


def _segments(b):
    return [("OUTBOUND", s) for s in b["outbound"]] + [("RETURN", s) for s in b["inbound"]]


def _ap(code):
    return f"{AIRPORTS[code][1]} ({code})"


# ---------------- e-ticket layouts ----------------
def _banner(c, b, pax):
    r, g, bl = (0.93, 0.47, 0.13)
    c.setFillColorRGB(r, g, bl)
    c.rect(0, PH - 32 * mm, PW, 32 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(15 * mm, PH - 18 * mm, b["airline"]["name"])
    c.setFont("Helvetica", 11)
    c.drawString(15 * mm, PH - 26 * mm, "Electronic Ticket Receipt")
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(PW - 15 * mm, PH - 18 * mm, f"Booking Reference (PNR): {b['pnr']}")
    c.setFont("Helvetica", 10)
    c.drawRightString(PW - 15 * mm, PH - 26 * mm, f"Issued: {_d(b['issued_on'])}")

    y = PH - 45 * mm
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(15 * mm, y, "Passenger")
    c.setFont("Helvetica", 10)
    y -= 6 * mm
    c.drawString(15 * mm, y, f"Name: {pax['surname']}/{pax['given_names']} {pax['title']}")
    c.drawString(110 * mm, y, f"Ticket Number: {pax['ticket_no']}")
    y -= 5 * mm
    c.drawString(15 * mm, y, f"Passport: {pax['passport_no']}")
    c.drawString(110 * mm, y, f"Baggage: {pax['baggage']} checked + {pax['cabin_baggage']} cabin")

    y -= 12 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(15 * mm, y, "Itinerary")
    y -= 7 * mm
    c.setFont("Helvetica-Bold", 8.5)
    for x, h in zip((15, 32, 52, 92, 132, 170), ("", "Flight", "From", "To", "Departure", "Arrival")):
        c.drawString(x * mm, y, h)
    c.setFont("Helvetica", 8.5)
    for leg, s in _segments(b):
        y -= 6 * mm
        c.drawString(15 * mm, y, leg[:3])
        c.drawString(32 * mm, y, s["flight_no"])
        c.drawString(52 * mm, y, f"{_ap(s['from'])} {s['from_terminal']}")
        c.drawString(92 * mm, y, f"{_ap(s['to'])} {s['to_terminal']}")
        c.drawString(132 * mm, y, _dt(s["departure_local"]))
        c.drawString(170 * mm, y, _dt(s["arrival_local"])[:17])
    return y


def _gds(c, b, pax):
    c.setFont("Courier-Bold", 11)
    y = PH - 20 * mm
    lines = [
        f"{b['airline']['name'].upper()}",
        "ELECTRONIC TICKET PASSENGER ITINERARY RECEIPT",
        "",
        f"BOOKING REF: {b['pnr']:<12}DATE OF ISSUE: {_d(b['issued_on'])}",
        f"NAME: {pax['surname']}/{pax['given_names']} {pax['title']}",
        f"ETKT NBR: {pax['ticket_no']}",
        f"FOID: PP{pax['passport_no']}",
        "",
        f"{'FLIGHT':<10}{'CL':<4}{'FROM':<6}{'TO':<6}{'DEPARTURE':<20}{'ARRIVAL':<20}BAG",
    ]
    for _, s in _segments(b):
        lines.append(f"{s['flight_no']:<10}{s['booking_class']:<4}{s['from']:<6}{s['to']:<6}"
                     f"{_dt(s['departure_local']):<20}{_dt(s['arrival_local']):<20}{pax['baggage']}")
        lines.append(f"{'':<14}{AIRPORTS[s['from']][0][:22]:<24}TERMINAL {s['from_terminal']}")
    for i, line in enumerate(lines):
        c.setFont("Courier-Bold" if i < 2 else "Courier", 11 if i < 2 else 8.5)
        c.drawString(15 * mm, y, line)
        y -= 5 * mm
    return y


def _cards(c, b, pax):
    r, g, bl = (0.85, 0.33, 0.38)
    c.setFillColorRGB(r, g, bl)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(15 * mm, PH - 20 * mm, b["airline"]["name"])
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.setFont("Helvetica", 10)
    c.drawString(15 * mm, PH - 27 * mm, "Your e-ticket itinerary")
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(PW - 15 * mm, PH - 20 * mm, f"PNR  {b['pnr']}")
    c.setFont("Helvetica", 9)
    c.drawRightString(PW - 15 * mm, PH - 26 * mm, f"E-ticket  {pax['ticket_no']}")
    c.drawRightString(PW - 15 * mm, PH - 31 * mm, f"Booked on  {_d(b['issued_on'])}")
    c.drawString(15 * mm, PH - 37 * mm, f"Traveller: {pax['title']} {pax['given_names']} {pax['surname']}   |   Passport {pax['passport_no']}")
    y = PH - 45 * mm
    for leg, s in _segments(b):
        y -= 30 * mm
        c.setStrokeColorRGB(r, g, bl)
        c.roundRect(15 * mm, y, PW - 30 * mm, 26 * mm, 3 * mm)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(20 * mm, y + 20 * mm, f"{leg}  {s['flight_no']}  -  {s['cabin']} ({s['booking_class']})")
        c.setFont("Helvetica-Bold", 16)
        c.drawString(20 * mm, y + 10 * mm, s["from"])
        c.drawString(115 * mm, y + 10 * mm, s["to"])
        c.setFont("Helvetica", 8.5)
        c.drawString(20 * mm, y + 4 * mm, f"{_dt(s['departure_local'])}  T-{s['from_terminal']}")
        c.drawString(115 * mm, y + 4 * mm, f"{_dt(s['arrival_local'])}  T-{s['to_terminal']}")
        h, m = divmod(s["duration_min"], 60)
        c.drawCentredString(85 * mm, y + 11 * mm, f"---- {h}h {m:02d}m ---->")
    c.drawString(15 * mm, y - 6 * mm, f"Baggage: {pax['baggage']} check-in, {pax['cabin_baggage']} cabin")
    return y - 6 * mm


def eticket(b: dict, pax: dict, path: Path):
    c = _canvas(path)
    y = {"banner": _banner, "gds": _gds, "cards": _cards}[b["airline"]["layout"]](c, b, pax)
    y -= 12 * mm
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15 * mm, y, "Fare Details (INR)")
    c.setFont("Helvetica", 9)
    for k, v in pax["fare_inr"].items():
        y -= 5 * mm
        label = {"base": "Base Fare", "total": "Total Amount"}.get(k, f"Tax {k}")
        c.drawString(15 * mm, y, label)
        c.drawRightString(80 * mm, y, f"{v:,.2f}")
    others = [p for p in b["passengers"] if p["ticket_no"] != pax["ticket_no"]]
    if others:
        y -= 10 * mm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(15 * mm, y, "Other passengers on this booking")
        c.setFont("Helvetica", 9)
        for p in others:
            y -= 5 * mm
            c.drawString(15 * mm, y, f"{p['surname']}/{p['given_names']} {p['title']}   Ticket {p['ticket_no']}")
    _finish(c)


# ---------------- hotel layouts ----------------
def hotel(b: dict, path: Path, layout: int):
    h = b["hotel"]
    c = _canvas(path)
    rows = [
        ("Confirmation No.", h["confirmation_no"]),
        ("Hotel", h["hotel_name"]),
        ("Address", h["address"]),
        ("Phone", h["phone"]),
        ("Check-in", f"{_d(h['check_in'])} from {h['check_in_time']}"),
        ("Check-out", f"{_d(h['check_out'])} until {h['check_out_time']}"),
        ("Nights", str(h["nights"])),
        ("Rooms", f"{h['rooms']} x {h['room_type']}"),
        ("Meal Plan", h["meal_plan"]),
        ("Lead Guest", h["guests"][0]),
        ("Rate per Night", f"INR {h['rate_per_night_inr']:,.2f}"),
        ("Total Amount", f"INR {h['total_inr']:,.2f}"),
    ]
    if layout == 0:  # formal letter
        c.setFont("Helvetica-Bold", 18)
        c.drawString(20 * mm, PH - 25 * mm, h["hotel_name"])
        c.setFont("Helvetica", 9)
        c.drawString(20 * mm, PH - 31 * mm, f"{h['address']}  |  {h['phone']}")
        c.setFont("Helvetica-Bold", 13)
        c.drawString(20 * mm, PH - 48 * mm, "Reservation Confirmation")
        c.setFont("Helvetica", 10)
        c.drawString(20 * mm, PH - 58 * mm, f"Dear {h['guests'][0]},")
        c.drawString(20 * mm, PH - 64 * mm, "Thank you for choosing us. We are pleased to confirm your reservation as follows:")
        y = PH - 76 * mm
        for k, v in rows:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(20 * mm, y, k)
            c.setFont("Helvetica", 10)
            c.drawString(65 * mm, y, v)
            y -= 6.5 * mm
    else:  # booking voucher
        c.setFillColorRGB(0.15, 0.4, 0.35)
        c.rect(15 * mm, PH - 35 * mm, PW - 30 * mm, 20 * mm, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(20 * mm, PH - 26 * mm, "HOTEL VOUCHER")
        c.setFont("Helvetica", 10)
        c.drawRightString(PW - 20 * mm, PH - 26 * mm, f"Booking ID {h['confirmation_no']}")
        c.setFillColorRGB(0, 0, 0)
        y = PH - 48 * mm
        for k, v in rows[1:]:
            c.setStrokeColorRGB(0.8, 0.8, 0.8)
            c.line(15 * mm, y - 2 * mm, PW - 15 * mm, y - 2 * mm)
            c.setFont("Helvetica", 8)
            c.drawString(17 * mm, y + 2 * mm, k.upper())
            c.setFont("Helvetica-Bold", 10)
            c.drawString(60 * mm, y + 1.5 * mm, v)
            y -= 9 * mm
    y -= 6 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y, "Guests")
    c.setFont("Helvetica", 10)
    for g in h["guests"]:
        y -= 5.5 * mm
        c.drawString(20 * mm, y, g)
    y -= 10 * mm
    c.setFont("Helvetica-Oblique", 8.5)
    c.drawString(20 * mm, y, f"Flight reference: {b['airline']['name']} PNR {b['pnr']}. Free cancellation up to 48 hours before check-in.")
    _finish(c)
