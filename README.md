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

## Secure OTP, Order Messages, and Current Location

The site includes a secure email + SMS OTP flow for new customer accounts,
optional WhatsApp order confirmations, email order confirmations, and a
**Use My Current Location** button at checkout.

It is intentionally safe to deploy before external accounts are configured:
`OTP_AUTH_ENABLED` defaults to `false`, so the existing password login remains
available. Turn it on only after configuring both email and Twilio in the
Render service's **Environment** tab.

### 1. Configure transactional email

Add these private environment variables in Render (do not put them in Git):

```
EMAIL_HOST=smtp.your-provider.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-smtp-username
EMAIL_HOST_PASSWORD=your-smtp-password-or-app-password
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=Uday Mart <orders@your-domain.com>
```

Use an SMTP provider that is permitted to send transactional email from your
chosen `DEFAULT_FROM_EMAIL` address.

### 2. Configure SMS OTP with Twilio Verify

Create a **Verify Service** in Twilio, then add these private Render variables:

```
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_VERIFY_SERVICE_SID=VA...
OTP_AUTH_ENABLED=true
```

New customers will then verify one email code and one SMS code before their
account becomes active. Password login also asks verified customers for the
two codes. The sign-in page also offers an OTP-only sign-in option.

### 3. Configure WhatsApp order confirmations (optional)

WhatsApp order messages must come from a WhatsApp Business sender and use an
approved template for business-initiated notifications. Create an approved
Twilio Content Template with these four variables in this order:

```
UdayMart order update: Hello {{1}}, your order {{2}} has been confirmed.
Total: {{3}}. Track it here: {{4}}
```

Then add these private Render variables and enable the feature:

```
TWILIO_WHATSAPP_FROM=+your-approved-whatsapp-sender
TWILIO_WHATSAPP_CONTENT_SID=HX...
WHATSAPP_NOTIFICATIONS_ENABLED=true
SITE_URL=https://udaymart.onrender.com
```

WhatsApp is sent only when the customer checked the WhatsApp consent box and
their registered mobile number has passed OTP verification. Email and
WhatsApp delivery results appear in the Django admin under **Order
notifications**; a failed message never cancels the order.

### 4. Current location

At checkout the customer can press **Use My Current Location**. Their browser
asks for permission and, if allowed, the order stores optional latitude,
longitude, and accuracy alongside the manual address. It works on Render's
HTTPS URL and the customer can always decline it and type the address instead.

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
