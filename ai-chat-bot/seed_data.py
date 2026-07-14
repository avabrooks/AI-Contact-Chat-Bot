"""
Populate assets.db with realistic SAMPLE data so the chatbot is demo-able
immediately. Priority order matches the rollout plan: computers get the
richest data, then monitors/monitor arms, then docks, then cables.

Replace this with a real loader once you have export access to the
company's device management system (see README.md).
"""

import random
from datetime import date, timedelta

from database import get_connection, init_db

random.seed(42)

EMPLOYEES = [
    ("Avan Brooks", "avan.brooks@company.com", "IT"),
    ("Jamie Chen", "jamie.chen@company.com", "Engineering"),
    ("Priya Patel", "priya.patel@company.com", "Engineering"),
    ("Marcus Lee", "marcus.lee@company.com", "Engineering"),
    ("Sofia Ramirez", "sofia.ramirez@company.com", "Design"),
    ("Derek Kim", "derek.kim@company.com", "Sales"),
    ("Hannah Wolfe", "hannah.wolfe@company.com", "Sales"),
    ("Owen Bailey", "owen.bailey@company.com", "Marketing"),
    ("Grace Nolan", "grace.nolan@company.com", "Marketing"),
    ("Tyler Osei", "tyler.osei@company.com", "Finance"),
    ("Nina Volkov", "nina.volkov@company.com", "Finance"),
    ("Ravi Shankar", "ravi.shankar@company.com", "HR"),
    ("Elena Kowalski", "elena.kowalski@company.com", "HR"),
    ("Sam Fitzgerald", "sam.fitzgerald@company.com", "Operations"),
    ("Chloe Bennett", "chloe.bennett@company.com", "Operations"),
    ("Liam O'Connor", "liam.oconnor@company.com", "Engineering"),
    ("Maya Singh", "maya.singh@company.com", "Design"),
    ("Jonah Fisher", "jonah.fisher@company.com", "Sales"),
    ("Aisha Mohammed", "aisha.mohammed@company.com", "IT"),
    ("Noah Petrov", "noah.petrov@company.com", "Engineering"),
]

LOCATIONS = ["HQ - Floor 2", "HQ - Floor 3", "HQ - Floor 4", "Remote", "Austin Office"]

COMPUTER_MODELS = [
    ("Dell", "Latitude 5440"),
    ("Dell", "Latitude 7450"),
    ("Apple", "MacBook Pro 14 (M3)"),
    ("Apple", "MacBook Pro 16 (M3 Pro)"),
    ("Apple", "MacBook Air 13 (M2)"),
    ("Lenovo", "ThinkPad T14"),
    ("HP", "EliteBook 840"),
]

MONITOR_MODELS = [
    ("Dell", "UltraSharp U2723QE"),
    ("Dell", "P2422H"),
    ("LG", "27UL850-W"),
    ("Samsung", "Odyssey G7"),
    ("Apple", "Studio Display"),
]

MONITOR_ARM_MODELS = [
    ("Ergotron", "LX Single Monitor Arm"),
    ("Ergotron", "LX Dual Monitor Arm"),
    ("Fully", "Jarvis Monitor Arm"),
    ("HumanScale", "M8.1"),
]

DOCK_MODELS = [
    ("Dell", "WD22TB4"),
    ("CalDigit", "TS4"),
    ("Anker", "PowerExpand Elite"),
    ("Kensington", "SD5750T"),
]

CABLES = [
    ("HDMI", "HDMI 2.1, 6ft", 40, 25),
    ("USB-C to USB-C", "USB-C 100W charge/data, 6ft", 60, 38),
    ("DisplayPort", "DisplayPort 1.4, 6ft", 25, 14),
    ("Ethernet (Cat6)", "Cat6 patch cable, 10ft", 50, 33),
    ("USB-A to USB-C", "USB-A to USB-C, 3ft", 35, 20),
    ("USB-C to Lightning", "USB-C to Lightning, 3ft", 20, 9),
    ("Thunderbolt 4", "Thunderbolt 4, 3ft", 15, 6),
    ("Power Cable (C13)", "Standard IEC C13 power cable", 45, 30),
]


def random_date(start_year=2021, end_year=2025):
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, delta))).isoformat()


def make_serial(prefix, i):
    return f"{prefix}-{i:05d}"


def seed():
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM assets")
    cur.execute("DELETE FROM cable_inventory")

    serial_counter = 1

    def insert_asset(asset_type, make, model, assigned=None, status="assigned"):
        nonlocal serial_counter
        prefix = {"computer": "CMP", "monitor": "MON", "monitor_arm": "ARM", "dock": "DOK"}[asset_type]
        serial = make_serial(prefix, serial_counter)
        serial_counter += 1
        if assigned:
            name, email, dept = assigned
        else:
            name = email = dept = None
        cur.execute(
            """INSERT INTO assets
               (asset_type, make, model, serial_number, assigned_to, assigned_email,
                department, status, location, purchase_date, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                asset_type, make, model, serial, name, email, dept, status,
                random.choice(LOCATIONS), random_date(), None,
            ),
        )

    # --- Computers: one per employee, plus a handful of spares in stock ---
    for emp in EMPLOYEES:
        make, model = random.choice(COMPUTER_MODELS)
        insert_asset("computer", make, model, assigned=emp, status="assigned")
    for _ in range(6):
        make, model = random.choice(COMPUTER_MODELS)
        insert_asset("computer", make, model, assigned=None, status="available")
    # a couple in repair
    for _ in range(2):
        make, model = random.choice(COMPUTER_MODELS)
        insert_asset("computer", make, model, assigned=None, status="in_repair")

    # --- Monitors: most employees have 1-2, some spares in stock ---
    for emp in EMPLOYEES:
        count = random.choice([1, 1, 2, 2, 2])
        for _ in range(count):
            make, model = random.choice(MONITOR_MODELS)
            insert_asset("monitor", make, model, assigned=emp, status="assigned")
    for _ in range(10):
        make, model = random.choice(MONITOR_MODELS)
        insert_asset("monitor", make, model, assigned=None, status="available")

    # --- Monitor arms: fewer than monitors, ~60% of employees have one ---
    for emp in EMPLOYEES:
        if random.random() < 0.6:
            make, model = random.choice(MONITOR_ARM_MODELS)
            insert_asset("monitor_arm", make, model, assigned=emp, status="assigned")
    for _ in range(8):
        make, model = random.choice(MONITOR_ARM_MODELS)
        insert_asset("monitor_arm", make, model, assigned=None, status="available")

    # --- Docks: ~50% of employees, mostly remote/hybrid folks ---
    for emp in EMPLOYEES:
        if random.random() < 0.5:
            make, model = random.choice(DOCK_MODELS)
            insert_asset("dock", make, model, assigned=emp, status="assigned")
    for _ in range(6):
        make, model = random.choice(DOCK_MODELS)
        insert_asset("dock", make, model, assigned=None, status="available")

    # --- Cables: bulk inventory ---
    for cable_type, desc, total, available in CABLES:
        cur.execute(
            """INSERT INTO cable_inventory
               (cable_type, description, quantity_total, quantity_available, location)
               VALUES (?,?,?,?,?)""",
            (cable_type, desc, total, available, "HQ - Supply Closet"),
        )

    conn.commit()
    conn.close()
    print("Seeded sample data into assets.db")


if __name__ == "__main__":
    seed()
