"""
Uday Mart – Sample Data Setup Script
Run: python setup_data.py  (after migrations)
Or:  python manage.py shell < setup_data.py
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'udaymart.settings')
django.setup()

from django.contrib.auth.models import User
from store.models import Category, Product

print("🌾 Setting up Uday Mart sample data...")

# ── CREATE SUPERUSER ──
admin_password = os.environ.get('ADMIN_PASSWORD')
if admin_password:
    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@udaymart.com')
    if not User.objects.filter(username=admin_username).exists():
        User.objects.create_superuser(admin_username, admin_email, admin_password)
        print(f"✅ Superuser created: {admin_username}")

# ── CATEGORIES ──
categories_data = [
    ('Groceries & Staples', 'groceries', '🌾'),
    ('Fruits & Vegetables', 'fruits-vegetables', '🥦'),
    ('Dairy & Eggs', 'dairy-eggs', '🥛'),
    ('Snacks & Beverages', 'snacks-beverages', '🍪'),
    ('Personal Care', 'personal-care', '🧴'),
    ('Household & Cleaning', 'household-cleaning', '🧹'),
    ('Medicines & Health', 'medicines-health', '💊'),
    ('Baby Products', 'baby-products', '👶'),
]

cats = {}
for name, slug, icon in categories_data:
    cat, created = Category.objects.get_or_create(
        slug=slug,
        defaults={'name': name, 'icon': icon, 'description': f'Best {name} at lowest prices'}
    )
    cats[slug] = cat
    if created:
        print(f"  ✅ Category: {name}")

# ── PRODUCTS ──
products_data = [
    # Groceries
    ('Aashirvaad Atta 5kg', 'aashirvaad-atta-5kg', 'groceries', 'Aashirvaad', 'Whole wheat atta for soft rotis. Made from finest quality wheat.', 265, 299, 50, True),
    ('Tata Salt 1kg', 'tata-salt-1kg', 'groceries', 'Tata', 'Iodized vacuum evaporated salt. Fine grain, pure and natural.', 25, 30, 200, False),
    ('Fortune Sunflower Oil 1L', 'fortune-sunflower-oil-1l', 'groceries', 'Fortune', 'Refined sunflower oil, light and healthy for everyday cooking.', 155, 179, 75, True),
    ('India Gate Basmati Rice 5kg', 'india-gate-basmati-5kg', 'groceries', 'India Gate', 'Premium long grain basmati rice with natural aroma.', 620, 699, 40, True),
    ('Toor Dal 1kg', 'toor-dal-1kg', 'groceries', 'Uday Mart', 'Premium quality toor dal, freshly packed. Rich in protein.', 145, 160, 100, False),

    # Fruits & Vegetables
    ('Fresh Tomatoes 1kg', 'fresh-tomatoes-1kg', 'fruits-vegetables', 'Farm Fresh', 'Locally sourced fresh red tomatoes. Great for curries and salads.', 40, 50, 80, False),
    ('Bananas (Dozen)', 'bananas-dozen', 'fruits-vegetables', 'Village Farm', 'Fresh ripe bananas, rich in potassium and natural energy.', 45, 60, 60, False),
    ('Onions 2kg', 'onions-2kg', 'fruits-vegetables', 'Farm Fresh', 'Premium quality onions, fresh from farm.', 55, 70, 120, False),

    # Dairy
    ('Amul Full Cream Milk 1L', 'amul-milk-1l', 'dairy-eggs', 'Amul', 'Fresh full cream milk, pasteurized and homogenized.', 68, 72, 150, True),
    ('Amul Butter 500g', 'amul-butter-500g', 'dairy-eggs', 'Amul', 'Pasteurized table butter, rich and creamy taste.', 245, 265, 40, True),
    ('Farm Eggs (12 pcs)', 'farm-eggs-12', 'dairy-eggs', 'Village Farm', 'Fresh country eggs, packed with protein.', 90, 105, 60, False),
    ('Amul Paneer 200g', 'amul-paneer-200g', 'dairy-eggs', 'Amul', 'Fresh soft paneer made from pure cow milk.', 95, 110, 50, False),

    # Snacks
    ('Lays Classic Salted 50g', 'lays-classic-50g', 'snacks-beverages', "Lay's", 'Classic salted potato chips, crispy and delicious.', 20, 20, 200, False),
    ('Bisleri Water 1L', 'bisleri-water-1l', 'snacks-beverages', 'Bisleri', 'Pure and safe packaged drinking water.', 20, 20, 500, False),
    ('Parle-G Biscuits 800g', 'parle-g-800g', 'snacks-beverages', 'Parle', 'Gluco biscuits, wholesome goodness of milk and wheat.', 55, 65, 300, True),
    ('Nescafé Classic 100g', 'nescafe-classic-100g', 'snacks-beverages', 'Nescafé', 'Rich and smooth instant coffee with deep aroma.', 285, 320, 80, True),

    # Personal Care
    ('Colgate Total Toothpaste 150g', 'colgate-total-150g', 'personal-care', 'Colgate', '12-hour antibacterial protection for whole mouth health.', 155, 175, 90, False),
    ('Dove Soap 3x100g', 'dove-soap-3pack', 'personal-care', 'Dove', 'Moisturizing beauty cream bar for soft and smooth skin.', 180, 210, 65, True),
    ('Head & Shoulders Shampoo 340ml', 'head-shoulders-340ml', 'personal-care', 'Head & Shoulders', 'Anti-dandruff shampoo for clean and flake-free hair.', 320, 370, 40, False),

    # Household
    ('Vim Dishwash Bar 200g', 'vim-dishwash-200g', 'household-cleaning', 'Vim', 'Tough on grease, gentle on hands. Lemon fragrance.', 22, 25, 200, False),
    ('Harpic Power Plus 1L', 'harpic-power-1l', 'household-cleaning', 'Harpic', '10x more powerful toilet cleaner, kills 99.9% germs.', 189, 220, 55, True),
    ('Lizol Surface Cleaner 1L', 'lizol-1l', 'household-cleaning', 'Lizol', 'Disinfectant floor cleaner, kills 99.9% germs. Floral scent.', 210, 240, 45, False),
]

for name, slug, cat_slug, brand, desc, price, orig_price, stock, featured in products_data:
    prod, created = Product.objects.get_or_create(
        slug=slug,
        defaults={
            'name': name,
            'category': cats[cat_slug],
            'brand': brand,
            'description': desc,
            'price': price,
            'original_price': orig_price,
            'stock': stock,
            'is_featured': featured,
            'is_available': True,
            'rating': 4.2,
            'review_count': 0,
        }
    )
    if created:
        print(f"  ✅ Product: {name}")

print("\n🎉 Uday Mart setup complete!")
print("   Admin URL: http://127.0.0.1:8000/admin/")
print("   Username: admin | Password: admin123")
print("   Site URL: http://127.0.0.1:8000/")
