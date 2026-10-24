import os
import sqlite3
from datetime import datetime, timedelta, timezone
import pymysql

items_data = [
    # (seller_id, title, price_cents, category, condition, location, image, quantity, views, hours_ago, description)
    (
        1,
        "Apex Pro AMOLED GPS Smartwatch",
        38000,
        "electronics",
        "New",
        "Bangsar, Kuala Lumpur",
        "img/catalog/smartwatch.jpg",
        3,
        142,
        4,
        "Brand new in sealed box. High-resolution AMOLED touchscreen, built-in GPS, multi-sport tracking, heart rate and SpO2 sensors. 14-day battery life on a single charge. Water-resistant up to 50m. Comes with magnetic fast charging cable and 1-year warranty."
    ),
    (
        1,
        "Sony WH-1000XM4 Wireless Noise-Cancelling Headphones",
        72000,
        "electronics",
        "Like New",
        "Petaling Jaya, Selangor",
        "img/catalog/headphones_xm4.jpg",
        1,
        285,
        12,
        "Industry-leading active noise cancellation with dual noise sensor technology. Premium matte black finish. Worn indoors only for a few video calls, no scratches, earpads are pristine. Includes original hard carry case, USB-C cable, and audio jack."
    ),
    (
        1,
        "Lenovo ThinkPad T480 Business Laptop (i5 / 16GB / 512GB SSD)",
        65000,
        "electronics",
        "Fair",
        "Cheras, Kuala Lumpur",
        "img/catalog/thinkpad.jpg",
        1,
        390,
        24,
        "Legendary ThinkPad build quality. Core i5-8th Gen processor, upgraded 16GB RAM and fast 512GB NVMe SSD. Has surface wear on top lid and keycaps as expected from office use, but 100% functional. Dual battery setup holds ~4 hours. Comes with original 65W USB-C charger."
    ),
    (
        1,
        "Heritage 14oz Japanese Selvedge Denim Jacket (L)",
        16500,
        "fashion",
        "Good",
        "Bangsar, Kuala Lumpur",
        "img/catalog/denim_jacket.jpg",
        1,
        178,
        16,
        "Heavyweight 14oz raw selvedge denim in deep indigo. Classic Type III silhouette with custom brass buttons and red selvedge ID along the inner placket. Natural honeycombs and subtle whiskering starting to develop. Size L, chest 42 inches."
    ),
    (
        1,
        "Nike Air Jordan 1 Retro High OG Chicago - UK 9 / US 10",
        59000,
        "fashion",
        "New",
        "Subang Jaya, Selangor",
        "img/catalog/jordans.jpg",
        2,
        412,
        6,
        "Deadstock, 100% authentic brand new in original box with extra laces. Iconic Varsity Red, Black, and White colorway. Premium tumbled leather construction. Stored in climate-controlled smoke-free room. Receipts available on request."
    ),
    (
        1,
        "Nordic Minimalist Solid Oak Round Coffee Table",
        24000,
        "home",
        "Like New",
        "Mont Kiara, Kuala Lumpur",
        "img/catalog/coffee_table.jpg",
        1,
        215,
        30,
        "Scandinavian design round coffee table crafted from solid white oak with natural satin finish. 80cm diameter, 45cm height. In like-new condition, protected with coaster mats from day one. Sturdy tapered legs, no wobbling or scratches. Self-pickup preferred."
    ),
    (
        1,
        "Dyson V11 Absolute Cordless Vacuum (Motor & Battery Good - For Parts)",
        22000,
        "home",
        "For Parts",
        "Petaling Jaya, Selangor",
        "img/catalog/dyson_vacuum.jpg",
        1,
        340,
        48,
        "Dyson V11 Absolute unit. The digital motor and lithium battery run strong, but the extension wand locking clip snapped and the dust bin hinge needs repair. Selling as-is for parts or for a DIY enthusiast who can replace the plastic clip. Includes charger and motorized head."
    ),
    (
        1,
        "Cervelo S5 Carbon Aero Road Bike (Shimano Ultegra 11-Speed)",
        285000,
        "sports",
        "Good",
        "Mont Kiara, Kuala Lumpur",
        "img/catalog/road_bike.jpg",
        1,
        530,
        18,
        "Aero carbon road bike, size 54cm (fits 172-182cm). Full Shimano Ultegra 11-speed mechanical groupset, hydraulic disc brakes, 50mm deep section carbon wheelset. Fresh Continental GP5000 tires and new Supacaz bar tape. Tuned and race-ready."
    ),
    (
        1,
        "Quechua 3-Person Waterproof Geodesic Camping Tent",
        14500,
        "sports",
        "Like New",
        "Shah Alam, Selangor",
        "img/catalog/camping_tent.jpg",
        2,
        160,
        36,
        "Easy setup 3-person dome tent with Fresh&Black heat-reflective fabric. 100% waterproof and wind-resistant up to 50 km/h. Pitched only once for an overnight camping trip in Janda Baik. Cleaned, thoroughly dried and repacked with all original pegs and guy lines."
    ),
    (
        1,
        "Harry Potter Complete Hardcover Deluxe Box Set (7 Books)",
        19500,
        "books",
        "Like New",
        "Bangsar, Kuala Lumpur",
        "img/catalog/hp_books.jpg",
        1,
        275,
        20,
        "Collectors hardcover edition box set featuring embossed foil spines and original chapter illustrations. All 7 books from Philosophers Stone to Deathly Hallows. Read once with dust jackets on, spine is uncreased, clean crisp pages with no notes or highlights."
    ),
    (
        1,
        "Vintage 90s Shonen Manga & Akira Artbook Collection",
        8500,
        "books",
        "Fair",
        "George Town, Penang",
        "img/catalog/vintage_manga.jpg",
        1,
        195,
        52,
        "Nostalgic collection of original Japanese 1990s manga tankobon (Dragon Ball, Slam Dunk, Yu Yu Hakusho) plus vintage Otomo Akira memorial artbook. Books show natural age tanning and corner shelf wear, but all pages and color plates are intact."
    ),
    (
        1,
        "Nintendo Switch OLED Model (White) + Zelda & Mario Games",
        98000,
        "toys",
        "Like New",
        "Subang Jaya, Selangor",
        "img/catalog/switch_oled.jpg",
        1,
        440,
        8,
        "Nintendo Switch OLED white console with vibrant 7-inch OLED screen. Tempered glass screen protector applied from day 1. Comes with dock, Joy-Con grip, HDMI cable, power adapter, plus physical cartridges for Zelda Tears of the Kingdom and Mario Kart 8 Deluxe."
    ),
    (
        1,
        "LEGO Icons Porsche 911 Turbo & Targa Set (10295) - Sealed",
        62000,
        "toys",
        "New",
        "Kuala Lumpur",
        "img/catalog/lego_porsche.jpg",
        2,
        310,
        10,
        "Factory sealed, brand new in mint condition box. 1,458 pieces. 2-in-1 build allows you to construct either the iconic 911 Turbo with turbocharger or the open-roof 911 Targa. Features working steering, gearstick, emergency brake, and rear-mounted flat-six engine."
    ),
    (
        1,
        "Segway Ninebot KickScooter MAX G30 (Long Range 65km)",
        145000,
        "vehicles",
        "Good",
        "Cyberjaya, Selangor",
        "img/catalog/scooter.jpg",
        1,
        380,
        22,
        "Heavy-duty electric commuter scooter with 350W motor and 10-inch puncture-resistant pneumatic tires. 65km maximum range per charge, built-in LED headlight and fast internal charger. Has minor scuffs on the deck edges, battery health at 94%. Ideal for city commuting."
    ),
    (
        1,
        "Shoei NXR / RF-1200 Full Face Motorcycle Helmet (Size M - For Parts / Project)",
        18000,
        "vehicles",
        "For Parts",
        "Johor Bahru, Johor",
        "img/catalog/helmet.jpg",
        1,
        290,
        60,
        "Authentic Shoei helmet shell in size Medium. Outer composite fiber shell is sound with surface scratches, but the inner comfort cheek pads and visor ratchet mechanism need replacement. Sold as-is strictly for track practice, display, or parts restoration."
    ),
    (
        1,
        "Vintage Seiko 5 Automatic Mechanical Watch (7S26 Blue Dial)",
        28000,
        "collectibles",
        "Good",
        "Ipoh, Perak",
        "img/catalog/watch.jpg",
        1,
        365,
        14,
        "Classic Japanese mechanical timepiece with 21-jewel automatic movement and exhibition caseback. Sunburst navy blue dial with day/date complication and luminous hands. Running accurately with ~40 hours power reserve. Solid stainless steel jubilee bracelet fitted for 7-inch wrist."
    ),
    (
        1,
        "Medicom Toy BE@RBRICK 400% Matte Black Designer Art Figure",
        89000,
        "collectibles",
        "New",
        "Bangsar, Kuala Lumpur",
        "img/catalog/art_toy.jpg",
        1,
        420,
        5,
        "100% genuine Medicom Toy BE@RBRICK 400% (28cm tall) in sleek stealth matte black. Brand new in sealed collector box with holographic authentication sticker. A striking centerpiece for any modern art or street culture collection."
    ),
    (
        1,
        "Barista Pro Stainless Steel Espresso Tool & Tamper Kit",
        13500,
        "other",
        "New",
        "Petaling Jaya, Selangor",
        "img/catalog/espresso.jpg",
        3,
        155,
        26,
        "Brand new 58mm calibrated spring-loaded coffee tamper, WDT needle distribution tool, stainless steel milk frothing pitcher (600ml), and silicone tamping mat. Food-grade SUS304 stainless steel with matte black ergonomic handles. Essential upgrade for home baristas."
    ),
    (
        1,
        "Samsonite Cosmolite 28-Inch Hard-Shell Spinner Suitcase",
        19000,
        "other",
        "Fair",
        "Kuala Lumpur",
        "img/catalog/luggage.jpg",
        1,
        230,
        40,
        "Ultra-lightweight Curv material check-in suitcase. Smooth 360-degree silent spinner wheels and TSA-approved combination lock. Exterior has noticeable airport baggage conveyor scuffs and sticker residues, but the shell is completely crack-free and interior lining is clean."
    ),
    (
        1,
        "Anker 65W GaN III Dual USB-C Fast Charger + 100W Braided Cable",
        11000,
        "other",
        "New",
        "Bangsar, Kuala Lumpur",
        "img/catalog/charger.jpg",
        5,
        175,
        2,
        "Brand new unopened retail packaging. Ultra-compact Gallium Nitride (GaN) wall adapter with 2x USB-C and 1x USB-A ports. Fast charges MacBook Pro, iPhone, iPad, and Galaxy devices simultaneously. Includes heavy-duty 1.8m braided 100W USB-C cable."
    ),
]


