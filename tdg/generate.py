"""Builds the ground-truth records (people, passports, bookings). Rendering lives in passport.py / pdfs.py."""
import random
from datetime import date, datetime, timedelta, timezone

from faker import Faker

from . import mrz
from .data import AIRLINES, AIRPORTS, BLOCK, CITIES, HOTELS, OFFICE_CODES, ROUTES

PNR_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def add_years(d: date, n: int) -> date:
    try:
        return d.replace(year=d.year + n)
    except ValueError:  # 29 Feb
        return d.replace(year=d.year + n, day=28)


def age_on(dob: date, on: date) -> int:
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


class Generator:
    def __init__(self, seed: int, ref_date: date, error_rate: float = 0.0):
        self.r = random.Random(seed)
        self.fake = Faker("en_IN")
        self.fake.seed_instance(seed)
        self.ref = ref_date
        self.error_rate = error_rate
        self.used = set()

    # ---------- helpers ----------
    def unique(self, make):
        while (v := make()) in self.used:
            pass
        self.used.add(v)
        return v

    def rdate(self, start: date, end: date) -> date:
        return start + timedelta(days=self.r.randint(0, (end - start).days))

    def address(self):
        city, state, lo, hi, office = self.r.choice(CITIES)
        return {
            "line1": self.fake.building_number() + ", " + self.fake.street_name(),
            "line2": self.fake.last_name() + " " + self.r.choice(["Nagar", "Layout", "Colony", "Puram", "Vihar", "Enclave"]),
            "city": city, "state": state, "pincode": str(self.r.randint(lo, hi)),
        }, office

    def first(self, sex):
        return self.fake.first_name_male() if sex == "M" else self.fake.first_name_female()

    # ---------- people ----------
    def person(self, sex, surname, dob, address, office, father=None, mother=None, spouse=None):
        bcity = self.r.choice(CITIES)
        return {
            "sex": sex, "surname": surname.upper(), "given_names": self.first(sex).upper(),
            "dob": dob, "place_of_birth": f"{bcity[0]}, {bcity[1]}".upper(),
            "father_name": father or f"{self.first('M')} {surname}".upper(),
            "mother_name": mother or f"{self.first('F')} {surname}".upper(),
            "spouse_name": spouse or "", "address": address, "office": office,
        }

    def group(self, size, depart):
        def adult_dob(lo, hi):
            return self.rdate(add_years(depart, -hi), add_years(depart, -lo))

        if size == 1 or self.r.random() < 0.3:  # solo traveller or friends
            people = []
            for _ in range(size):
                addr, office = self.address()
                people.append(self.person(self.r.choice("MF"), self.fake.last_name(), adult_dob(22, 45), addr, office))
            return people, "solo" if size == 1 else "friends"

        surname = self.fake.last_name()
        addr, office = self.address()
        lead = self.person("M", surname, adult_dob(28, 60), addr, office)
        wife = self.person("F", surname, lead["dob"] + timedelta(days=self.r.randint(-5 * 365, 2 * 365)), addr, office,
                           father=f"{self.first('M')} {self.fake.last_name()}".upper(),
                           mother=f"{self.first('F')} {self.fake.last_name()}".upper())
        wife["spouse_name"] = f"{lead['given_names']} {surname}".upper()
        lead["spouse_name"] = f"{wife['given_names']} {surname}".upper()
        people = [lead, wife]
        for _ in range(size - 2):
            kid = self.person(self.r.choice("MF"), surname, adult_dob(2, 17), addr, office,
                              father=f"{lead['given_names']} {surname}".upper(),
                              mother=f"{wife['given_names']} {surname}".upper())
            people.append(kid)
        return people, "family"

    # ---------- passports ----------
    def passport(self, p, travel_end):
        """Issue a passport valid >= 6 months past travel_end (unless an error is injected)."""
        errors = []
        inject = self.r.random() < self.error_rate
        minor_at = lambda issue: age_on(p["dob"], issue) < 18
        if inject and age_on(p["dob"], self.ref) >= 28 and self.r.random() < 0.5:
            expiry = travel_end + timedelta(days=self.r.randint(1, 170))
            issue = add_years(expiry + timedelta(days=1), -10)
            errors.append({"type": "validity_under_6_months"})
        else:
            for _ in range(100):
                issue = self.rdate(max(p["dob"] + timedelta(days=30), add_years(self.ref, -9)), self.ref - timedelta(days=30))
                expiry = add_years(issue, 5 if minor_at(issue) else 10) - timedelta(days=1)
                if expiry >= travel_end + timedelta(days=183):
                    break
            else:
                issue = self.ref - timedelta(days=30)
                expiry = add_years(issue, 5 if minor_at(issue) else 10) - timedelta(days=1)
            if inject:
                errors.append({"type": "check_digit", "field": self.r.choice(["passport_no", "dob", "expiry", "composite"])})

        no = self.unique(lambda: self.r.choice("ABCJKLMNPRSTUVWZ") + str(self.r.randint(1000000, 9999999)))
        l1, l2 = mrz.build(no, "IND", p["surname"], p["given_names"], "IND", p["dob"], p["sex"], expiry)
        if errors and errors[0]["type"] == "check_digit":
            pos = {"passport_no": 9, "dob": 19, "expiry": 27, "composite": 43}[errors[0]["field"]]
            l2 = l2[:pos] + str((int(l2[pos]) + self.r.randint(1, 9)) % 10) + l2[pos + 1:]
        old = None
        if self.r.random() < 0.2 and not minor_at(issue):
            old_issue = add_years(issue, -10)
            if old_issue > p["dob"]:
                old = {"number": self.r.choice("EFGHJ") + str(self.r.randint(1000000, 9999999)),
                       "date_of_issue": old_issue.isoformat(), "place_of_issue": p["office"]}
        checks = mrz.validate(l2)
        validity_ok = expiry >= travel_end + timedelta(days=183)
        return {
            "type": "P", "country_code": "IND", "passport_no": no, "specimen": True,
            "surname": p["surname"], "given_names": p["given_names"], "nationality": "INDIAN", "sex": p["sex"],
            "date_of_birth": p["dob"].isoformat(), "place_of_birth": p["place_of_birth"],
            "place_of_issue": p["office"], "date_of_issue": issue.isoformat(), "date_of_expiry": expiry.isoformat(),
            "father_name": p["father_name"], "mother_name": p["mother_name"], "spouse_name": p["spouse_name"],
            "address": p["address"], "old_passport": old,
            "file_no": OFFICE_CODES[p["office"]] + str(self.r.randint(10**12, 10**13 - 1)),
            "mrz": {"line1": l1, "line2": l2, "checks": checks},
            "mrz_valid": all(checks.values()), "validity_ok": validity_ok,
            "expected_valid": all(checks.values()) and validity_ok, "injected_errors": errors,
        }

    # ---------- flights ----------
    def legs(self, a, b, day, airline, min_dep=None):
        """Flight legs a->b (direct or via), departing on `day` local time."""
        dest = b if b in ROUTES else a
        origin = a if b in ROUTES else b
        route = self.r.choice([rt for rt in ROUTES[dest] if rt[0] == origin])
        stops = [origin, route[1], dest] if route[1] else [origin, dest]
        if b not in ROUTES:
            stops.reverse()
        out, t = [], None
        for x, y in zip(stops, stops[1:]):
            ox, oy = AIRPORTS[x][3], AIRPORTS[y][3]
            if t is None:
                local = datetime.combine(day, datetime.min.time()) + timedelta(minutes=self.r.randrange(5, 24 * 60 - 5, 5))
                dep = (local - timedelta(minutes=ox)).replace(tzinfo=timezone.utc)
            else:
                dep = t + timedelta(minutes=self.r.randrange(90, 245, 5))
            block = BLOCK.get((x, y)) or BLOCK[(y, x)]
            block += self.r.choice([-10, -5, 0, 5, 10])
            arr = dep + timedelta(minutes=block)
            out.append({
                "flight_no": f"{airline['code']} {self.r.randint(100, 1999)}",
                "from": x, "to": y,
                "from_terminal": self.r.choice(AIRPORTS[x][4]), "to_terminal": self.r.choice(AIRPORTS[y][4]),
                "departure_local": (dep + timedelta(minutes=ox)).replace(tzinfo=None).isoformat(timespec="minutes"),
                "arrival_local": (arr + timedelta(minutes=oy)).replace(tzinfo=None).isoformat(timespec="minutes"),
                "duration_min": block, "cabin": "Economy",
                "booking_class": self.r.choice("YBMHKQVLT"),
            })
            t = arr
        return out

    def hotel(self, dest, check_in, check_out, guests, family):
        h = HOTELS[dest]
        r = self.r
        addr = h["fmt"].format(n=r.randint(1, 299), m=r.randint(1, 40), street=r.choice(h["streets"]),
                               area=r.choice(h["areas"]), pc=r.choice(h["pc"]))
        rooms = 1 if family or len(guests) <= 2 else (len(guests) + 1) // 2
        nights = (check_out - check_in).days
        rate = r.randrange(3500, 14000, 50)
        return {
            "confirmation_no": str(self.unique(lambda: r.randint(10**9, 10**10 - 1))),
            "hotel_name": r.choice(h["names"]), "address": addr,
            "city": AIRPORTS[dest][1], "country": AIRPORTS[dest][2],
            "phone": h["phone"].format(a=r.randint(100, 999), b=r.randint(1000, 9999)),
            "check_in": check_in.isoformat(), "check_out": check_out.isoformat(), "nights": nights,
            "check_in_time": "14:00", "check_out_time": "12:00",
            "rooms": rooms,
            "room_type": "Family Room" if family and len(guests) > 2 else r.choice(["Deluxe Double", "Superior Twin", "Premier King"]),
            "meal_plan": r.choice(["Room Only", "Breakfast Included"]),
            "guests": guests, "rate_per_night_inr": rate, "total_inr": rate * nights * rooms,
            "fictional": True,
        }

    def booking(self, size):
        r = self.r
        dest = r.choice(list(ROUTES))
        origin = r.choice(sorted({o for o, _ in ROUTES[dest]}))
        depart = self.ref + timedelta(days=r.randint(7, 365))
        airline = r.choice(AIRLINES)
        returning = r.random() < 0.75
        outbound = self.legs(origin, dest, depart, airline)
        arrive = date.fromisoformat(outbound[-1]["arrival_local"][:10])
        stay = r.randint(3, 14)
        inbound = self.legs(dest, origin, arrive + timedelta(days=stay), airline) if returning else []
        travel_end = date.fromisoformat((inbound or outbound)[-1]["arrival_local"][:10])

        people, kind = self.group(size, depart)
        passports = [self.passport(p, travel_end) for p in people]
        pnr = self.unique(lambda: "".join(r.choice(PNR_CHARS) for _ in range(6)))
        issued = depart - timedelta(days=r.randint(1, 90))

        def title(p):
            adult = age_on(date.fromisoformat(p["date_of_birth"]), depart) >= 12
            return ("MR" if p["sex"] == "M" else "MRS" if p["spouse_name"] else "MS") if adult else \
                ("MSTR" if p["sex"] == "M" else "MISS")

        base = sum(BLOCK.get((l["from"], l["to"])) or BLOCK[(l["to"], l["from"])] for l in outbound + inbound) * 38
        passengers = []
        for p in passports:
            fare = {"base": round(base * r.uniform(0.8, 1.4), -1),
                    "YQ": r.randrange(1500, 6000, 10), "YR": r.randrange(200, 800, 10),
                    "K3": 0, "P2": r.choice([236, 415, 590]), "IN": r.choice([550, 615, 780, 1050])}
            fare["K3"] = round(fare["base"] * 0.05)  # 5% GST on economy
            fare["total"] = sum(v for k, v in fare.items())
            passengers.append({
                "title": title(p), "surname": p["surname"], "given_names": p["given_names"],
                "passport_no": p["passport_no"], "ticket_no": f"{airline['prefix']}-{r.randint(10**9, 10**10 - 1)}",
                "baggage": f"{r.choice([15, 20, 25, 30])}KG", "cabin_baggage": "7KG",
                "fare_inr": fare,
            })
        out_arr = date.fromisoformat(outbound[-1]["arrival_local"][:10])
        check_out = date.fromisoformat(inbound[0]["departure_local"][:10]) if inbound else out_arr + timedelta(days=stay)
        guests = [f"{p['title']} {p['given_names']} {p['surname']}" for p in passengers]
        return {
            "pnr": pnr, "group_type": kind, "issued_on": issued.isoformat(), "trip_type": "return" if returning else "one-way",
            "airline": {"name": airline["name"], "code": airline["code"], "fictional": True, "layout": airline["layout"]},
            "outbound": outbound, "inbound": inbound, "passengers": passengers,
            "total_fare_inr": sum(p["fare_inr"]["total"] for p in passengers),
            "hotel": self.hotel(dest, out_arr, check_out, guests, kind == "family"),
            "test_document": True,
        }, passports


def pax_counts(total: int, r: random.Random):
    """Split `total` passports into PNR group sizes, weighted towards 1-2."""
    sizes = []
    while total > 0:
        n = min(total, r.choices([1, 2, 3, 4], weights=[35, 35, 15, 15])[0])
        sizes.append(n)
        total -= n
    return sizes
