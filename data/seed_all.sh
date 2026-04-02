#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SQL_FILE="$SCRIPT_DIR/seed_data.sql"

echo "=== Bookstore Microservice - Seed Data ==="
echo ""

# -------------------------------------------------------
# Phase 1: Auth Service (Python - can hash password)
# -------------------------------------------------------
echo "[1/7] Seeding auth-service (users)..."
docker-compose exec -T auth-service python manage.py shell <<'PYEOF'
from app.models import User
from django.db import connection

users = [
    {"username": "admin",    "email": "admin@gmail.com",    "role": "ADMIN",    "password": "123456"},
    {"username": "staff",    "email": "staff@gmail.com",    "role": "STAFF",    "password": "123456"},
]

for i in range(1, 11):
    users.append({
        "username": f"customer{i}",
        "email": f"customer{i}@gmail.com",
        "role": "CUSTOMER",
        "password": "123456",
    })

User.objects.all().delete()
with connection.cursor() as cursor:
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='app_user'")

for u in users:
    obj = User(username=u["username"], email=u["email"], role=u["role"])
    obj.set_password(u["password"])
    obj.save()

print(f"Auth: seeded {len(users)} users")
PYEOF

# -------------------------------------------------------
# Helper: extract SQL section and pipe to service's sqlite3
# -------------------------------------------------------
seed_service() {
    local service_name="$1"
    local section_name="$2"

    # Extract lines between section header and next section header (or EOF)
    local sql
    sql=$(sed -n "/^-- ========== ${section_name} ==========$/,/^-- ==========/{ /^-- ==========/d; p; }" "$SQL_FILE")

    if [ -z "$sql" ]; then
        echo "  WARNING: No SQL found for section '${section_name}'"
        return 1
    fi

    echo "$sql" | docker-compose exec -T "$service_name" python -c "
import sys, sqlite3
conn = sqlite3.connect('/app/data/db.sqlite3')
conn.executescript(sys.stdin.read())
conn.close()
print('  Done.')
"
}

# -------------------------------------------------------
# Phase 2: Catalog Service (categories)
# -------------------------------------------------------
echo "[2/7] Seeding catalog-service (categories)..."
seed_service "catalog-service" "catalog-service"

# -------------------------------------------------------
# Phase 3: Book Service (books)
# -------------------------------------------------------
echo "[3/7] Seeding book-service (books)..."
seed_service "book-service" "book-service"

# -------------------------------------------------------
# Phase 4: Customer / Staff / Manager
# -------------------------------------------------------
echo "[4/7] Seeding customer-service, staff-service, manager-service..."
seed_service "customer-service" "customer-service"
seed_service "staff-service" "staff-service"
seed_service "manager-service" "manager-service"

# -------------------------------------------------------
# Phase 5: Cart Service
# -------------------------------------------------------
echo "[5/7] Seeding cart-service (carts + items)..."
seed_service "cart-service" "cart-service"

# -------------------------------------------------------
# Phase 6: Order / Payment / Shipping
# -------------------------------------------------------
echo "[6/7] Seeding order-service, pay-service, ship-service..."
seed_service "order-service" "order-service"
seed_service "pay-service" "pay-service"
seed_service "ship-service" "ship-service"

# -------------------------------------------------------
# Phase 7: Comment-Rate Service (reviews)
# -------------------------------------------------------
echo "[7/7] Seeding comment-rate-service (reviews)..."
seed_service "comment-rate-service" "comment-rate-service"

echo ""
echo "=== All services seeded successfully! ==="
echo ""
echo "Test accounts:"
echo "  Admin:    admin / 123456"
echo "  Staff:    staff / 123456"
for i in $(seq 1 10); do
  echo "  Customer: customer${i} / 123456"
done
