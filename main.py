import os
import shutil
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

DB_NAME = "book_shop.db"
PHOTO_FOLDER = "photos"
PLACEHOLDER = "picture.png"


def connect_db():
    db = sqlite3.connect(DB_NAME)
    db.execute("PRAGMA foreign_keys = ON")
    return db


def create_tables():
    db = connect_db()
    with open("schema.sql", "r", encoding="utf-8") as file:
        text = file.read()
    db.executescript(text)
    db.commit()
    db.close()


def add_start_data():
    db = connect_db()
    cur = db.cursor()

    roles = ["client", "manager", "admin"]
    for role in roles:
        cur.execute("INSERT OR IGNORE INTO roles(name) VALUES(?)", (role,))

    categories = ["Роман", "Учебник", "Фантастика", "Детектив"]
    for category in categories:
        cur.execute("INSERT OR IGNORE INTO categories(name) VALUES(?)", (category,))

    suppliers = ["Книжный мир", "БукПоставка", "ЛитРесурс"]
    for supplier in suppliers:
        cur.execute("INSERT OR IGNORE INTO suppliers(name) VALUES(?)", (supplier,))

    statuses = ["Новый", "Собирается", "Готов", "Выдан"]
    for status in statuses:
        cur.execute("INSERT OR IGNORE INTO order_statuses(name) VALUES(?)", (status,))

    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM roles WHERE name='client'")
        client_role = cur.fetchone()[0]
        cur.execute("SELECT id FROM roles WHERE name='manager'")
        manager_role = cur.fetchone()[0]
        cur.execute("SELECT id FROM roles WHERE name='admin'")
        admin_role = cur.fetchone()[0]

        users = [
            ("client", "123", "Иванов Иван Иванович", client_role),
            ("manager", "123", "Петров Петр Петрович", manager_role),
            ("admin", "123", "Админ Админович", admin_role),
        ]
        for user in users:
            cur.execute("INSERT INTO users(login, password, full_name, role_id) VALUES(?,?,?,?)", user)

    cur.execute("SELECT COUNT(*) FROM products")
    if cur.fetchone()[0] == 0:
        products = [
            ("", "Война и мир", 1, "Большая книга", "Толстой", 1, 900, "шт", 5, 10),
            ("", "Python для чайников", 2, "Учебник для новичков", "Автор 1", 2, 1200, "шт", 10, 30),
            ("", "Космический путь", 3, "Книга про космос", "Автор 2", 3, 700, "шт", 0, 5),
            ("", "Тайна дома", 4, "Детектив", "Автор 3", 1, 500, "шт", 3, 17),
        ]
        for product in products:
            cur.execute("""
                INSERT INTO products(image_path, name, category_id, description, manufacturer, supplier_id, price, unit, stock_count, discount)
                VALUES(?,?,?,?,?,?,?,?,?,?)
            """, product)

    cur.execute("SELECT COUNT(*) FROM orders")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO orders(article, status_id, pickup_address, order_date, receive_date) VALUES(?,?,?,?,?)",
                    ("ORD-1", 1, "Москва, пункт 1", "2026-02-09", "2026-02-12"))
        cur.execute("INSERT INTO order_products(order_id, product_id, count) VALUES(?,?,?)", (1, 1, 1))

    db.commit()
    db.close()


