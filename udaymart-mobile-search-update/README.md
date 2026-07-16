# 🛒 Uday Mart – Village E-Commerce Website

A complete Amazon-style e-commerce website for your village supermarket.
Built with **Django** (Python) + **SQLite** (SQL) + **HTML/CSS/JS** frontend.

---

## Deploy on Render

This repository includes a `render.yaml` Blueprint that deploys the Django site
and creates a PostgreSQL database automatically.

1. Push the contents of this `udaymart` folder to a GitHub repository.
2. In Render, select **New → Blueprint**, connect that repository, and click
   **Apply**.
3. Render runs the configured build, migrations, and sample product setup, then
   provides the public `onrender.com` URL.
4. In the Blueprint form, enter `ADMIN_USERNAME`, `ADMIN_EMAIL`, and a strong
   `ADMIN_PASSWORD`; Render creates this administrator during the first build.

`SECRET_KEY` and `DATABASE_URL` are configured automatically by the Blueprint.
Do not use the old `admin / admin123` demo credentials in production. Uploaded
media is stored on Render's ephemeral filesystem; use object storage (such as
Cloudinary or S3) before relying on uploaded product images in production.

## 🚀 Quick Setup (Step by Step)

### Step 1: Install Python
Download from https://python.org (version 3.10 or above)

### Step 2: Open Terminal / Command Prompt
Navigate to the project folder:
```
cd udaymart
```

### Step 3: Create a Virtual Environment
```
python -m venv venv
```
Activate it:
- **Windows:** `venv\Scripts\activate`
- **Mac/Linux:** `source venv/bin/activate`

### Step 4: Install Requirements
```
pip install -r requirements.txt
```

### Step 5: Run Database Migrations
```
python manage.py makemigrations
python manage.py migrate
```

### Step 6: Load Sample Data (Categories + Products + Admin)
```
python setup_data.py
```
This creates:
- ✅ 8 product categories
- ✅ 22 sample products
- ✅ Admin account: **admin / admin123**

### Step 7: Run the Server
```
python manage.py runserver
```

### Step 8: Open in Browser
- 🏪 **Shop:** http://127.0.0.1:8000/
- ⚙️ **Admin Panel:** http://127.0.0.1:8000/admin/

---

## 🌐 Website Features

| Feature | Description |
|---|---|
| 🏠 Homepage | Hero banner, category grid, featured/new/bestseller sections |
| 🔍 Search | Search by name, brand, category |
| 📦 Products | Grid with filters, sort, price range |
| 🛒 Cart | Add/remove/update quantities |
| 💳 Checkout | Address form, multiple payment methods |
| 📬 Orders | Order history, status tracking |
| ❤️ Wishlist | Save products for later |
| 👤 Account | Register, login, profile, logout |
| ⭐ Reviews | Star ratings and comments |
| 🔧 Admin | Full Django admin panel |

---

## 📁 Project Structure

```
udaymart/
├── manage.py              ← Run commands
├── setup_data.py          ← Load sample data
├── requirements.txt       ← Python packages
├── db.sqlite3             ← Database (auto-created)
│
├── udaymart/              ← Project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
└── store/                 ← Main app
    ├── models.py          ← Database tables
    ├── views.py           ← Page logic
    ├── urls.py            ← URL routes
    ├── forms.py           ← Forms
    ├── admin.py           ← Admin panel
    ├── context_processors.py
    │
    ├── templates/store/   ← HTML pages
    │   ├── base.html
    │   ├── home.html
    │   ├── product_list.html
    │   ├── product_detail.html
    │   ├── cart.html
    │   ├── checkout.html
    │   ├── order_*.html
    │   ├── login.html
    │   ├── register.html
    │   ├── profile.html
    │   ├── wishlist.html
    │   └── search.html
    │
    └── static/store/
        ├── css/style.css  ← Amazon-style CSS
        └── js/main.js     ← JavaScript
```

---

## 🔧 Admin Panel Guide

Login at http://127.0.0.1:8000/admin/ with `admin / admin123`

### Adding Products:
1. Click **Categories** → Add your categories
2. Click **Products** → Add products with:
   - Name, price, description
   - Category, brand
   - Stock quantity
   - Product image (upload photo)
   - Mark as Featured/Available

### Managing Orders:
- View all orders in **Orders** section
- Change order status (Pending → Confirmed → Shipped → Delivered)

---

## 💡 Customization Tips

- **Change site name:** Edit `udaymart/settings.py` and templates
- **Add your logo:** Replace logo section in `base.html`
- **Change colors:** Edit CSS variables in `style.css` (`:root` section)
- **Add categories:** Use Admin panel
- **Add products with images:** Upload via Admin panel
- **Production deployment:** Set `DEBUG = False`, use PostgreSQL

---

## 🏗️ Database Models

| Model | Purpose |
|---|---|
| Category | Product categories with icon |
| Product | Products with price, stock, rating |
| ProductImage | Multiple images per product |
| Cart | User's shopping cart |
| CartItem | Items in cart with quantity |
| Order | Placed orders with address |
| OrderItem | Products within an order |
| Review | Star ratings and comments |
| Wishlist | Saved products |

---

Made with ❤️ for Uday Mart – Your Village Supermarket 🌾
