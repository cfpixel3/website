import app

client = app.app.test_client()

print("1. Testing Index Route...")
res = client.get("/")
assert res.status_code == 200, f"Index failed: {res.status_code}"
assert b"Bazaar" in res.data
print("   Index OK!")

print("2. Testing Browse Route...")
res = client.get("/browse?q=camera")
assert res.status_code == 200, f"Browse query failed: {res.status_code}"
assert b"Camera" in res.data
print("   Browse search OK!")

res = client.get("/browse?category=electronics")
assert res.status_code == 200
print("   Browse category filter OK!")

print("3. Testing Listing Detail...")
res = client.get("/listing/1")
assert res.status_code == 200
assert b"Vintage 35mm Rangefinder" in res.data
print("   Listing detail OK!")

print("4. Testing User Registration & Login...")
with client:
    # Get register page to obtain CSRF token
    res = client.get("/register")
    assert res.status_code == 200
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    
    # Register a new user
    import time
    uname = f"testuser_{int(time.time())}"
    email = f"{uname}@example.com"
    res = client.post("/register", data={
        "csrf_token": token,
        "username": uname,
        "email": email,
        "password": "Password123!",
        "confirm": "Password123!"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert uname.encode() in res.data
    print(f"   Registered and logged in user: {uname}")

    # Check account page
    res = client.get("/account")
    assert res.status_code == 200
    assert uname.encode() in res.data

    # 5. Sell a new item
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    res = client.post("/sell", data={
        "csrf_token": token,
        "title": "MySQL Tested Mechanical Keyboard",
        "description": "Tested on MySQL 8.0 with InnoDB and utf8mb4 collation.",
        "price": "149.90",
        "category": "electronics",
        "condition": "New",
        "location": "Kuala Lumpur",
        "quantity": "5"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"MySQL Tested Mechanical Keyboard" in res.data
    print("   Created listing on MySQL OK!")

    # 6. Add to cart & Checkout
    # Listing 1 is owned by seller 1 (bryantc.official), current user is testuser, so can buy!
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    res = client.post("/cart/add/1", data={"csrf_token": token, "qty": "1"}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Cart" in res.data
    print("   Added item to cart OK!")

    res = client.get("/cart")
    assert res.status_code == 200
    assert b"Vintage 35mm Rangefinder" in res.data

    # Checkout
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    res = client.post("/checkout", data={
        "csrf_token": token,
        "ship_name": "Test Buyer",
        "ship_phone": "0123456789",
        "ship_address": "123 Jalan Ampang",
        "ship_city": "Kuala Lumpur",
        "ship_postal": "50450",
        "payment_method": "Cash on delivery",
        "note": "Please leave at front door."
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Order placed" in res.data or b"Order #" in res.data
    print("   Checkout transaction on MySQL OK!")

    # 7. Check orders page
    res = client.get("/orders")
    assert res.status_code == 200
    assert b"Order #" in res.data or b"Vintage 35mm" in res.data
    print("   Orders page OK!")

    # 8. Send message to seller 1
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    res = client.post("/listing/1/message", data={
        "csrf_token": token,
        "body": "Hi Bryant, is this item still available?"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Hi Bryant, is this item still available?" in res.data
    print("   Message seller on MySQL OK!")

    # Check inbox
    res = client.get("/messages")
    assert res.status_code == 200
    print("   Inbox OK!")

    # 9. Clean up test data so database remains clean
    with app.app.app_context():
        db = app.get_db()
        test_u = app.query("SELECT id FROM users WHERE username = ?", (uname,), one=True)
        if test_u:
            t_uid = test_u["id"]
            db.execute("DELETE FROM messages WHERE sender_id = ? OR recipient_id = ?", (t_uid, t_uid))
            db.execute("DELETE FROM order_items WHERE seller_id = ? OR order_id IN (SELECT id FROM orders WHERE buyer_id = ?)", (t_uid, t_uid))
            db.execute("DELETE FROM orders WHERE buyer_id = ?", (t_uid,))
            db.execute("DELETE FROM cart_items WHERE user_id = ?", (t_uid,))
            db.execute("DELETE FROM favorites WHERE user_id = ?", (t_uid,))
            db.execute("DELETE FROM listings WHERE seller_id = ?", (t_uid,))
            db.execute("DELETE FROM users WHERE id = ?", (t_uid,))
            # Restore listing 1 stock and active status
            db.execute("UPDATE listings SET status = 'active', quantity = 1 WHERE id = 1")
            db.commit()
            print(f"   Cleaned up temporary test user: {uname}")

print("\nALL END-TO-END TESTS PASSED ON MYSQL BAZAAR_DB!")

