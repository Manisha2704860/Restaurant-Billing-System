import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
import sqlite3
from datetime import datetime
import pandas as pd
from fpdf import FPDF, XPos, YPos
import os
from time import strftime

# ================== Database Setup & Menu ==================
db_path = os.path.join("db", "restaurant.db")
os.makedirs("db", exist_ok=True)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS orders")
cursor.execute("DROP TABLE IF EXISTS order_items")
cursor.execute("DROP TABLE IF EXISTS menu")
cursor.execute("DROP TABLE IF EXISTS tables")

cursor.execute("""
CREATE TABLE IF NOT EXISTS menu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    category TEXT,
    price REAL,
    gst REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_type TEXT,
    table_no TEXT,
    customer_name TEXT,
    timestamp TEXT,
    total REAL,
    gst REAL,
    discount REAL,
    final_amount REAL,
    payment_method TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    item_name TEXT,
    qty INTEGER,
    price REAL
)
""")

# Tables for Dine-in
cursor.execute("""
CREATE TABLE IF NOT EXISTS tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_no TEXT UNIQUE,
    status TEXT DEFAULT 'Free'
)
""")
cursor.execute("SELECT COUNT(*) FROM tables")
if cursor.fetchone()[0] == 0:
    for i in range(1, 11):  # 10 tables
        cursor.execute("INSERT INTO tables(table_no, status) VALUES (?, 'Free')", (str(i),))


conn.commit()

def insert_sample_menu():
    cursor.execute("SELECT COUNT(*) FROM menu")
    if cursor.fetchone()[0] == 0:
        menu_items = [
            ("Pizza", "Main", 250, 5),
            ("Burger", "Main", 120, 5),
            ("Pasta", "Main", 180, 5),
            ("Coke", "Beverage", 50, 0),
            ("Ice Cream", "Dessert", 80, 0),
        ]
        cursor.executemany("INSERT INTO menu(name, category, price, gst) VALUES (?, ?, ?, ?)", menu_items)
        conn.commit()
insert_sample_menu()

# ================== Login Page ==================
USERS = {
    "admin": "admin123",   # username: password
    "cashier": "cashier123"
}
USER_ROLES = {
    "admin": "admin",
    "cashier": "cashier"
}

class LoginPage:
    def __init__(self, root):
        self.root = root
        self.root.title("Login - Restaurant Billing System")
        self.root.geometry("350x220")
        tk.Label(root, text="Login Page", font=("Arial", 14, "bold")).pack(pady=10)
        tk.Label(root, text="Username:").pack()
        self.username_entry = tk.Entry(root)
        self.username_entry.pack()
        tk.Label(root, text="Password:").pack()
        self.password_entry = tk.Entry(root, show="*")
        self.password_entry.pack()
        self.message_label = tk.Label(root, text="", fg="red")
        self.message_label.pack()

        login_btn = tk.Button(root, text="Login", command=self.login)
        login_btn.pack(pady=10)
        self.root.bind('<Return>', lambda event: self.login())

    def login(self):
        uname = self.username_entry.get().strip()
        passwd = self.password_entry.get()
        if uname in USERS and USERS[uname] == passwd:
            self.root.destroy()
            main_root = tk.Tk()
            RestaurantBilling(main_root, uname, USER_ROLES.get(uname, "cashier"))
            main_root.mainloop()
        else:
            self.message_label.config(text="Invalid username or password!")

