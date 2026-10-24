"""
Bazaar - a marketplace for buying and selling.

Run:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000
"""
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from functools import wraps

import pymysql
import pymysql.cursors
from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(INSTANCE_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Load environment variables from .env if present
def _load_env_file():
    env_file = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k and k not in os.environ:
                    os.environ[k] = v

_load_env_file()

# MySQL Database configuration
MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "admin")
MYSQL_DB = os.environ.get("MYSQL_DB", "bazaar_db")


def _load_secret_key():
    """Persist a random secret key so sessions survive restarts."""
    path = os.path.join(INSTANCE_DIR, "secret.key")
    if not os.path.exists(path):
        with open(path, "w") as fh:
            fh.write(secrets.token_hex(32))
    with open(path) as fh:
        return fh.read().strip()


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or _load_secret_key(),
    MAX_CONTENT_LENGTH=6 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(days=14),
)

CATEGORIES = [
    ("electronics", "Electronics", "💻"),
    ("fashion", "Fashion", "👗"),
    ("home", "Home & Garden", "🛋️"),
    ("sports", "Sports & Outdoors", "🚲"),
    ("books", "Books & Media", "📚"),
    ("toys", "Toys & Games", "🎮"),
    ("vehicles", "Vehicles", "🚗"),
    ("collectibles", "Collectibles & Art", "🎨"),
    ("other", "Other", "📦"),
]
CATEGORY_MAP = {slug: (name, icon) for slug, name, icon in CATEGORIES}
CONDITIONS = ["New", "Like New", "Good", "Fair", "For Parts"]
PAYMENT_METHODS = ["Cash on delivery", "Bank transfer", "Pay on meetup"]
ORDER_STATUSES = ["Pending", "Order Received", "Shipped", "Delivering", "Delivered"]
PER_PAGE = 12
IMAGE_SIGNATURES = {
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".webp": (b"RIFF",),
}

MALAYSIA_STATES = [
    "Kuala Lumpur",
    "Selangor",
    "Penang",
    "Johor",
    "Perak",
    "Melaka",
    "Kedah",
    "Pahang",
    "Negeri Sembilan",
    "Kelantan",
    "Terengganu",
    "Sabah",
    "Sarawak",
    "Putrajaya",
    "Perlis",
    "Labuan",
]

MALAYSIA_COORDS = {
    "bangsar": (3.1292, 101.6704, 14),
    "mont kiara": (3.1678, 101.6528, 14),
    "cheras": (3.1068, 101.7259, 14),
    "bukit bintang": (3.1466, 101.7115, 14),
    "klcc": (3.1578, 101.7119, 14),
    "kuala lumpur": (3.1390, 101.6869, 13),
    "petaling jaya": (3.1073, 101.6067, 14),
    "subang jaya": (3.0567, 101.5851, 14),
    "shah alam": (3.0738, 101.5183, 13),
    "klang": (3.0449, 101.4456, 13),
    "cyberjaya": (2.9213, 101.6559, 14),
    "putrajaya": (2.9264, 101.6964, 13),
    "selangor": (3.0738, 101.5183, 11),
    "george town": (5.4164, 100.3327, 14),
    "bayan lepas": (5.2975, 100.2676, 13),
    "penang": (5.4164, 100.3327, 12),
    "johor bahru": (1.4927, 103.7414, 13),
    "skudai": (1.5368, 103.6582, 13),
    "johor": (1.4927, 103.7414, 11),
    "ipoh": (4.5975, 101.0901, 13),
    "taiping": (4.8517, 100.7414, 13),
    "perak": (4.5975, 101.0901, 11),
    "melaka": (2.1896, 102.2501, 13),
    "alor setar": (6.1248, 100.3678, 13),
    "kedah": (6.1248, 100.3678, 11),
    "kuantan": (3.8168, 103.3317, 13),
    "pahang": (3.8168, 103.3317, 10),
    "seremban": (2.7258, 101.9424, 13),
    "negeri sembilan": (2.7258, 101.9424, 11),
    "kota bharu": (6.1254, 102.2386, 13),
    "kelantan": (6.1254, 102.2386, 11),
    "kuala terengganu": (5.3117, 103.1324, 13),
    "terengganu": (5.3117, 103.1324, 11),
    "kuching": (1.5533, 110.3592, 13),
    "miri": (4.3995, 113.9914, 13),
    "sarawak": (1.5533, 110.3592, 10),
    "kota kinabalu": (5.9804, 116.0735, 13),
    "sandakan": (5.8394, 118.1172, 13),
    "sabah": (5.9804, 116.0735, 10),
    "perlis": (6.4449, 100.2048, 12),
    "labuan": (5.2831, 115.2308, 13),
}


def get_location_coords(location_str):
    if not location_str:
        return 3.1390, 101.6869, 12
    loc_lower = location_str.lower()
    for key, (lat, lng, zoom) in MALAYSIA_COORDS.items():
        if key in loc_lower:
            return lat, lng, zoom
    return 3.1390, 101.6869, 12


TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100) NOT NULL UNIQUE,
        email VARCHAR(191) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        bio TEXT NOT NULL DEFAULT (''),
        location VARCHAR(100) NOT NULL DEFAULT '',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS listings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        seller_id INT NOT NULL,
        title VARCHAR(255) NOT NULL,
        description TEXT NOT NULL,
        price_cents INT NOT NULL,
        category VARCHAR(50) NOT NULL,
        `condition` VARCHAR(50) NOT NULL,
        location VARCHAR(100) NOT NULL DEFAULT '',
        image VARCHAR(255) NULL,
        quantity INT NOT NULL DEFAULT 1,
        status VARCHAR(50) NOT NULL DEFAULT 'active',
        views INT NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_listings_status (status, created_at),
        INDEX idx_listings_seller (seller_id),
        CONSTRAINT fk_listings_seller FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS favorites (
        user_id INT NOT NULL,
        listing_id INT NOT NULL,
        PRIMARY KEY (user_id, listing_id),
        CONSTRAINT fk_fav_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        CONSTRAINT fk_fav_listing FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS cart_items (
        user_id INT NOT NULL,
        listing_id INT NOT NULL,
        qty INT NOT NULL DEFAULT 1,
        PRIMARY KEY (user_id, listing_id),
        CONSTRAINT fk_cart_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        CONSTRAINT fk_cart_listing FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
        id INT AUTO_INCREMENT PRIMARY KEY,
        buyer_id INT NOT NULL,
        total_cents INT NOT NULL,
        ship_name VARCHAR(100) NOT NULL,
        ship_phone VARCHAR(50) NOT NULL DEFAULT '',
        ship_address TEXT NOT NULL,
        ship_city VARCHAR(100) NOT NULL,
        ship_postal VARCHAR(20) NOT NULL DEFAULT '',
        payment_method VARCHAR(50) NOT NULL,
        note TEXT NOT NULL DEFAULT (''),
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_orders_buyer (buyer_id),
        CONSTRAINT fk_orders_buyer FOREIGN KEY (buyer_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS order_items (
        id INT AUTO_INCREMENT PRIMARY KEY,
        order_id INT NOT NULL,
        listing_id INT NULL,
        seller_id INT NOT NULL,
        title VARCHAR(255) NOT NULL,
        image VARCHAR(255) NULL,
        price_cents INT NOT NULL,
        qty INT NOT NULL,
        status VARCHAR(50) NOT NULL DEFAULT 'Processing',
        INDEX idx_oi_order (order_id),
        INDEX idx_oi_seller (seller_id),
        CONSTRAINT fk_oi_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS messages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        listing_id INT NOT NULL,
        sender_id INT NOT NULL,
        recipient_id INT NOT NULL,
        body TEXT NOT NULL,
        is_read INT NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_messages_users (sender_id, recipient_id),
        CONSTRAINT fk_msg_listing FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
        CONSTRAINT fk_msg_sender FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
        CONSTRAINT fk_msg_recipient FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """
]

LISTING_SELECT = """
SELECT l.*, u.username AS seller_name,
       (SELECT COUNT(*) FROM favorites f
         WHERE f.listing_id = l.id AND f.user_id = :uid) AS is_fav
  FROM listings l JOIN users u ON u.id = l.seller_id
"""


# --------------------------------------------------------------------------
# Database helpers & MySQL Compatibility Layer
# --------------------------------------------------------------------------
class DictRow(dict):
    """Row supporting both column name access (row['col']) and integer index (row[0])."""
    def __init__(self, mapping, keys):
        super().__init__(mapping)
        self._keys = tuple(keys)

    def __getitem__(self, key):
        if isinstance(key, int):
            return super().__getitem__(self._keys[key])
        return super().__getitem__(key)


class CursorWrapper:
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = cursor.lastrowid
        self.rowcount = cursor.rowcount

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        keys = [col[0] for col in self._cursor.description]
        return DictRow(row, keys)

    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows:
            return []
        keys = [col[0] for col in self._cursor.description]
        return [DictRow(r, keys) for r in rows]

    def __iter__(self):
        return iter(self.fetchall())


def translate_sql(sql, params):
    """Translate SQLite parameter syntax (? and :name) to MySQL (%s and %(name)s)."""
    if not sql or not sql.strip():
        return sql, params
    s = sql.strip()
    if s.upper().startswith("PRAGMA"):
        return None, ()
    if s.upper().startswith("BEGIN"):
        return "START TRANSACTION", ()

    # Strip SQLite-specific ESCAPE clauses
    s = re.sub(r"\s+ESCAPE\s+['\"].*?['\"]", "", s, flags=re.IGNORECASE)

    if isinstance(params, dict):
        for k in sorted(params.keys(), key=len, reverse=True):
            s = re.sub(rf':{k}\b', f'%({k})s', s)
        return s, params
    elif isinstance(params, (tuple, list)):
        s = s.replace('?', '%s')
        return s, params
    return s, params


class MySQLWrapper:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        tsql, tparams = translate_sql(sql, params)
        if tsql is None:
            return None
        cur = self._conn.cursor(pymysql.cursors.DictCursor)
        cur.execute(tsql, tparams)
        return CursorWrapper(cur)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


def create_connection(database=MYSQL_DB):
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=database,
        charset="utf8mb4",
        autocommit=True
    )


def get_db():
    if "db" not in g:
        conn = create_connection()
        g.db = MySQLWrapper(conn)
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, params=(), one=False):
    cur = get_db().execute(sql, params)
    if cur is None:
        return None if one else []
    rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows


def init_db():
    # Ensure database exists
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        charset="utf8mb4",
        autocommit=True
    )
    with conn.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn.close()

    db = MySQLWrapper(create_connection())
    for ddl in TABLES_SQL:
        db.execute(ddl)
    has_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if not has_users:
        seed(db)
    db.commit()
    db.close()


def seed(db):
    """Fill a brand new database with official members and listings."""
    pw = generate_password_hash("test123")
    users = [
        ("bryantc.official", "bryantc@example.com", "Official seller store for electronics, vintage items, fashion and gear.", "Bangsar, Kuala Lumpur"),
        ("syazaiwany.official", "syazaiwany@example.com", "Verified buyer from Selangor. Looking for quality gear and deals.", "Petaling Jaya, Selangor"),
    ]
    for username, email, bio, loc in users:
        db.execute("INSERT INTO users (username, email, password_hash, bio, location) VALUES (?,?,?,?,?)",
                   (username, email, pw, bio, loc))
    now = datetime.now(timezone.utc)

    def ts(hours_ago):
        return (now - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S")

    items = [
        (1, "Vintage 35mm Rangefinder Film Camera", 18500, "collectibles", "Good", "Bangsar, Kuala Lumpur", "img/seed/camera.jpg", 1, 318, 3,
         "Beautiful all-metal rangefinder with a crisp 50mm f/2 lens. Shutter speeds all fire accurately, viewfinder is clear and the leatherette is intact with only light wear. Includes the original strap. A perfect companion for film photography."),
        (1, "Aether ANC Wireless Headphones", 12000, "electronics", "Like New", "Petaling Jaya, Selangor", "img/seed/headphones.jpg", 2, 254, 8,
         "Over-ear Bluetooth headphones with active noise cancellation and about 35 hours of battery. Used for a few weeks only. Comes with the hard case, USB-C charging cable and 3.5mm cable."),
        (1, "Mid-Century Walnut Lounge Armchair", 24000, "home", "Good", "Subang Jaya, Selangor", "img/seed/armchair.jpg", 1, 402, 20,
         "Gorgeous mustard fabric lounge chair with solid walnut legs and arms. Very comfortable, no stains or tears. Local pickup preferred in Subang/PJ area - fits in an SUV."),
        (1, "Trail Mountain Bike - Full Suspension", 39000, "sports", "Good", "Mont Kiara, Kuala Lumpur", "img/seed/bike.jpg", 1, 521, 30,
         "Full suspension 27.5in trail bike, size medium. 1x12 drivetrain, hydraulic disc brakes, dropper post. Just serviced with new brake pads and chain. Ready to ride Bukit Kiara trails."),
        (1, "Brown Leather Biker Jacket (M)", 9500, "fashion", "Like New", "George Town, Penang", "img/seed/jacket.jpg", 1, 187, 36,
         "Genuine cowhide leather jacket in a rich cognac brown. Size medium, fits true to size. Zippers are smooth and the lining is spotless. Worn only a handful of times."),
        (1, "Compact 75% Mechanical Keyboard - Pastel", 7500, "electronics", "New", "Johor Bahru, Johor", "img/seed/keyboard.jpg", 3, 143, 48,
         "Hot-swappable 75% layout board with linear switches, PBT keycaps and per-key RGB underglow. Bluetooth, 2.4GHz and USB-C. Brand new, opened only for photos."),
        (1, "Classic Novels Hardcover Stack (5 books)", 2800, "books", "Good", "Cheras, Kuala Lumpur", "img/seed/books.jpg", 2, 96, 60,
         "Five hardcover classics: The Old Man and the Sea, The Great Gatsby, Moby Dick, To Kill a Mockingbird and 1984. Clean pages, no highlighting. Great for a shelf or a gift."),
        (1, "Retro Handheld Game Console + 2 Controllers", 14000, "toys", "Good", "Ipoh, Perak", "img/seed/console.jpg", 1, 211, 72,
         "Retro-style handheld with a built-in library of 400+ classic games, plus two wired controllers for TV play via the HDMI/AV output. Fully working, battery lasts about 6 hours."),
        (1, "Apex Pro AMOLED GPS Smartwatch", 38000, "electronics", "New", "Bangsar, Kuala Lumpur", "img/catalog/smartwatch.jpg", 3, 142, 4,
         "Brand new in sealed box. High-resolution AMOLED touchscreen, built-in GPS, multi-sport tracking, heart rate and SpO2 sensors. 14-day battery life on a single charge. Water-resistant up to 50m. Comes with magnetic fast charging cable and 1-year warranty."),
        (1, "Sony WH-1000XM4 Wireless Noise-Cancelling Headphones", 72000, "electronics", "Like New", "Petaling Jaya, Selangor", "img/catalog/headphones_xm4.jpg", 1, 285, 12,
         "Industry-leading active noise cancellation with dual noise sensor technology. Premium matte black finish. Worn indoors only for a few video calls, no scratches, earpads are pristine. Includes original hard carry case, USB-C cable, and audio jack."),
        (1, "Lenovo ThinkPad T480 Business Laptop (i5 / 16GB / 512GB SSD)", 65000, "electronics", "Fair", "Cheras, Kuala Lumpur", "img/catalog/thinkpad.jpg", 1, 390, 24,
         "Legendary ThinkPad build quality. Core i5-8th Gen processor, upgraded 16GB RAM and fast 512GB NVMe SSD. Has surface wear on top lid and keycaps as expected from office use, but 100% functional. Dual battery setup holds ~4 hours. Comes with original 65W USB-C charger."),
        (1, "Heritage 14oz Japanese Selvedge Denim Jacket (L)", 16500, "fashion", "Good", "Bangsar, Kuala Lumpur", "img/catalog/denim_jacket.jpg", 1, 178, 16,
         "Heavyweight 14oz raw selvedge denim in deep indigo. Classic Type III silhouette with custom brass buttons and red selvedge ID along the inner placket. Natural honeycombs and subtle whiskering starting to develop. Size L, chest 42 inches."),
        (1, "Nike Air Jordan 1 Retro High OG Chicago - UK 9 / US 10", 59000, "fashion", "New", "Subang Jaya, Selangor", "img/catalog/jordans.jpg", 2, 412, 6,
         "Deadstock, 100% authentic brand new in original box with extra laces. Iconic Varsity Red, Black, and White colorway. Premium tumbled leather construction. Stored in climate-controlled smoke-free room. Receipts available on request."),
        (1, "Nordic Minimalist Solid Oak Round Coffee Table", 24000, "home", "Like New", "Mont Kiara, Kuala Lumpur", "img/catalog/coffee_table.jpg", 1, 215, 30,
         "Scandinavian design round coffee table crafted from solid white oak with natural satin finish. 80cm diameter, 45cm height. In like-new condition, protected with coaster mats from day one. Sturdy tapered legs, no wobbling or scratches. Self-pickup preferred."),
        (1, "Dyson V11 Absolute Cordless Vacuum (Motor & Battery Good - For Parts)", 22000, "home", "For Parts", "Petaling Jaya, Selangor", "img/catalog/dyson_vacuum.jpg", 1, 340, 48,
         "Dyson V11 Absolute unit. The digital motor and lithium battery run strong, but the extension wand locking clip snapped and the dust bin hinge needs repair. Selling as-is for parts or for a DIY enthusiast who can replace the plastic clip. Includes charger and motorized head."),
        (1, "Cervelo S5 Carbon Aero Road Bike (Shimano Ultegra 11-Speed)", 285000, "sports", "Good", "Mont Kiara, Kuala Lumpur", "img/catalog/road_bike.jpg", 1, 530, 18,
         "Aero carbon road bike, size 54cm (fits 172-182cm). Full Shimano Ultegra 11-speed mechanical groupset, hydraulic disc brakes, 50mm deep section carbon wheelset. Fresh Continental GP5000 tires and new Supacaz bar tape. Tuned and race-ready."),
        (1, "Quechua 3-Person Waterproof Geodesic Camping Tent", 14500, "sports", "Like New", "Shah Alam, Selangor", "img/catalog/camping_tent.jpg", 2, 160, 36,
         "Easy setup 3-person dome tent with Fresh&Black heat-reflective fabric. 100% waterproof and wind-resistant up to 50 km/h. Pitched only once for an overnight camping trip in Janda Baik. Cleaned, thoroughly dried and repacked with all original pegs and guy lines."),
        (1, "Harry Potter Complete Hardcover Deluxe Box Set (7 Books)", 19500, "books", "Like New", "Bangsar, Kuala Lumpur", "img/catalog/hp_books.jpg", 1, 275, 20,
         "Collectors hardcover edition box set featuring embossed foil spines and original chapter illustrations. All 7 books from Philosophers Stone to Deathly Hallows. Read once with dust jackets on, spine is uncreased, clean crisp pages with no notes or highlights."),
        (1, "Vintage 90s Shonen Manga & Akira Artbook Collection", 8500, "books", "Fair", "George Town, Penang", "img/catalog/vintage_manga.jpg", 1, 195, 52,
         "Nostalgic collection of original Japanese 1990s manga tankobon (Dragon Ball, Slam Dunk, Yu Yu Hakusho) plus vintage Otomo Akira memorial artbook. Books show natural age tanning and corner shelf wear, but all pages and color plates are intact."),
        (1, "Nintendo Switch OLED Model (White) + Zelda & Mario Games", 98000, "toys", "Like New", "Subang Jaya, Selangor", "img/catalog/switch_oled.jpg", 1, 440, 8,
         "Nintendo Switch OLED white console with vibrant 7-inch OLED screen. Tempered glass screen protector applied from day 1. Comes with dock, Joy-Con grip, HDMI cable, power adapter, plus physical cartridges for Zelda Tears of the Kingdom and Mario Kart 8 Deluxe."),
        (1, "LEGO Icons Porsche 911 Turbo & Targa Set (10295) - Sealed", 62000, "toys", "New", "Kuala Lumpur", "img/catalog/lego_porsche.jpg", 2, 310, 10,
         "Factory sealed, brand new in mint condition box. 1,458 pieces. 2-in-1 build allows you to construct either the iconic 911 Turbo with turbocharger or the open-roof 911 Targa. Features working steering, gearstick, emergency brake, and rear-mounted flat-six engine."),
        (1, "Segway Ninebot KickScooter MAX G30 (Long Range 65km)", 145000, "vehicles", "Good", "Cyberjaya, Selangor", "img/catalog/scooter.jpg", 1, 380, 22,
         "Heavy-duty electric commuter scooter with 350W motor and 10-inch puncture-resistant pneumatic tires. 65km maximum range per charge, built-in LED headlight and fast internal charger. Has minor scuffs on the deck edges, battery health at 94%. Ideal for city commuting."),
        (1, "Shoei NXR / RF-1200 Full Face Motorcycle Helmet (Size M - For Parts / Project)", 18000, "vehicles", "For Parts", "Johor Bahru, Johor", "img/catalog/helmet.jpg", 1, 290, 60,
         "Authentic Shoei helmet shell in size Medium. Outer composite fiber shell is sound with surface scratches, but the inner comfort cheek pads and visor ratchet mechanism need replacement. Sold as-is strictly for track practice, display, or parts restoration."),
        (1, "Vintage Seiko 5 Automatic Mechanical Watch (7S26 Blue Dial)", 28000, "collectibles", "Good", "Ipoh, Perak", "img/catalog/watch.jpg", 1, 365, 14,
         "Classic Japanese mechanical timepiece with 21-jewel automatic movement and exhibition caseback. Sunburst navy blue dial with day/date complication and luminous hands. Running accurately with ~40 hours power reserve. Solid stainless steel jubilee bracelet fitted for 7-inch wrist."),
        (1, "Medicom Toy BE@RBRICK 400% Matte Black Designer Art Figure", 89000, "collectibles", "New", "Bangsar, Kuala Lumpur", "img/catalog/art_toy.jpg", 1, 420, 5,
         "100% genuine Medicom Toy BE@RBRICK 400% (28cm tall) in sleek stealth matte black. Brand new in sealed collector box with holographic authentication sticker. A striking centerpiece for any modern art or street culture collection."),
        (1, "Barista Pro Stainless Steel Espresso Tool & Tamper Kit", 13500, "other", "New", "Petaling Jaya, Selangor", "img/catalog/espresso.jpg", 3, 155, 26,
         "Brand new 58mm calibrated spring-loaded coffee tamper, WDT needle distribution tool, stainless steel milk frothing pitcher (600ml), and silicone tamping mat. Food-grade SUS304 stainless steel with matte black ergonomic handles. Essential upgrade for home baristas."),
        (1, "Samsonite Cosmolite 28-Inch Hard-Shell Spinner Suitcase", 19000, "other", "Fair", "Kuala Lumpur", "img/catalog/luggage.jpg", 1, 230, 40,
         "Ultra-lightweight Curv material check-in suitcase. Smooth 360-degree silent spinner wheels and TSA-approved combination lock. Exterior has noticeable airport baggage conveyor scuffs and sticker residues, but the shell is completely crack-free and interior lining is clean."),
        (1, "Anker 65W GaN III Dual USB-C Fast Charger + 100W Braided Cable", 11000, "other", "New", "Bangsar, Kuala Lumpur", "img/catalog/charger.jpg", 5, 175, 2,
         "Brand new unopened retail packaging. Ultra-compact Gallium Nitride (GaN) wall adapter with 2x USB-C and 1x USB-A ports. Fast charges MacBook Pro, iPhone, iPad, and Galaxy devices simultaneously. Includes heavy-duty 1.8m braided 100W USB-C cable."),
    ]
    for seller, title, price, cat, cond, loc, img, qty, views, hours, desc in items:
        db.execute(
            "INSERT INTO listings (seller_id,title,description,price_cents,category,`condition`,location,image,quantity,views,created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (seller, title, desc, price, cat, cond, loc, img, qty, views, ts(hours)))


# --------------------------------------------------------------------------
# Auth, CSRF and template helpers
# --------------------------------------------------------------------------
@app.before_request
def load_user_and_check_csrf():
    g.user = None
    uid = session.get("user_id")
    if uid:
        g.user = query("SELECT id, username, email, bio, location, created_at FROM users WHERE id = ?", (uid,), one=True)
        if g.user is None:
            session.clear()
    if request.method == "POST":
        token = session.get("csrf_token")
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
        if not token or not sent or not secrets.compare_digest(token, sent):
            if request.is_json or request.headers.get("X-Requested-With") == "fetch":
                return jsonify(error="Session expired. Please reload the page."), 400
            flash("Your session expired. Please try again.", "error")
            return redirect(request.referrer or url_for("index"))


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            if request.headers.get("X-Requested-With") == "fetch":
                return jsonify(error="login_required", login_url=url_for("login", next=request.referrer or "/")), 401
            flash("Please log in to continue.", "info")
            return redirect(url_for("login", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)
    return wrapped


def safe_next(target):
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return None


@app.context_processor
def inject_globals():
    cart_count = unread = 0
    if g.get("user"):
        cart_count = query("SELECT COALESCE(SUM(qty),0) AS n FROM cart_items WHERE user_id = ?", (g.user["id"],), one=True)["n"]
        unread = query("SELECT COUNT(*) AS n FROM messages WHERE recipient_id = ? AND is_read = 0", (g.user["id"],), one=True)["n"]
    return dict(csrf_token=csrf_token, categories=CATEGORIES, category_map=CATEGORY_MAP,
                cart_count=cart_count, unread_count=unread, current_user=g.get("user"),
                malaysia_states=MALAYSIA_STATES)


@app.template_global()
def browse_url(args, drop=(), **overrides):
    merged = {k: v for k, v in args.items() if k not in drop}
    merged.update(overrides)
    return url_for("browse", **{k: v for k, v in merged.items() if v not in (None, "")})


@app.template_filter("money")
def money(cents):
    return "RM {:,.2f}".format((cents or 0) / 100)


def _parse_ts(value):
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    if not value:
        return datetime.now(timezone.utc)
    return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


@app.template_filter("timeago")
def timeago(value):
    try:
        delta = datetime.now(timezone.utc) - _parse_ts(value)
    except (TypeError, ValueError):
        return ""
    s = int(delta.total_seconds())
    if s < 60:
        return "just now"
    if s < 3600:
        return f"{s // 60}m ago"
    if s < 86400:
        return f"{s // 3600}h ago"
    if s < 86400 * 30:
        return f"{s // 86400}d ago"
    return _parse_ts(value).strftime("%b %d, %Y")


@app.template_filter("datefmt")
def datefmt(value):
    try:
        return _parse_ts(value).strftime("%b %d, %Y")
    except (TypeError, ValueError):
        return ""


@app.template_filter("timefmt")
def timefmt(value):
    try:
        return _parse_ts(value).strftime("%b %d, %H:%M")
    except (TypeError, ValueError):
        return ""


# --------------------------------------------------------------------------
# Image uploads
# --------------------------------------------------------------------------
def save_image(file_storage):
    """Validate and store an uploaded image. Returns (relative_path, error)."""
    if not file_storage or not file_storage.filename:
        return None, None
    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in IMAGE_SIGNATURES:
        return None, "Image must be a JPG, PNG, GIF or WEBP file."
    head = file_storage.stream.read(16)
    file_storage.stream.seek(0)
    if not any(head.startswith(sig) for sig in IMAGE_SIGNATURES[ext]):
        return None, "That file does not look like a valid image."
    if ext == ".webp" and head[8:12] != b"WEBP":
        return None, "That file does not look like a valid image."
    name = f"{secrets.token_hex(12)}{ext}"
    file_storage.save(os.path.join(UPLOAD_DIR, name))
    return f"uploads/{name}", None


def delete_image(path):
    if path and path.startswith("uploads/"):
        full = os.path.join(BASE_DIR, "static", path)
        if os.path.abspath(full).startswith(UPLOAD_DIR) and os.path.exists(full):
            os.remove(full)


@app.errorhandler(413)
def too_large(_e):
    flash("That file is too large (6 MB maximum).", "error")
    return redirect(request.referrer or url_for("index"))


@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", code=404, title="Page not found",
                           message="We could not find what you were looking for."), 404


@app.errorhandler(403)
def forbidden(_e):
    return render_template("error.html", code=403, title="Not allowed",
                           message="You do not have permission to do that."), 403


# --------------------------------------------------------------------------
# Pages: home, browse, listing detail
# --------------------------------------------------------------------------
def uid():
    return g.user["id"] if g.user else 0


@app.route("/favicon.ico")
def favicon():
    return app.send_static_file("favicon.ico")


@app.route("/")
def index():
    latest = query(LISTING_SELECT + " WHERE l.status='active' ORDER BY l.created_at DESC, l.id DESC LIMIT 8", {"uid": uid()})
    trending = query(LISTING_SELECT + " WHERE l.status='active' ORDER BY l.views DESC LIMIT 4", {"uid": uid()})
    counts = {r["category"]: r["n"] for r in query(
        "SELECT category, COUNT(*) AS n FROM listings WHERE status='active' GROUP BY category")}
    stats = {
        "members": query("SELECT COUNT(*) AS n FROM users", one=True)["n"],
        "listings": query("SELECT COUNT(*) AS n FROM listings WHERE status='active'", one=True)["n"],
        "sold": query("SELECT COALESCE(SUM(qty),0) AS n FROM order_items", one=True)["n"],
    }
    return render_template("index.html", latest=latest, trending=trending, counts=counts, stats=stats)


@app.route("/browse")
def browse():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "")
    condition = request.args.get("condition", "")
    state = request.args.get("state", "").strip()
    sort = request.args.get("sort", "newest")
    page = max(request.args.get("page", 1, type=int), 1)

    where, params = ["l.status = 'active'"], {"uid": uid()}
    if q:
        esc = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where.append("(l.title LIKE :q OR l.description LIKE :q)")
        params["q"] = f"%{esc}%"
    if category in CATEGORY_MAP:
        where.append("l.category = :category")
        params["category"] = category
    if condition in CONDITIONS:
        where.append("l.condition = :condition")
        params["condition"] = condition
    if state:
        where.append("l.location LIKE :state")
        params["state"] = f"%{state}%"
    for key, op in (("min_price", ">="), ("max_price", "<=")):
        raw = request.args.get(key, "").strip()
        if raw:
            try:
                params[key] = int(Decimal(raw) * 100)
                where.append(f"l.price_cents {op} :{key}")
            except (InvalidOperation, ValueError):
                pass
    order = {
        "newest": "l.created_at DESC, l.id DESC",
        "price_asc": "l.price_cents ASC",
        "price_desc": "l.price_cents DESC",
        "popular": "l.views DESC",
    }.get(sort, "l.created_at DESC, l.id DESC")

    clause = " WHERE " + " AND ".join(where)
    total = query("SELECT COUNT(*) AS n FROM listings l" + clause, params, one=True)["n"]
    pages = max((total + PER_PAGE - 1) // PER_PAGE, 1)
    page = min(page, pages)
    params.update(limit=PER_PAGE, offset=(page - 1) * PER_PAGE)
    results = query(LISTING_SELECT + clause + f" ORDER BY {order} LIMIT :limit OFFSET :offset", params)

    args = {k: v for k, v in request.args.items() if k != "page" and v}
    return render_template("browse.html", results=results, total=total, page=page, pages=pages,
                           q=q, category=category, condition=condition, state=state, sort=sort,
                           min_price=request.args.get("min_price", ""),
                           max_price=request.args.get("max_price", ""),
                           conditions=CONDITIONS, args=args)


@app.route("/listing/<int:listing_id>")
def listing_detail(listing_id):
    listing = query(LISTING_SELECT + " WHERE l.id = :id", {"uid": uid(), "id": listing_id}, one=True)
    if listing is None:
        abort(404)
    is_owner = g.user is not None and g.user["id"] == listing["seller_id"]
    if not is_owner:
        db = get_db()
        db.execute("UPDATE listings SET views = views + 1 WHERE id = ?", (listing_id,))
        db.commit()
    seller = query("SELECT id, username, bio, location, created_at FROM users WHERE id = ?", (listing["seller_id"],), one=True)
    seller_stats = query(
        "SELECT (SELECT COUNT(*) FROM listings WHERE seller_id = :s AND status='active') AS active,"
        "       (SELECT COALESCE(SUM(qty),0) FROM order_items WHERE seller_id = :s) AS sold", {"s": seller["id"]}, one=True)
    related = query(LISTING_SELECT + " WHERE l.status='active' AND l.category = :c AND l.id != :id"
                    " ORDER BY l.views DESC LIMIT 4", {"uid": uid(), "c": listing["category"], "id": listing_id})
    in_cart = 0
    if g.user:
        row = query("SELECT qty FROM cart_items WHERE user_id = ? AND listing_id = ?", (g.user["id"], listing_id), one=True)
        in_cart = row["qty"] if row else 0
    coords = get_location_coords(listing["location"])
    return render_template("listing.html", listing=listing, seller=seller, seller_stats=seller_stats,
                           related=related, is_owner=is_owner, in_cart=in_cart, coords=coords)


@app.route("/user/<int:user_id>")
def profile(user_id):
    seller = query("SELECT id, username, bio, location, created_at FROM users WHERE id = ?", (user_id,), one=True)
    if seller is None:
        abort(404)
    listings = query(LISTING_SELECT + " WHERE l.seller_id = :s AND l.status='active' ORDER BY l.created_at DESC",
                     {"uid": uid(), "s": user_id})
    sold = query("SELECT COALESCE(SUM(qty),0) AS n FROM order_items WHERE seller_id = ?", (user_id,), one=True)["n"]
    return render_template("profile.html", seller=seller, listings=listings, sold=sold)


# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("index"))
    form = {}
    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in ("username", "email")}
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        errors = []
        if not re.fullmatch(r"[A-Za-z0-9_.]{3,30}", form["username"]):
            errors.append("Username must be 3-30 characters: letters, numbers, dots or underscores.")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", form["email"]):
            errors.append("Please enter a valid email address.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if not errors and query("SELECT 1 FROM users WHERE username = ? OR email = ?", (form["username"], form["email"]), one=True):
            errors.append("That username or email is already registered.")
        if errors:
            for e in errors:
                flash(e, "error")
        else:
            db = get_db()
            cur = db.execute("INSERT INTO users (username, email, password_hash, bio, location) VALUES (?,?,?,?,?)",
                             (form["username"], form["email"], generate_password_hash(password), "", ""))
            db.commit()
            session.clear()
            session["user_id"] = cur.lastrowid
            session.permanent = True
            flash(f"Welcome to Bazaar, {form['username']}!", "success")
            return redirect(url_for("index"))
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("index"))
    nxt = safe_next(request.values.get("next"))
    if request.method == "POST":
        ident = request.form.get("identity", "").strip()
        user = query("SELECT * FROM users WHERE username = ? OR email = ?", (ident, ident), one=True)
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session["user_id"] = user["id"]
            session.permanent = True
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(nxt or url_for("index"))
        flash("Incorrect username/email or password.", "error")
    return render_template("login.html", next=nxt or "")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    if request.method == "POST":
        bio = request.form.get("bio", "").strip()[:300]
        location = request.form.get("location", "").strip()[:80]
        db = get_db()
        db.execute("UPDATE users SET bio = ?, location = ? WHERE id = ?", (bio, location, g.user["id"]))
        db.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("account"))
    return render_template("account.html")


# --------------------------------------------------------------------------
# Listings: create / edit / delete / status
# --------------------------------------------------------------------------
def parse_listing_form():
    f = request.form
    data = {
        "title": f.get("title", "").strip(),
        "description": f.get("description", "").strip(),
        "price": f.get("price", "").strip(),
        "category": f.get("category", ""),
        "condition": f.get("condition", ""),
        "location": f.get("location", "").strip(),
        "quantity": f.get("quantity", "1").strip(),
    }
    errors = []
    if not 3 <= len(data["title"]) <= 100:
        errors.append("Title must be between 3 and 100 characters.")
    if len(data["description"]) < 10:
        errors.append("Please add a description of at least 10 characters.")
    if len(data["description"]) > 3000:
        errors.append("Description is too long (3000 characters maximum).")
    try:
        price = Decimal(data["price"])
        if not 0 < price <= 1_000_000:
            raise InvalidOperation
        data["price_cents"] = int((price * 100).quantize(Decimal("1")))
    except InvalidOperation:
        errors.append("Enter a valid price greater than 0.")
    if data["category"] not in CATEGORY_MAP:
        errors.append("Choose a category.")
    if data["condition"] not in CONDITIONS:
        errors.append("Choose the item's condition.")
    try:
        data["quantity"] = int(data["quantity"])
        if not 1 <= data["quantity"] <= 999:
            raise ValueError
    except ValueError:
        errors.append("Quantity must be between 1 and 999.")
    data["location"] = data["location"][:80]
    return data, errors


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    data = {"quantity": 1, "location": g.user["location"]}
    if request.method == "POST":
        data, errors = parse_listing_form()
        image, img_err = save_image(request.files.get("image"))
        if img_err:
            errors.append(img_err)
        if errors:
            delete_image(image)
            for e in errors:
                flash(e, "error")
        else:
            db = get_db()
            cur = db.execute(
                "INSERT INTO listings (seller_id,title,description,price_cents,category,`condition`,location,image,quantity)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (g.user["id"], data["title"], data["description"], data["price_cents"], data["category"],
                 data["condition"], data["location"], image, data["quantity"]))
            db.commit()
            flash("Your listing is live!", "success")
            return redirect(url_for("listing_detail", listing_id=cur.lastrowid))
    return render_template("sell.html", listing=data, editing=False, conditions=CONDITIONS)


def own_listing_or_404(listing_id):
    listing = query("SELECT * FROM listings WHERE id = ?", (listing_id,), one=True)
    if listing is None:
        abort(404)
    if listing["seller_id"] != g.user["id"]:
        abort(403)
    return listing


@app.route("/listing/<int:listing_id>/edit", methods=["GET", "POST"])
@login_required
def edit_listing(listing_id):
    listing = own_listing_or_404(listing_id)
    form = dict(listing)
    form["price"] = f"{listing['price_cents'] / 100:.2f}"
    if request.method == "POST":
        data, errors = parse_listing_form()
        form.update(data)
        image, img_err = save_image(request.files.get("image"))
        if img_err:
            errors.append(img_err)
        if errors:
            delete_image(image)
            for e in errors:
                flash(e, "error")
        else:
            new_image = image or listing["image"]
            if image or request.form.get("remove_image"):
                if request.form.get("remove_image") and not image:
                    new_image = None
                delete_image(listing["image"])
            status = "active" if data["quantity"] > 0 and listing["status"] == "active" else listing["status"]
            db = get_db()
            db.execute(
                "UPDATE listings SET title=?, description=?, price_cents=?, category=?, `condition`=?, location=?,"
                " image=?, quantity=?, status=? WHERE id=?",
                (data["title"], data["description"], data["price_cents"], data["category"], data["condition"],
                 data["location"], new_image, data["quantity"], status, listing_id))
            db.commit()
            flash("Listing updated.", "success")
            return redirect(url_for("listing_detail", listing_id=listing_id))
    return render_template("sell.html", listing=form, editing=True, listing_id=listing_id,
                           has_image=bool(listing["image"]), current_image=listing["image"], conditions=CONDITIONS)


@app.route("/listing/<int:listing_id>/delete", methods=["POST"])
@login_required
def delete_listing(listing_id):
    listing = own_listing_or_404(listing_id)
    db = get_db()
    db.execute("DELETE FROM listings WHERE id = ?", (listing_id,))
    db.commit()
    delete_image(listing["image"])
    flash("Listing deleted.", "info")
    return redirect(url_for("dashboard"))


@app.route("/listing/<int:listing_id>/toggle", methods=["POST"])
@login_required
def toggle_listing(listing_id):
    listing = own_listing_or_404(listing_id)
    new_status = "sold" if listing["status"] == "active" else "active"
    db = get_db()
    if new_status == "active" and listing["quantity"] < 1:
        db.execute("UPDATE listings SET quantity = 1 WHERE id = ?", (listing_id,))
    db.execute("UPDATE listings SET status = ? WHERE id = ?", (new_status, listing_id))
    db.commit()
    flash("Marked as sold." if new_status == "sold" else "Listing is active again.", "success")
    return redirect(request.referrer or url_for("dashboard"))


# --------------------------------------------------------------------------
# Favorites
# --------------------------------------------------------------------------
@app.route("/listing/<int:listing_id>/favorite", methods=["POST"])
@login_required
def toggle_favorite(listing_id):
    if query("SELECT 1 FROM listings WHERE id = ?", (listing_id,), one=True) is None:
        abort(404)
    db = get_db()
    exists = query("SELECT 1 FROM favorites WHERE user_id = ? AND listing_id = ?", (g.user["id"], listing_id), one=True)
    if exists:
        db.execute("DELETE FROM favorites WHERE user_id = ? AND listing_id = ?", (g.user["id"], listing_id))
    else:
        db.execute("INSERT INTO favorites (user_id, listing_id) VALUES (?,?)", (g.user["id"], listing_id))
    db.commit()
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify(favorited=not exists)
    return redirect(request.referrer or url_for("favorites"))


@app.route("/favorites")
@login_required
def favorites():
    items = query(LISTING_SELECT + " JOIN favorites fv ON fv.listing_id = l.id AND fv.user_id = :uid"
                  " ORDER BY l.created_at DESC", {"uid": g.user["id"]})
    return render_template("favorites.html", items=items)


# --------------------------------------------------------------------------
# Cart and checkout
# --------------------------------------------------------------------------
def cart_rows():
    return query(
        "SELECT c.qty, l.id, l.title, l.image, l.price_cents, l.quantity AS stock, l.status, l.seller_id,"
        "       l.category, u.username AS seller_name"
        "  FROM cart_items c JOIN listings l ON l.id = c.listing_id JOIN users u ON u.id = l.seller_id"
        " WHERE c.user_id = ? ORDER BY l.title", (g.user["id"],))


@app.route("/cart")
@login_required
def cart():
    rows = cart_rows()
    total = sum(r["qty"] * r["price_cents"] for r in rows if r["status"] == "active")
    return render_template("cart.html", rows=rows, total=total)


@app.route("/cart/add/<int:listing_id>", methods=["POST"])
@login_required
def cart_add(listing_id):
    listing = query("SELECT * FROM listings WHERE id = ?", (listing_id,), one=True)
    if listing is None:
        abort(404)
    if listing["seller_id"] == g.user["id"]:
        flash("You cannot buy your own listing.", "error")
        return redirect(url_for("listing_detail", listing_id=listing_id))
    if listing["status"] != "active" or listing["quantity"] < 1:
        flash("Sorry, this item is no longer available.", "error")
        return redirect(url_for("listing_detail", listing_id=listing_id))
    qty = max(request.form.get("qty", 1, type=int), 1)
    db = get_db()
    row = query("SELECT qty FROM cart_items WHERE user_id = ? AND listing_id = ?", (g.user["id"], listing_id), one=True)
    new_qty = min((row["qty"] if row else 0) + qty, listing["quantity"])
    if row:
        db.execute("UPDATE cart_items SET qty = ? WHERE user_id = ? AND listing_id = ?", (new_qty, g.user["id"], listing_id))
    else:
        db.execute("INSERT INTO cart_items (user_id, listing_id, qty) VALUES (?,?,?)", (g.user["id"], listing_id, new_qty))
    db.commit()
    if request.form.get("buy_now"):
        return redirect(url_for("checkout"))
    flash("Added to your cart.", "success")
    return redirect(request.referrer or url_for("cart"))


@app.route("/cart/update/<int:listing_id>", methods=["POST"])
@login_required
def cart_update(listing_id):
    listing = query("SELECT quantity FROM listings WHERE id = ?", (listing_id,), one=True)
    qty = request.form.get("qty", 1, type=int)
    db = get_db()
    if listing is None or qty < 1:
        db.execute("DELETE FROM cart_items WHERE user_id = ? AND listing_id = ?", (g.user["id"], listing_id))
    else:
        qty = min(qty, max(listing["quantity"], 1))
        db.execute("UPDATE cart_items SET qty = ? WHERE user_id = ? AND listing_id = ?", (qty, g.user["id"], listing_id))
    db.commit()
    return redirect(url_for("cart"))


@app.route("/cart/remove/<int:listing_id>", methods=["POST"])
@login_required
def cart_remove(listing_id):
    db = get_db()
    db.execute("DELETE FROM cart_items WHERE user_id = ? AND listing_id = ?", (g.user["id"], listing_id))
    db.commit()
    flash("Item removed from your cart.", "info")
    return redirect(url_for("cart"))


@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    rows = [r for r in cart_rows()]
    problems = [r for r in rows if r["status"] != "active" or r["stock"] < r["qty"]]
    if not rows:
        flash("Your cart is empty.", "info")
        return redirect(url_for("browse"))
    if problems:
        flash("Some items in your cart are no longer available in that quantity. Please review your cart.", "error")
        return redirect(url_for("cart"))
    total = sum(r["qty"] * r["price_cents"] for r in rows)
    form = {"ship_name": "", "ship_phone": "", "ship_address": "", "ship_city": "", "ship_postal": "",
            "payment_method": PAYMENT_METHODS[0], "note": ""}
    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in form}
        errors = []
        if len(form["ship_name"]) < 2:
            errors.append("Please enter your full name.")
        if len(form["ship_address"]) < 5:
            errors.append("Please enter a delivery address.")
        if len(form["ship_city"]) < 2:
            errors.append("Please enter your city.")
        if form["payment_method"] not in PAYMENT_METHODS:
            errors.append("Choose a payment method.")
        if errors:
            for e in errors:
                flash(e, "error")
        else:
            db = get_db()
            try:
                db.execute("START TRANSACTION")
                items, grand = [], 0
                for r in cart_rows():
                    fresh = db.execute("SELECT * FROM listings WHERE id = ?", (r["id"],)).fetchone()
                    if fresh is None or fresh["status"] != "active" or fresh["quantity"] < r["qty"] \
                            or fresh["seller_id"] == g.user["id"]:
                        raise ValueError(f"'{r['title']}' is no longer available.")
                    items.append((fresh, r["qty"]))
                    grand += fresh["price_cents"] * r["qty"]
                cur = db.execute(
                    "INSERT INTO orders (buyer_id,total_cents,ship_name,ship_phone,ship_address,ship_city,ship_postal,payment_method,note)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (g.user["id"], grand, form["ship_name"], form["ship_phone"], form["ship_address"],
                     form["ship_city"], form["ship_postal"], form["payment_method"], form["note"][:500]))
                order_id = cur.lastrowid
                for fresh, qty in items:
                    db.execute("INSERT INTO order_items (order_id,listing_id,seller_id,title,image,price_cents,qty,status)"
                               " VALUES (?,?,?,?,?,?,?,?)",
                               (order_id, fresh["id"], fresh["seller_id"], fresh["title"], fresh["image"],
                                fresh["price_cents"], qty, "Pending"))
                    left = fresh["quantity"] - qty
                    db.execute("UPDATE listings SET quantity = ?, status = ? WHERE id = ?",
                               (left, "active" if left > 0 else "sold", fresh["id"]))
                    db.execute("DELETE FROM cart_items WHERE listing_id = ? AND user_id != ? AND qty > ?",
                               (fresh["id"], g.user["id"], left))
                db.execute("DELETE FROM cart_items WHERE user_id = ?", (g.user["id"],))
                db.commit()
            except ValueError as exc:
                db.rollback()
                flash(str(exc), "error")
                return redirect(url_for("cart"))
            except Exception:
                db.rollback()
                raise
            flash("Order placed! The sellers have been notified.", "success")
            return redirect(url_for("order_detail", order_id=order_id, new=1))
    return render_template("checkout.html", rows=rows, total=total, form=form, methods=PAYMENT_METHODS)


@app.route("/orders")
@login_required
def orders():
    rows = query("SELECT * FROM orders WHERE buyer_id = ? ORDER BY created_at DESC, id DESC", (g.user["id"],))
    result = []
    for o in rows:
        items = query("SELECT * FROM order_items WHERE order_id = ?", (o["id"],))
        result.append((o, items))
    return render_template("orders.html", orders=result)


@app.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = query("SELECT * FROM orders WHERE id = ? AND buyer_id = ?", (order_id, g.user["id"]), one=True)
    if order is None:
        abort(404)
    items = query("SELECT oi.*, u.username AS seller_name FROM order_items oi JOIN users u ON u.id = oi.seller_id"
                  " WHERE oi.order_id = ?", (order_id,))
    return render_template("order_detail.html", order=order, items=items)


# --------------------------------------------------------------------------
# Seller dashboard
# --------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    me = g.user["id"]
    listings = query("SELECT * FROM listings WHERE seller_id = ? ORDER BY created_at DESC, id DESC", (me,))
    sales = query(
        "SELECT oi.*, o.created_at, o.ship_name, o.ship_address, o.ship_city, o.ship_postal, o.ship_phone,"
        "       o.payment_method, u.username AS buyer_name, u.id AS buyer_id"
        "  FROM order_items oi JOIN orders o ON o.id = oi.order_id JOIN users u ON u.id = o.buyer_id"
        " WHERE oi.seller_id = ? ORDER BY o.created_at DESC, oi.id DESC", (me,))
    stats = {
        "active": sum(1 for l in listings if l["status"] == "active"),
        "views": sum(l["views"] for l in listings),
        "units": sum(s["qty"] for s in sales),
        "revenue": sum(s["qty"] * s["price_cents"] for s in sales),
    }
    return render_template("dashboard.html", listings=listings, sales=sales, stats=stats, statuses=ORDER_STATUSES)


@app.route("/sales/<int:item_id>/status", methods=["POST"])
@login_required
def update_sale_status(item_id):
    item = query("SELECT * FROM order_items WHERE id = ? AND seller_id = ?", (item_id, g.user["id"]), one=True)
    if item is None:
        abort(404)
    status = request.form.get("status")
    if status in ORDER_STATUSES or status == "Processing":
        db = get_db()
        db.execute("UPDATE order_items SET status = ? WHERE id = ?", (status, item_id))
        db.commit()
        messages = {
            "Order Received": f"Order for '{item['title']}' received! You can now prepare to ship it.",
            "Shipped": f"Order for '{item['title']}' marked as shipped out.",
            "Delivering": f"Order for '{item['title']}' is now marked as delivering.",
            "Delivered": f"Order for '{item['title']}' marked as delivered.",
        }
        flash(messages.get(status, f"Order status updated to {status}."), "success")
    return redirect(url_for("dashboard") + "#sales")


@app.route("/orders/item/<int:item_id>/arrived", methods=["POST"])
@login_required
def confirm_order_arrival(item_id):
    # Verify the item belongs to an order placed by the current user
    item = query(
        "SELECT oi.*, o.buyer_id FROM order_items oi JOIN orders o ON o.id = oi.order_id"
        " WHERE oi.id = ? AND o.buyer_id = ?",
        (item_id, g.user["id"]), one=True
    )
    if item is None:
        abort(404)
    db = get_db()
    db.execute("UPDATE order_items SET status = 'Delivered' WHERE id = ?", (item_id,))
    db.commit()
    flash(f"Order confirmed! You have confirmed that '{item['title']}' has arrived.", "success")
    return redirect(request.referrer or url_for("order_detail", order_id=item["order_id"]))



# --------------------------------------------------------------------------
# Messaging
# --------------------------------------------------------------------------
def clean_body(raw):
    return raw.strip()[:2000]


@app.route("/listing/<int:listing_id>/message", methods=["POST"])
@login_required
def message_seller(listing_id):
    listing = query("SELECT id, seller_id FROM listings WHERE id = ?", (listing_id,), one=True)
    if listing is None:
        abort(404)
    if listing["seller_id"] == g.user["id"]:
        flash("This is your own listing.", "error")
        return redirect(url_for("listing_detail", listing_id=listing_id))
    body = clean_body(request.form.get("body", ""))
    if not body:
        flash("Write a message first.", "error")
        return redirect(url_for("listing_detail", listing_id=listing_id))
    db = get_db()
    db.execute("INSERT INTO messages (listing_id, sender_id, recipient_id, body) VALUES (?,?,?,?)",
               (listing_id, g.user["id"], listing["seller_id"], body))
    db.commit()
    flash("Message sent to the seller.", "success")
    return redirect(url_for("conversation", listing_id=listing_id, other_id=listing["seller_id"]))


@app.route("/messages")
@login_required
def inbox():
    me = g.user["id"]
    rows = query(
        "SELECT m.*, l.title, l.image, su.username AS sender_name, ru.username AS recipient_name"
        "  FROM messages m JOIN listings l ON l.id = m.listing_id"
        "  JOIN users su ON su.id = m.sender_id JOIN users ru ON ru.id = m.recipient_id"
        " WHERE m.sender_id = ? OR m.recipient_id = ? ORDER BY m.created_at DESC, m.id DESC", (me, me))
    threads = {}
    for m in rows:
        other_id = m["recipient_id"] if m["sender_id"] == me else m["sender_id"]
        other_name = m["recipient_name"] if m["sender_id"] == me else m["sender_name"]
        key = (m["listing_id"], other_id)
        t = threads.setdefault(key, {"last": m, "other_id": other_id, "other_name": other_name, "unread": 0})
        if m["recipient_id"] == me and not m["is_read"]:
            t["unread"] += 1
    return render_template("inbox.html", threads=list(threads.values()))


@app.route("/messages/<int:listing_id>/<int:other_id>", methods=["GET", "POST"])
@login_required
def conversation(listing_id, other_id):
    me = g.user["id"]
    listing = query("SELECT l.*, u.username AS seller_name FROM listings l JOIN users u ON u.id = l.seller_id"
                    " WHERE l.id = ?", (listing_id,), one=True)
    other = query("SELECT id, username FROM users WHERE id = ?", (other_id,), one=True)
    if listing is None or other is None or other_id == me or listing["seller_id"] not in (me, other_id):
        abort(404)
    db = get_db()
    if request.method == "POST":
        body = clean_body(request.form.get("body", ""))
        if body:
            db.execute("INSERT INTO messages (listing_id, sender_id, recipient_id, body) VALUES (?,?,?,?)",
                       (listing_id, me, other_id, body))
            db.commit()
        return redirect(url_for("conversation", listing_id=listing_id, other_id=other_id) + "#end")
    db.execute("UPDATE messages SET is_read = 1 WHERE listing_id = ? AND recipient_id = ? AND sender_id = ?",
               (listing_id, me, other_id))
    db.commit()
    msgs = query("SELECT * FROM messages WHERE listing_id = ? AND"
                 " ((sender_id = ? AND recipient_id = ?) OR (sender_id = ? AND recipient_id = ?))"
                 " ORDER BY created_at, id", (listing_id, me, other_id, other_id, me))
    return render_template("conversation.html", listing=listing, other=other, msgs=msgs)


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG") == "1")
else:
    init_db()