def populate():
    now = datetime.now(timezone.utc)
    print(f"Items to add: {len(items_data)}")

    # 1. MySQL
    m_conn = pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
        port=int(os.environ.get("MYSQL_PORT", 3306)),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", "admin"),
        db=os.environ.get("MYSQL_DB", "bazaar_db"),
        charset="utf8mb4",
        autocommit=False,
    )
    m_cur = m_conn.cursor()
    m_inserted = 0

    for seller_id, title, price_cents, category, condition, location, image, qty, views, hours_ago, desc in items_data:
        created_at = (now - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S")
        m_cur.execute("SELECT id FROM listings WHERE seller_id = %s AND title = %s", (seller_id, title))
        if not m_cur.fetchone():
            sql = """
                INSERT INTO listings (seller_id, title, description, price_cents, category, `condition`, location, image, quantity, views, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', %s)
            """
            m_cur.execute(sql, (seller_id, title, desc, price_cents, category, condition, location, image, qty, views, created_at))
            m_inserted += 1

    m_conn.commit()
    m_cur.execute("SELECT COUNT(*) FROM listings WHERE seller_id = 1")
    m_total_u1 = m_cur.fetchone()[0]
    m_conn.close()
    print(f"MySQL: Inserted {m_inserted} items. Total listings for user 1: {m_total_u1}")

    # 2. SQLite
    sqlite_path = os.path.join(os.path.dirname(__file__), "instance", "bazaar.db")
    if os.path.exists(sqlite_path):
        s_conn = sqlite3.connect(sqlite_path)
        s_cur = s_conn.cursor()
        s_inserted = 0
        for seller_id, title, price_cents, category, condition, location, image, qty, views, hours_ago, desc in items_data:
            created_at = (now - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S")
            s_cur.execute("SELECT id FROM listings WHERE seller_id = ? AND title = ?", (seller_id, title))
            if not s_cur.fetchone():
                s_cur.execute(
                    """
                    INSERT INTO listings (seller_id, title, description, price_cents, category, condition, location, image, quantity, views, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
                    """,
                    (seller_id, title, desc, price_cents, category, condition, location, image, qty, views, created_at)
                )
                s_inserted += 1
        s_conn.commit()
        s_cur.execute("SELECT COUNT(*) FROM listings WHERE seller_id = 1")
        s_total_u1 = s_cur.fetchone()[0]
        s_conn.close()
        print(f"SQLite: Inserted {s_inserted} items. Total listings for user 1: {s_total_u1}")


if __name__ == "__main__":
    populate()
