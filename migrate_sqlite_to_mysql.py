import os
import sqlite3
import pymysql

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "instance", "bazaar.db")
MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "admin")
MYSQL_DB = os.environ.get("MYSQL_DB", "bazaar_db")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))

def migrate():
    if not os.path.exists(SQLITE_PATH):
        print(f"No SQLite database found at {SQLITE_PATH}.")
        return

    s_conn = sqlite3.connect(SQLITE_PATH)
    s_conn.row_factory = sqlite3.Row
    s_cur = s_conn.cursor()

    m_conn = pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        db=MYSQL_DB,
        port=MYSQL_PORT,
        autocommit=False
    )
    m_cur = m_conn.cursor()

    try:
        # 1. users
        s_cur.execute("SELECT id, username, email, password_hash, bio, location, created_at FROM users ORDER BY id")
        users = s_cur.fetchall()
        for u in users:
            m_cur.execute(
                """
                INSERT INTO users (id, username, email, password_hash, bio, location, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE username=VALUES(username), email=VALUES(email)
                """,
                (u['id'], u['username'], u['email'], u['password_hash'], u['bio'], u['location'], u['created_at'])
            )
        print(f"Migrated {len(users)} users.")

        # 2. listings
        s_cur.execute(
            """
            SELECT id, seller_id, title, description, price_cents, category, condition, location, image, quantity, status, views, created_at
            FROM listings ORDER BY id
            """
        )
        listings = s_cur.fetchall()
        for l in listings:
            m_cur.execute(
                """
                INSERT INTO listings (id, seller_id, title, description, price_cents, category, `condition`, location, image, quantity, status, views, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE title=VALUES(title), views=VALUES(views), quantity=VALUES(quantity), status=VALUES(status)
                """,
                (l['id'], l['seller_id'], l['title'], l['description'], l['price_cents'], l['category'],
                 l['condition'], l['location'], l['image'], l['quantity'], l['status'], l['views'], l['created_at'])
            )
        print(f"Migrated {len(listings)} listings.")

        # 3. favorites
        s_cur.execute("SELECT user_id, listing_id FROM favorites")
        favs = s_cur.fetchall()
        for f in favs:
            m_cur.execute(
                "INSERT IGNORE INTO favorites (user_id, listing_id) VALUES (%s, %s)",
                (f['user_id'], f['listing_id'])
            )
        print(f"Migrated {len(favs)} favorites.")

        # 4. cart_items
        s_cur.execute("SELECT user_id, listing_id, qty FROM cart_items")
        carts = s_cur.fetchall()
        for c in carts:
            m_cur.execute(
                """
                INSERT INTO cart_items (user_id, listing_id, qty) VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE qty=VALUES(qty)
                """,
                (c['user_id'], c['listing_id'], c['qty'])
            )
        print(f"Migrated {len(carts)} cart_items.")

        # 5. orders
        s_cur.execute(
            """
            SELECT id, buyer_id, total_cents, ship_name, ship_phone, ship_address, ship_city, ship_postal, payment_method, note, created_at
            FROM orders ORDER BY id
            """
        )
        orders = s_cur.fetchall()
        for o in orders:
            m_cur.execute(
                """
                INSERT INTO orders (id, buyer_id, total_cents, ship_name, ship_phone, ship_address, ship_city, ship_postal, payment_method, note, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE total_cents=VALUES(total_cents)
                """,
                (o['id'], o['buyer_id'], o['total_cents'], o['ship_name'], o['ship_phone'], o['ship_address'],
                 o['ship_city'], o['ship_postal'], o['payment_method'], o['note'], o['created_at'])
            )
        print(f"Migrated {len(orders)} orders.")

        # 6. order_items
        s_cur.execute(
            """
            SELECT id, order_id, listing_id, seller_id, title, image, price_cents, qty, status
            FROM order_items ORDER BY id
            """
        )
        order_items = s_cur.fetchall()
        for oi in order_items:
            m_cur.execute(
                """
                INSERT INTO order_items (id, order_id, listing_id, seller_id, title, image, price_cents, qty, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE status=VALUES(status)
                """,
                (oi['id'], oi['order_id'], oi['listing_id'], oi['seller_id'], oi['title'], oi['image'],
                 oi['price_cents'], oi['qty'], oi['status'])
            )
        print(f"Migrated {len(order_items)} order_items.")

        # 7. messages
        s_cur.execute(
            """
            SELECT id, listing_id, sender_id, recipient_id, body, is_read, created_at
            FROM messages ORDER BY id
            """
        )
        msgs = s_cur.fetchall()
        for m in msgs:
            m_cur.execute(
                """
                INSERT INTO messages (id, listing_id, sender_id, recipient_id, body, is_read, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE is_read=VALUES(is_read)
                """,
                (m['id'], m['listing_id'], m['sender_id'], m['recipient_id'], m['body'], m['is_read'], m['created_at'])
            )
        print(f"Migrated {len(msgs)} messages.")

        m_conn.commit()
        print("Data migration committed successfully!")

    except Exception as e:
        m_conn.rollback()
        print("Migration failed, rolled back:", e)
        raise
    finally:
        s_conn.close()
        m_conn.close()

if __name__ == "__main__":
    migrate()