class App:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Книжный склад - вход")
        self.window.geometry("1100x650")
        self.window.minsize(900, 550)

        self.user_name = "Гость"
        self.user_role = "guest"
        self.edit_window_open = False

        self.search_text = tk.StringVar()
        self.sort_text = tk.StringVar(value="Без сортировки")
        self.filter_text = tk.StringVar(value="Все диапазоны")

        self.show_login()
        self.window.mainloop()

    def clear(self):
        for widget in self.window.winfo_children():
            widget.destroy()

    def show_login(self):
        self.clear()
        self.window.title("Книжный склад - вход")

        frame = tk.Frame(self.window)
        frame.pack(expand=True)

        tk.Label(frame, text="Вход", font=("Arial", 24)).pack(pady=10)

        tk.Label(frame, text="Логин").pack()
        login_entry = tk.Entry(frame, width=30)
        login_entry.pack(pady=5)

        tk.Label(frame, text="Пароль").pack()
        password_entry = tk.Entry(frame, width=30, show="*")
        password_entry.pack(pady=5)

        def login():
            login = login_entry.get()
            password = password_entry.get()

            db = connect_db()
            cur = db.cursor()
            cur.execute("""
                SELECT users.full_name, roles.name
                FROM users
                JOIN roles ON users.role_id = roles.id
                WHERE users.login = ? AND users.password = ?
            """, (login, password))
            user = cur.fetchone()
            db.close()

            if user is None:
                messagebox.showerror("Ошибка входа", "Логин или пароль неправильный")
                return

            self.user_name = user[0]
            self.user_role = user[1]
            self.show_products()

        tk.Button(frame, text="Войти", width=25, command=login).pack(pady=8)

        def guest_login():
            self.user_name = "Гость"
            self.user_role = "guest"
            self.show_products()

        tk.Button(frame, text="Войти как гость", width=25, command=guest_login).pack(pady=8)

        tk.Label(frame, text="Тестовые входы: client/123, manager/123, admin/123").pack(pady=15)

    def make_top_panel(self, title):
        top = tk.Frame(self.window)
        top.pack(fill="x", padx=10, pady=8)

        tk.Label(top, text=title, font=("Arial", 18)).pack(side="left")
        tk.Label(top, text=self.user_name).pack(side="right", padx=10)
        tk.Button(top, text="Выход", command=self.show_login).pack(side="right")

    def show_products(self):
        self.clear()
        self.window.title("Книжный склад - товары")
        self.make_top_panel("Список товаров")

        control = tk.Frame(self.window)
        control.pack(fill="x", padx=10)

        can_search = self.user_role in ["manager", "admin"]
        can_admin = self.user_role == "admin"

        if can_search:
            tk.Label(control, text="Поиск").pack(side="left")
            entry = tk.Entry(control, textvariable=self.search_text, width=25)
            entry.pack(side="left", padx=5)
            entry.bind("<KeyRelease>", lambda event: self.load_products())

            sort_box = ttk.Combobox(control, textvariable=self.sort_text, state="readonly", width=25)
            sort_box["values"] = [
                "Без сортировки",
                "Цена по возрастанию",
                "Цена по убыванию",
                "Количество по возрастанию",
                "Количество по убыванию",
            ]
            sort_box.pack(side="left", padx=5)
            sort_box.bind("<<ComboboxSelected>>", lambda event: self.load_products())

            filter_box = ttk.Combobox(control, textvariable=self.filter_text, state="readonly", width=18)
            filter_box["values"] = ["Все диапазоны", " 0-10,99%", "11-14,99%", "15% и более"]
            filter_box.pack(side="left", padx=5)
            filter_box.bind("<<ComboboxSelected>>", lambda event: self.load_products())

        if can_admin:
            tk.Button(control, text="Добавить товар", command=lambda: self.open_product_form(None)).pack(side="right", padx=5)

        if self.user_role in ["manager", "admin"]:
            tk.Button(control, text="Заказы", command=self.show_orders).pack(side="right", padx=5)

        columns = ("id", "name", "category", "description", "manufacturer", "supplier", "price", "final_price", "unit", "stock", "discount")
        self.product_table = ttk.Treeview(self.window, columns=columns, show="headings")
        self.product_table.pack(fill="both", expand=True, padx=10, pady=10)

        names = ["ID", "Название", "Категория", "Описание", "Производитель", "Поставщик", "Цена", "Цена со скидкой", "Ед.", "Склад", "Скидка"]
        for i in range(len(columns)):
            self.product_table.heading(columns[i], text=names[i])
            self.product_table.column(columns[i], width=100)

        self.product_table.tag_configure("big_discount", background="#23E1EF")
        self.product_table.tag_configure("empty", background="lightgray")

        if can_admin:
            self.product_table.bind("<Double-1>", self.product_double_click)

        self.load_products()

    def load_products(self):
        for item in self.product_table.get_children():
            self.product_table.delete(item)

        db = connect_db()
        cur = db.cursor()

        sql = """
            SELECT products.id, products.name, categories.name, products.description,
                   products.manufacturer, suppliers.name, products.price, products.unit,
                   products.stock_count, products.discount
            FROM products
            JOIN categories ON products.category_id = categories.id
            JOIN suppliers ON products.supplier_id = suppliers.id
        """
        params = []
        where_parts = []

        if self.user_role in ["manager", "admin"]:
            search = self.search_text.get().strip()
            if search != "":
                like = "%" + search + "%"
                where_parts.append("""
                    (products.name LIKE ? OR categories.name LIKE ? OR products.description LIKE ?
                    OR products.manufacturer LIKE ? OR suppliers.name LIKE ? OR products.unit LIKE ?)
                """)
                params.extend([like, like, like, like, like, like])

            filt = self.filter_text.get()
            if filt == "0-10,99%":
                where_parts.append("products.discount >= 0 AND products.discount < 11")
            if filt == "11-14,99%":
                where_parts.append("products.discount >= 11 AND products.discount < 15")
            if filt == "15% и более":
                where_parts.append("products.discount >= 15")

        if len(where_parts) > 0:
            sql += " WHERE " + " AND ".join(where_parts)

        if self.user_role in ["manager", "admin"]:
            sort = self.sort_text.get()
            if sort == "Цена по возрастанию":
                sql += " ORDER BY products.price ASC"
            if sort == "Цена по убыванию":
                sql += " ORDER BY products.price DESC"
            if sort == "Количество по возрастанию":
                sql += " ORDER BY products.stock_count ASC"
            if sort == "Количество по убыванию":
                sql += " ORDER BY products.stock_count DESC"

        cur.execute(sql, params)
        rows = cur.fetchall()
        db.close()

        for row in rows:
            price = row[6]
            discount = row[9]
            final_price = round(price - price * discount / 100, 2)
            values = list(row)
            values.insert(7, final_price)

            tag = ""
            if row[8] == 0:
                tag = "empty"
            elif discount > 25:
                tag = "big_discount"

            self.product_table.insert("", "end", values=values, tags=(tag,))

    def product_double_click(self, event):
        item = self.product_table.focus()
        if item == "":
            return
        values = self.product_table.item(item, "values")
        product_id = values[0]
        self.open_product_form(product_id)

    def get_combo_data(self, table):
        db = connect_db()
        cur = db.cursor()
        cur.execute(f"SELECT id, name FROM {table}")
        rows = cur.fetchall()
        db.close()
        return rows

    def open_product_form(self, product_id):
        if self.edit_window_open:
            messagebox.showwarning("Предупреждение", "Уже открыто окно редактирования")
            return

        self.edit_window_open = True
        win = tk.Toplevel(self.window)
        win.title("Товар")
        win.geometry("500x620")

        def on_close():
            self.edit_window_open = False
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)

        categories = self.get_combo_data("categories")
        suppliers = self.get_combo_data("suppliers")

        product = None
        if product_id is not None:
            db = connect_db()
            cur = db.cursor()
            cur.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            product = cur.fetchone()
            db.close()

        tk.Label(win, text="ID").pack()
        id_entry = tk.Entry(win)
        id_entry.pack(fill="x", padx=20)
        id_entry.config(state="readonly")

        tk.Label(win, text="Фото").pack()
        image_entry = tk.Entry(win)
        image_entry.pack(fill="x", padx=20)

        def choose_image():
            path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
            if path != "":
                image_entry.delete(0, "end")
                image_entry.insert(0, path)

        tk.Button(win, text="Выбрать фото", command=choose_image).pack(pady=3)

        tk.Label(win, text="Название").pack()
        name_entry = tk.Entry(win)
        name_entry.pack(fill="x", padx=20)

        tk.Label(win, text="Категория").pack()
        category_combo = ttk.Combobox(win, state="readonly")
        category_combo["values"] = [x[1] for x in categories]
        category_combo.pack(fill="x", padx=20)

        tk.Label(win, text="Описание").pack()
        description_entry = tk.Entry(win)
        description_entry.pack(fill="x", padx=20)

        tk.Label(win, text="Производитель").pack()
        manufacturer_entry = tk.Entry(win)
        manufacturer_entry.pack(fill="x", padx=20)

        tk.Label(win, text="Поставщик").pack()
        supplier_combo = ttk.Combobox(win, state="readonly")
        supplier_combo["values"] = [x[1] for x in suppliers]
        supplier_combo.pack(fill="x", padx=20)

        tk.Label(win, text="Цена").pack()
        price_entry = tk.Entry(win)
        price_entry.pack(fill="x", padx=20)

        tk.Label(win, text="Единица измерения").pack()
        unit_entry = tk.Entry(win)
        unit_entry.pack(fill="x", padx=20)

        tk.Label(win, text="Количество").pack()
        stock_entry = tk.Entry(win)
        stock_entry.pack(fill="x", padx=20)

        tk.Label(win, text="Скидка").pack()
        discount_entry = tk.Entry(win)
        discount_entry.pack(fill="x", padx=20)

        if product is not None:
            id_entry.config(state="normal")
            id_entry.insert(0, product[0])
            id_entry.config(state="readonly")
            image_entry.insert(0, product[1] or "")
            name_entry.insert(0, product[2])
            category_combo.current(product[3] - 1)
            description_entry.insert(0, product[4] or "")
            manufacturer_entry.insert(0, product[5] or "")
            supplier_combo.current(product[6] - 1)
            price_entry.insert(0, product[7])
            unit_entry.insert(0, product[8])
            stock_entry.insert(0, product[9])
            discount_entry.insert(0, product[10])

        def save_product():
            try:
                name = name_entry.get().strip()
                category_index = category_combo.current()
                description = description_entry.get().strip()
                manufacturer = manufacturer_entry.get().strip()
                supplier_index = supplier_combo.current()
                price = float(price_entry.get())
                unit = unit_entry.get().strip()
                stock = int(stock_entry.get())
                discount = float(discount_entry.get())
                image_path = image_entry.get().strip()

                if name == "" or unit == "":
                    messagebox.showerror("Ошибка", "Название и единица измерения не должны быть пустыми")
                    return
                if category_index < 0 or supplier_index < 0:
                    messagebox.showerror("Ошибка", "Выберите категорию и поставщика")
                    return
                if price < 0 or stock < 0 or discount < 0:
                    messagebox.showerror("Ошибка", "Цена, количество и скидка не могут быть отрицательными")
                    return

                category_id = categories[category_index][0]
                supplier_id = suppliers[supplier_index][0]

                if image_path != "" and os.path.exists(image_path):
                    os.makedirs(PHOTO_FOLDER, exist_ok=True)
                    new_path = os.path.join(PHOTO_FOLDER, os.path.basename(image_path))
                    if os.path.abspath(image_path) != os.path.abspath(new_path):
                        shutil.copy(image_path, new_path)
                    image_path = new_path

                db = connect_db()
                cur = db.cursor()

                if product_id is None:
                    cur.execute("""
                        INSERT INTO products(image_path, name, category_id, description, manufacturer, supplier_id, price, unit, stock_count, discount)
                        VALUES(?,?,?,?,?,?,?,?,?,?)
                    """, (image_path, name, category_id, description, manufacturer, supplier_id, price, unit, stock, discount))
                else:
                    cur.execute("""
                        UPDATE products
                        SET image_path=?, name=?, category_id=?, description=?, manufacturer=?, supplier_id=?, price=?, unit=?, stock_count=?, discount=?
                        WHERE id=?
                    """, (image_path, name, category_id, description, manufacturer, supplier_id, price, unit, stock, discount, product_id))

                db.commit()
                db.close()
                self.load_products()
                on_close()
            except ValueError:
                messagebox.showerror("Ошибка", "Цена и скидка должны быть числами. Количество должно быть целым числом")

        tk.Button(win, text="Сохранить", command=save_product).pack(pady=10)

        if product_id is not None:
            def delete_product():
                answer = messagebox.askyesno("Удаление", "Точно удалить товар?")
                if not answer:
                    return

                db = connect_db()
                cur = db.cursor()
                cur.execute("SELECT COUNT(*) FROM order_products WHERE product_id = ?", (product_id,))
                count = cur.fetchone()[0]
                if count > 0:
                    db.close()
                    messagebox.showerror("Ошибка", "Товар есть в заказе. Удалить нельзя")
                    return

                cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
                db.commit()
                db.close()
                self.load_products()
                on_close()

            tk.Button(win, text="Удалить", command=delete_product).pack(pady=5)

    def show_orders(self):
        self.clear()
        self.window.title("Книжный склад - заказы")
        self.make_top_panel("Заказы")

        top = tk.Frame(self.window)
        top.pack(fill="x", padx=10)
        tk.Button(top, text="Назад к товарам", command=self.show_products).pack(side="left")

        if self.user_role == "admin":
            tk.Button(top, text="Добавить заказ", command=lambda: self.open_order_form(None)).pack(side="right")

        columns = ("id", "article", "status", "address", "order_date", "receive_date")
        self.order_table = ttk.Treeview(self.window, columns=columns, show="headings")
        self.order_table.pack(fill="both", expand=True, padx=10, pady=10)

        names = ["ID", "Артикул", "Статус", "Адрес выдачи", "Дата заказа", "Дата выдачи"]
        for i in range(len(columns)):
            self.order_table.heading(columns[i], text=names[i])
            self.order_table.column(columns[i], width=150)

        if self.user_role == "admin":
            self.order_table.bind("<Double-1>", self.order_double_click)

        self.load_orders()

    def load_orders(self):
        for item in self.order_table.get_children():
            self.order_table.delete(item)

        db = connect_db()
        cur = db.cursor()
        cur.execute("""
            SELECT orders.id, orders.article, order_statuses.name, orders.pickup_address, orders.order_date, orders.receive_date
            FROM orders
            JOIN order_statuses ON orders.status_id = order_statuses.id
        """)
        rows = cur.fetchall()
        db.close()

        for row in rows:
            self.order_table.insert("", "end", values=row)

    def order_double_click(self, event):
        item = self.order_table.focus()
        if item == "":
            return
        values = self.order_table.item(item, "values")
        self.open_order_form(values[0])

    def open_order_form(self, order_id):
        win = tk.Toplevel(self.window)
        win.title("Заказ")
        win.geometry("450x420")

        statuses = self.get_combo_data("order_statuses")

        order = None
        if order_id is not None:
            db = connect_db()
            cur = db.cursor()
            cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
            order = cur.fetchone()
            db.close()

        tk.Label(win, text="ID").pack()
        id_entry = tk.Entry(win)
        id_entry.pack(fill="x", padx=20)
        id_entry.config(state="readonly")

        tk.Label(win, text="Артикул").pack()
        article_entry = tk.Entry(win)
        article_entry.pack(fill="x", padx=20)

        tk.Label(win, text="Статус").pack()
        status_combo = ttk.Combobox(win, state="readonly")
        status_combo["values"] = [x[1] for x in statuses]
        status_combo.pack(fill="x", padx=20)

        tk.Label(win, text="Адрес пункта выдачи").pack()
        address_entry = tk.Entry(win)
        address_entry.pack(fill="x", padx=20)

        tk.Label(win, text="Дата заказа, например 2026-02-09").pack()
        order_date_entry = tk.Entry(win)
        order_date_entry.pack(fill="x", padx=20)

        tk.Label(win, text="Дата выдачи, например 2026-02-12").pack()
        receive_date_entry = tk.Entry(win)
        receive_date_entry.pack(fill="x", padx=20)

        if order is not None:
            id_entry.config(state="normal")
            id_entry.insert(0, order[0])
            id_entry.config(state="readonly")
            article_entry.insert(0, order[1])
            status_combo.current(order[2] - 1)
            address_entry.insert(0, order[3])
            order_date_entry.insert(0, order[4])
            receive_date_entry.insert(0, order[5])

        def save_order():
            article = article_entry.get().strip()
            status_index = status_combo.current()
            address = address_entry.get().strip()
            order_date = order_date_entry.get().strip()
            receive_date = receive_date_entry.get().strip()

            if article == "" or address == "" or order_date == "" or receive_date == "":
                messagebox.showerror("Ошибка", "Заполните все поля")
                return
            if status_index < 0:
                messagebox.showerror("Ошибка", "Выберите статус")
                return

            status_id = statuses[status_index][0]

            db = connect_db()
            cur = db.cursor()
            if order_id is None:
                cur.execute("INSERT INTO orders(article, status_id, pickup_address, order_date, receive_date) VALUES(?,?,?,?,?)",
                            (article, status_id, address, order_date, receive_date))
            else:
                cur.execute("UPDATE orders SET article=?, status_id=?, pickup_address=?, order_date=?, receive_date=? WHERE id=?",
                            (article, status_id, address, order_date, receive_date, order_id))
            db.commit()
            db.close()
            self.load_orders()
            win.destroy()

        tk.Button(win, text="Сохранить", command=save_order).pack(pady=10)

        if order_id is not None:
            def delete_order():
                answer = messagebox.askyesno("Удаление", "Точно удалить заказ?")
                if not answer:
                    return
                db = connect_db()
                cur = db.cursor()
                cur.execute("DELETE FROM orders WHERE id = ?", (order_id,))
                db.commit()
                db.close()
                self.load_orders()
                win.destroy()

            tk.Button(win, text="Удалить", command=delete_order).pack(pady=5)


if __name__ == "__main__":
    create_tables()
    add_start_data()
    App()
