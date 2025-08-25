import sqlite3
import os
import json
from datetime import datetime

DB_FILE = "db/restaurant.db"

def init_db():
    os.makedirs("db", exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Bills table with payment and datetime
    cur.execute('''CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_no TEXT,
        customer_name TEXT,
        phone TEXT,
        orders TEXT,
        subtotal REAL,
        gst REAL,
        discount REAL,
        total REAL,
        payment_method TEXT,
        datetime TEXT
    )''')

    # Menu table for upload (admin)
    cur.execute('''CREATE TABLE IF NOT EXISTS menu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item TEXT UNIQUE,
        price REAL
    )''')

    # Users table
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )''')

    # Tables table for tracking occupancy
    cur.execute('''CREATE TABLE IF NOT EXISTS tables (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_number INTEGER UNIQUE,
        status TEXT DEFAULT 'Free'
    )''')

    # Initialize 10 tables if not already present
    cur.execute('SELECT COUNT(*) FROM tables')
    count = cur.fetchone()[0]
    if count < 10:
        for i in range(1, 11):
            cur.execute('INSERT OR IGNORE INTO tables (table_number, status) VALUES (?, ?)', (i, 'Free'))

    # Add default users if not exist
    cur.execute("SELECT * FROM users WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    ("admin", "admin123", "admin"))
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    ("cashier", "cashier123", "cashier"))

    conn.commit()
    conn.close()

def authenticate_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT username, role FROM users WHERE username=? AND password=?", (username, password))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"username": row[0], "role": row[1]}
    return None

def save_bill(bill):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('''INSERT INTO bills (bill_no, customer_name, phone, orders, subtotal, gst,
                    discount, total, payment_method, datetime)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (bill["bill_no"], bill["customer_name"], bill["phone"], json.dumps(bill["order"]),
                 bill["subtotal"], bill["gst"], bill["discount"], bill["total"], bill["payment_method"],
                 bill["datetime"]))
    conn.commit()
    conn.close()

def load_menu():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT item, price FROM menu")
    rows = cur.fetchall()
    conn.close()
    return {item: price for item, price in rows}

def update_menu(items):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    for item, price in items.items():
        cur.execute('INSERT OR REPLACE INTO menu (item, price) VALUES (?, ?)', (item, price))
    conn.commit()
    conn.close()

def get_all_bills():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('SELECT bill_no, customer_name, phone, total, payment_method, datetime FROM bills')
    rows = cur.fetchall()
    conn.close()
    return rows