# ================== Main Application ==================
class RestaurantBilling:
    # Your __init__ and other methods...

    def setup_live_clock(self):
        self.clock_label = tk.Label(self.root, font=("Arial", 12))
        self.clock_label.pack(anchor="ne", padx=10, pady=5)
        self.update_clock()

    def update_clock(self):
        current_time = strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.config(text=current_time)
        self.root.after(1000, self.update_clock)

    def __init__(self, root, user, role):
        self.root = root
        self.user = user
        self.role = role
        self.root.title(f"Restaurant Billing Software - Logged in as {user.capitalize()} ({role})")
        self.root.geometry("1200x700")
        self.current_discount = 0  # No discount initially
        self.cart=[]
        # Setup live clock (top right corner label)
        self.setup_live_clock()


        # === Table/Customer/Payment method ===
        top_input_frame = tk.Frame(self.root)
        top_input_frame.pack(pady=8)
        tk.Label(top_input_frame, text="Table No. (Dine-In):").grid(row=0, column=0, sticky='e')
        self.table_no_var = tk.StringVar(value="1")
        self_options = [row[0] for row in cursor.fetchall()]
        self.table_no_menu = ttk.Combobox(top_input_frame, textvariable=self.table_no_var,values=self_options, state='readonly', width=10)
        self.table_no_menu.grid(row=0, column=1)
        
        tk.Label(top_input_frame, text="Customer Name (Takeaway):").grid(row=0, column=2, sticky='e')
        self.customer_name_var = tk.StringVar()
        self.customer_name_entry = tk.Entry(top_input_frame, textvariable=self.customer_name_var, width=15)
        self.customer_name_entry.grid(row=0, column=3)

        tk.Label(top_input_frame, text="Payment Method:").grid(row=0, column=4, sticky='e')
        self.payment_method_var = tk.StringVar(value="Cash")
        payment_options = ["Cash", "Card", "UPI"]
        self.payment_method_menu = ttk.Combobox(top_input_frame, textvariable=self.payment_method_var, values=payment_options, width=10, state='readonly')
        self.payment_method_menu.grid(row=0, column=5)

        # ========== Order Type ==========
        self.order_type = tk.StringVar(value="Dine-In")
        order_type_frame = tk.Frame(self.root)
        order_type_frame.pack()
        tk.Label(order_type_frame, text="Order Type:", font=("Arial", 12)).pack(side=tk.LEFT)
        tk.Radiobutton(order_type_frame, text="Dine-In", variable=self.order_type, value="Dine-In").pack(side=tk.LEFT)
        tk.Radiobutton(order_type_frame, text="Takeaway", variable=self.order_type, value="Takeaway").pack(side=tk.LEFT)

        # ========== Menu ========== (Always show after login)
        self.menu_frame = tk.Frame(self.root)
        self.menu_frame.pack(side="left", fill="y", padx=8)
        tk.Label(self.menu_frame, text="Menu", font=("Arial", 14, "bold")).pack()
        self.menu_tree = ttk.Treeview(self.menu_frame, columns=("name", "Category", "Price", "gst"), show="headings")
        self.menu_tree.heading("name", text="Name")
        self.menu_tree.heading("Category", text="Category")
        self.menu_tree.heading("Price", text="Price")
        self.menu_tree.heading("gst", text="GST (%)")
        self.menu_tree.pack(fill="y", expand=True)
        self.load_menu()
        tk.Button(self.menu_frame, text="Add to Cart", command=self.add_to_cart).pack(pady=10)
        if self.role == "admin":
            tk.Button(self.menu_frame, text="Open Admin Panel", bg="orange", command=self.open_admin_panel).pack(pady=5)

        # ========== Table Management (Admin only) ==========
        if self.role in ["admin"]:
            self.table_frame = tk.LabelFrame(self.root, text="Table Management", padx=10, pady=10)
            self.table_frame.pack(side="top", fill="x", padx=10, pady=5)
            self.table_tree = ttk.Treeview(self.table_frame, columns=("Table", "Status"), show="headings", height=5)
            self.table_tree.heading("Table", text="Table No.")
            self.table_tree.heading("Status", text="status")
            self.table_tree.pack(fill="x")
            self.load_tables()
            self.table_btns_frame = tk.Frame(self.table_frame)
            self.table_btns_frame.pack(fill="x", pady=5)
            for i in range(1, 11):
                btn = tk.Button(self.table_btns_frame, text=f"Table {i}", width=10,
                                command=lambda t=i: self.toggle_table_status(t))
                btn.grid(row=0, column=i-1, padx=2)

    def toggle_table_status(self, table_no):
        cursor.execute("SELECT status FROM tables WHERE table_no=?", (table_no,))
        result = cursor.fetchone()
        if result:
            current_status = result[0]
            new_status = "Free" if current_status == "Occupied" else "Occupied"
            cursor.execute("UPDATE tables SET status=? WHERE table_no=?", (new_status, table_no))
            conn.commit()
            self.load_tables()
            self.load_free_tables()
    # ========== Cart ==========
        self.cart_frame = tk.Frame(self.root)
        self.cart_frame.pack(side="right", fill="both", expand=True, padx=8)
        tk.Label(self.cart_frame, text="Cart", font=("Arial", 14, "bold")).pack()
        self.cart_tree = ttk.Treeview(self.cart_frame, columns=("Item", "Qty", "Price", "gst"), show="headings")
        self.cart_tree.heading("Item", text="Item")
        self.cart_tree.heading("Qty", text="Qty")
        self.cart_tree.heading("Price", text="Price")
        self.cart_tree.heading("gst", text="GST (%)")
        self.cart_tree.pack(fill="both", expand=True)

    # ...existing code...
    # Buttons in one horizontal frame (side by side)
        buttons_frame = tk.Frame(self.cart_frame)
        buttons_frame.pack(pady=10)

        gen_bill_btn = tk.Button(buttons_frame, text="Generate Bill", bg="green", fg="white", width=15, command=self.generate_bill)
        gen_bill_btn.pack(side=tk.LEFT, padx=5)

        clear_cart_btn = tk.Button(buttons_frame, text="Clear Cart", bg="red", fg="white", width=15, command=self.clear_cart)
        clear_cart_btn.pack(side=tk.LEFT, padx=5)

        discount_btn = tk.Button(buttons_frame, text="Apply Discount", bg="blue", fg="white", width=15, command=self.apply_discount)
        discount_btn.pack(side=tk.LEFT, padx=5)

        # Export report button below buttons_frame or at bottom_frame - your choice
        tk.Button(self.cart_frame, text="Export Report (CSV)", bg="blue", fg="white", command=self.export_report).pack(pady=5)

        # ========== Bottom Control Buttons ==========
        bottom_frame = tk.Frame(self.root, bd=6, relief=tk.RIDGE)
        bottom_frame.pack(side=tk.BOTTOM, fill="x")
        tk.Button(bottom_frame, text="Exit", command=self.root.destroy).pack(side=tk.LEFT, padx=5)

        # Initialize cart list
        self.cart = []

        # Setup live clock (top right corner label)
        self.setup_live_clock()

    def load_menu(self):
        for i in self.menu_tree.get_children():
            self.menu_tree.delete(i)
        cursor.execute("SELECT name, category, price, gst FROM menu")
        for row in cursor.fetchall():
            self.menu_tree.insert("", "end", iid=row[0], values=row)

    def load_free_tables(self):
        cursor.execute("SELECT table_no FROM tables WHERE status='Free'")
        free_tables = [row[0] for row in cursor.fetchall()]
        self.table_no_menu['values'] = free_tables
        if free_tables:
            self.table_no_var.set(free_tables[0])
        else:
            self.table_no_var.set("")

    def load_tables(self):
        for i in self.table_tree.get_children():
            self.table_tree.delete(i)
        self.table_tree.tag_configure("Free", background="lightgreen")
        self.table_tree.tag_configure("Occupied", background="tomato")
        cursor.execute("SELECT table_no, status FROM tables")
        for row in cursor.fetchall():
            self.table_tree.insert("", "end", values=row, tags=(row,))
        

    def add_to_cart(self):
        selected_items = self.menu_tree.selection()
        if not selected_items:
            messagebox.showerror("Error", "Please select an item from the menu.")
            return
        for selected in selected_items:
            item_values = self.menu_tree.item(selected, "values")
            if not item_values:
                continue
            item_name, category, price, gst = item_values
            qty = 1
            self.cart.append((item_name, qty, float(price), float(gst)))
            self.cart_tree.insert("", "end", values=(item_name, qty, price, gst))
    
    def clear_cart(self):
        self.cart = []
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        self.bill_text.delete("1.0", tk.END)
        self.current_discount = 0  # Reset discount on clear
    
    def apply_discount(self):
        if not self.cart:
            messagebox.showerror("Error", "Cart is empty! Add items before applying discount.")
            return
        discount_val =simpledialog.askfloat("Discount", "Enter discount percentage", minvalue=0, maxvalue=100)
        if discount_val is None:
            return
        self.current_discount = discount_val
        messagebox.showinfo("Discount Applied", f"Discount of {discount_val}% applied.")
   
    def generate_bill(self):
        if not self.cart:
            messagebox.showerror("Error", "Cart is empty!")
            return
 
        table_no = self.table_no_var.get().strip() if self.order_type.get() == "Dine-In" else ""
        customer_name = self.customer_name_var.get().strip() if self.order_type.get() == "Takeaway" else ""
        payment_method = self.payment_method_var.get()

        order_id = None
        subtotal = sum(qty * price for _, qty, price, _ in self.cart)
        gst_total = sum(qty * price * gst_pcnt / 100 for _, qty, price, gst_pcnt in self.cart)
        discount = (subtotal * self.current_discount / 100) if self.current_discount else 0
        final_amount = subtotal + gst_total - discount
        order_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            cursor.execute("""INSERT INTO orders(order_type, table_no, customer_name, timestamp, total, gst, discount, final_amount, payment_method)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                           (
                               self.order_type.get(),
                               table_no, customer_name, order_time,
                               subtotal, gst_total, discount, final_amount,
                               payment_method
                           ))
            order_id = cursor.lastrowid
            for item_name, qty, price, gst_pcnt in self.cart:
                cursor.execute("INSERT INTO order_items(order_id, item_name, qty, price) VALUES (?, ?, ?, ?)",
                               (order_id, item_name, qty, price))
            conn.commit()

            # Mark table occupied if Dine-In
            if self.order_type.get() == "Dine-In" and table_no:
                cursor.execute("UPDATE tables SET status='Occupied' WHERE table_no=?", (table_no,))
                conn.commit()
                self.load_tables()
                self.load_free_tables()

        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to save order: {e}")
            return
        
        self.display_bill(order_id, subtotal, gst_total, discount, final_amount, table_no, customer_name, payment_method)
       
        # Reset discount after bill generated
        self.current_discount = 0


    def display_bill(self, order_id, subtotal, gst, discount, final_amount, table_no, customer_name, payment_method):
        bill_win = tk.Toplevel(self.root)
        bill_win.title("Customer Bill")
        bill_win.geometry("500x600")
        bill_text = tk.Text(bill_win, bd=6, relief=tk.RIDGE, width=60, height=30)
        bill_text.pack(pady=10, fill="both", expand=True)
        bill_text.insert(tk.END,f"      🍽 Raju Restaurant 🍽\n")
        bill_text.insert(tk.END, "******* Restaurant Bill *******".center(32) + "\n")
        bill_text.insert(tk.END, f"Order ID: {order_id}\n")
        bill_text.insert(tk.END, f"Order Type: {self.order_type.get()}\n")
        if table_no:
            bill_text.insert(tk.END, f"Table No: {table_no}\n")
        if customer_name:
            bill_text.insert(tk.END, f"Customer: {customer_name}\n")
        bill_text.insert(tk.END, f"Payment: {payment_method}\n")
        bill_text.insert(tk.END, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        bill_text.insert(tk.END, "------------------------------\n")
        bill_text.insert(tk.END, f"{'Item':15} {'Qty':>3} {'Price':>10}\n")
        bill_text.insert(tk.END, "------------------------------\n")
        for item_name, qty, price, gst_pcnt in self.cart:
            bill_text.insert(tk.END, f"{item_name:15} {qty:3} {price:10.2f}\n")
        bill_text.insert(tk.END, "------------------------------\n")
        bill_text.insert(tk.END, f"Subtotal: Rs. {subtotal:.2f}\n")
        bill_text.insert(tk.END, f"GST: Rs. {gst:.2f}\n")
        bill_text.insert(tk.END, f"Discount: -Rs. {discount:.2f}\n")
        bill_text.insert(tk.END, f"Final Amount: Rs. {final_amount:.2f}\n")
        bill_text.insert(tk.END, "******************************\n")
        bill_text.insert(tk.END, "✅ Thank you and visit again 😊\n")

        bill_text.config(state="disabled")

        def print_bill():
            import tempfile
            import platform
            bill_content = bill_text.get("1.0", tk.END)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp:
                tmp.write(bill_content)
                tmp_path = tmp.name
            if platform.system() == "Windows":
                import os
                os.startfile(tmp_path, "print")
            else:
                import subprocess
                subprocess.run(["lp", tmp_path])

        btn_frame = tk.Frame(bill_win)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Print", command=print_bill).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Close", command=bill_win.destroy).pack(side=tk.LEFT, padx=10)

        # Free up table after bill
        if self.order_type.get() == "Dine-In" and table_no:
            cursor.execute("UPDATE tables SET status='Free' WHERE table_no=?", (table_no,))
            conn.commit()
            self.load_tables()
            self.load_free_tables()

    def export_report(self):
        # Ensure the "data" directory exists
        if not os.path.exists('data'):
            os.makedirs('data')
        cursor.execute("SELECT * FROM orders")
        data = cursor.fetchall()
        df = pd.DataFrame(data, columns=["OrderID", "OrderType", "TableNo", "Customer", "Timestamp", "Subtotal", "GST", "Discount", "FinalAmount", "PaymentMethod"])
        save_path = os.path.join('data', 'sales_report.csv')
        df.to_csv(save_path, index=False)
        messagebox.showinfo("Exported", f"Sales report saved as {save_path}")

    def open_admin_panel(self):
        admin_win = tk.Toplevel(self.root)
        admin_win.title("Admin Panel - Menu Management")
        admin_win.geometry("500x400")
        tk.Label(admin_win, text="Add New Menu Item", font=("Arial", 14, "bold")).pack(pady=5)
        tk.Label(admin_win, text="Item Name").pack()
        name_entry = tk.Entry(admin_win)
        name_entry.pack()
        tk.Label(admin_win, text="Category").pack()
        category_entry = tk.Entry(admin_win)
        category_entry.pack()
        tk.Label(admin_win, text="Price").pack()
        price_entry = tk.Entry(admin_win)
        price_entry.pack()
        tk.Label(admin_win, text="GST (%)").pack()
        gst_entry = tk.Entry(admin_win)
        gst_entry.pack()
        def add_item():
            name = name_entry.get()
            category = category_entry.get()
            price = price_entry.get()
            gst = gst_entry.get()
            if not (name and category and price and gst):
                messagebox.showerror("Error", "Please fill all fields")
                return
            try:
                price_val = float(price)
                gst_val = float(gst)
            except ValueError:
                messagebox.showerror("Error", "Price and GST must be numbers")
                return
            cursor.execute("INSERT INTO menu(name, category, price, gst) VALUES (?, ?, ?, ?)",
                           (name, category, price_val, gst_val))
            conn.commit()
            messagebox.showinfo("Success", f"Item '{name}' added to menu")
            self.load_menu()
            admin_win.destroy()
        tk.Button(admin_win, text="Add Item", bg="green", fg="white", command=add_item).pack(pady=10)

if __name__ == "__main__":
    login_root = tk.Tk()
    LoginPage(login_root)
    login_root.mainloop()