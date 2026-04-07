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

users = [
    {"username": "admin",      "email": "admin@bookstore.vn",      "role": "ADMIN",    "password": "admin123"},
    {"username": "manager1",   "email": "manager1@bookstore.vn",   "role": "MANAGER",  "password": "manager123"},
    {"username": "staff1",     "email": "staff1@bookstore.vn",     "role": "STAFF",    "password": "staff123"},
    {"username": "staff2",     "email": "staff2@bookstore.vn",     "role": "STAFF",    "password": "staff123"},
    {"username": "nguyenvana", "email": "nguyenvana@gmail.com",    "role": "CUSTOMER", "password": "customer123"},
    {"username": "tranthib",   "email": "tranthib@gmail.com",      "role": "CUSTOMER", "password": "customer123"},
    {"username": "levanc",     "email": "levanc@gmail.com",        "role": "CUSTOMER", "password": "customer123"},
    {"username": "phamthid",   "email": "phamthid@gmail.com",      "role": "CUSTOMER", "password": "customer123"},
    {"username": "hoange",     "email": "hoange@gmail.com",        "role": "CUSTOMER", "password": "customer123"},
]

created = 0
for u in users:
    obj, was_created = User.objects.get_or_create(
        username=u["username"],
        defaults={"email": u["email"], "role": u["role"], "password": ""}
    )
    if was_created:
        obj.set_password(u["password"])
        obj.save()
        created += 1

print(f"Auth: {created} users created ({len(users)} total defined)")
PYEOF

# -------------------------------------------------------
# Helper: extract SQL section and pipe to service's PostgreSQL via Django
# -------------------------------------------------------
seed_service() {
    local service_name="$1"
    local section_name="$2"
    local db_name="$3"

    # Extract lines between section header and next section header (or EOF)
    local sql
    sql=$(sed -n "/^-- ========== ${section_name} ==========$/,/^-- ==========/{ /^-- ==========/d; p; }" "$SQL_FILE")

    if [ -z "$sql" ]; then
        echo "  WARNING: No SQL found for section '${section_name}'"
        return 1
    fi

    echo "$sql" | docker-compose exec -T postgres psql -U postgres -d "$db_name" -q
    echo "  Done."
}

# -------------------------------------------------------
# Phase 2: Catalog Service (categories)
# -------------------------------------------------------
echo "[2/7] Seeding catalog-service (categories)..."
seed_service "catalog-service" "catalog-service" "catalog_db"

# -------------------------------------------------------
# Phase 3: Book Service (books)
# -------------------------------------------------------
echo "[3/7] Seeding book-service (books)..."
seed_service "book-service" "book-service" "book_db"

# -------------------------------------------------------
# Phase 4: Customer / Staff / Manager
# -------------------------------------------------------
echo "[4/7] Seeding customer-service, staff-service, manager-service..."
seed_service "customer-service" "customer-service" "customer_db"
seed_service "staff-service" "staff-service" "staff_db"
seed_service "manager-service" "manager-service" "manager_db"

# -------------------------------------------------------
# Phase 5: Cart Service
# -------------------------------------------------------
echo "[5/7] Seeding cart-service (carts + items)..."
seed_service "cart-service" "cart-service" "cart_db"

# -------------------------------------------------------
# Phase 6: Order / Payment / Shipping
# -------------------------------------------------------
echo "[6/7] Seeding order-service, pay-service, ship-service..."
seed_service "order-service" "order-service" "order_db"
seed_service "pay-service" "pay-service" "payment_db"
seed_service "ship-service" "ship-service" "shipping_db"

# -------------------------------------------------------
# Phase 7: Comment-Rate Service (reviews)
# -------------------------------------------------------
echo "[7/7] Seeding comment-rate-service (reviews)..."
seed_service "comment-rate-service" "comment-rate-service" "comment_db"

# -------------------------------------------------------
# Reset sequences for all services
# -------------------------------------------------------
echo ""
echo "Resetting PostgreSQL sequences..."

reset_sequences() {
    local db_name="$1"
    docker-compose exec -T postgres psql -U postgres -d "$db_name" -q -c "
DO \$\$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'app_%')
    LOOP
        BEGIN
            EXECUTE format('SELECT setval(pg_get_serial_sequence(''%I'', ''id''), COALESCE(MAX(id), 1)) FROM %I', r.tablename, r.tablename);
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END;
    END LOOP;
END \$\$;
"
    echo "  $db_name: sequences reset"
}

reset_sequences "auth_db"
reset_sequences "catalog_db"
reset_sequences "book_db"
reset_sequences "customer_db"
reset_sequences "staff_db"
reset_sequences "manager_db"
reset_sequences "cart_db"
reset_sequences "order_db"
reset_sequences "payment_db"
reset_sequences "shipping_db"
reset_sequences "comment_db"

echo ""
echo "=== All services seeded successfully! ==="
echo ""
echo "Test accounts:"
echo "  Admin:    admin / admin123"
echo "  Manager:  manager1 / manager123"
echo "  Staff:    staff1 / staff123"
echo "  Customer: nguyenvana / customer123"
