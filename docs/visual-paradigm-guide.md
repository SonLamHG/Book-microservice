# Visual Paradigm — Hướng dẫn xuất Class Diagram & ERD cho tiểu luận

Tiểu luận SoAD (Ch.2 §2.10) yêu cầu sinh viên:

> - Thiết kế Class Diagram bằng Visual Paradigm (VP)
> - Mapping từ Class Diagram → Database
> - Export sơ đồ từ VP (PNG/PDF)

Repo này đã viết sẵn 2 file PlantUML chính xác từ Django models thật:

| File | Nội dung |
|---|---|
| `docs/class-diagram.puml` | Class diagram toàn hệ — 8 bounded contexts, đầy đủ inheritance / composition / association |
| `docs/er-diagram.puml`    | ERD per-service — 11 database, primary key, foreign key, cross-service logical reference |

Sinh viên có 3 cách dùng để hoàn thành phần Class Diagram trong tiểu luận:

---

## Cách 1 — Render trực tiếp ra PNG/PDF (nhanh nhất)

Không cần Visual Paradigm. PlantUML tự render được.

**Online (không cài):**
1. Vào https://www.plantuml.com/plantuml/uml/
2. Copy nội dung `docs/class-diagram.puml` → paste
3. Submit → tải PNG/SVG/PDF

**CLI (nếu đã cài plantuml + Java):**
```bash
plantuml -tpng docs/class-diagram.puml      # → docs/class-diagram.png
plantuml -tpdf docs/class-diagram.puml      # → docs/class-diagram.pdf
plantuml -tsvg docs/er-diagram.puml         # → docs/er-diagram.svg
```

**VS Code extension:**
- Cài `jebbs.plantuml`
- Mở `.puml` → `Alt+D` để preview → click chuột phải → Export.

---

## Cách 2 — Import vào Visual Paradigm rồi export (đúng yêu cầu tiểu luận)

Visual Paradigm hỗ trợ import PlantUML trực tiếp.

1. Mở Visual Paradigm.
2. **Tools → Code → Instant Reverse → Reverse from PlantUML…**
   (hoặc: **File → Import → PlantUML…** ở các phiên bản mới)
3. Chọn file `docs/class-diagram.puml` → OK.
4. VP tự sinh ra Class Diagram. Có thể chỉnh layout, đổi màu, thêm note.
5. **File → Export → Image** (PNG/JPG) hoặc **Export → PDF** để lấy file nộp.

> **Lưu ý:** Một số phiên bản Community edition của VP không có Instant Reverse from PlantUML.
> Nếu vậy, dùng Cách 3 để vẽ tay trong VP — vẫn dùng file `.puml` làm sơ đồ tham chiếu.

---

## Cách 3 — Vẽ tay trong VP, dùng `.puml` làm reference (điểm cộng cho bản in)

Tiểu luận có ghi rõ:
> **SINH VIÊN MANG THEO BẢN IN KHI ĐI THI**
> **Bản IN được viết tay hay vẽ tay nhiều là điểm +**

Để vẽ tay trong VP (rồi vẽ tay lên bản in), tham chiếu danh sách class + thuộc tính dưới đây.

### Yêu cầu Ch.2 §2.10.2 — Classes per service

Tiểu luận liệt kê 3 service mẫu — bạn cần vẽ ít nhất các class này:

#### Product Service
| Class | Thuộc tính bắt buộc |
|---|---|
| `Category` | id, name, description, created_at |
| `Product` | id, name, price, stock, category_id, description, product_type, created_at |
| `Book` | product_id (PK→Product), author, publisher, isbn |
| `Electronics` | product_id (PK→Product), brand, warranty_months |
| `Fashion` | product_id (PK→Product), size, color, material |

**Quan hệ:**
- `Product` → `Category` : Association `1..*` to `1` (mỗi product thuộc 1 category)
- `Book`, `Electronics`, `Fashion` → `Product` : **Inheritance** (đúng theo template tiểu luận)

#### User Service
| Class | Thuộc tính |
|---|---|
| `User` | id, username, email, password, role (CUSTOMER/STAFF/MANAGER/ADMIN), created_at |
| `Customer` | id, name, email, phone, address, auth_user_id, created_at |
| `Staff` | id, name, email, role, auth_user_id, created_at |
| `Manager` | id, name, email, department, auth_user_id, created_at |

**Quan hệ:**
- `User` ↔ `Customer/Staff/Manager` : Association `1` to `0..1` (1 user có 0 hoặc 1 profile)

#### Order Service
| Class | Thuộc tính |
|---|---|
| `Order` | id, customer_id, total_amount, status, shipping_address, payment_method, shipping_method, created_at |
| `OrderItem` | id, order_id, book_id, quantity, price |
| `SagaLog` | id, order_id, step, status, details, created_at |

**Quan hệ:**
- `Order` ◆— `OrderItem` : **Composition** `1` to `1..*`
- `Order` ◆— `SagaLog` : Composition `1` to `0..*`

### Các service còn lại (đầy đủ trong `class-diagram.puml`)

| Service | Class chính |
|---|---|
| Cart Service | `Cart`, `CartItem` (composition) |
| Payment Service | `Payment` |
| Shipping Service | `Shipment` |
| Comment-Rate Service | `Review` |
| Advisory Chat Service | `KnowledgeDocument`, `ChatSession`, `ChatMessage`, `CustomerBehaviorSummary` |

---

## Mapping Class Diagram → Database (Ch.2 §2.10.3)

Theo nguyên tắc:
- Class → Table
- Attribute → Column
- Inheritance → Foreign Key có `PRIMARY KEY` chia sẻ
- Composition → Foreign Key với `ON DELETE CASCADE`

Ví dụ mapping `Product` + `Book`:

```sql
-- Product (base)
CREATE TABLE app_product (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(255) NOT NULL,
    price        DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    stock        INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    category_id  INTEGER,                                 -- logical FK
    description  TEXT DEFAULT '',
    product_type VARCHAR(20) NOT NULL DEFAULT 'book',
    created_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Book (subtype) — PK đồng thời là FK→Product (đúng pattern OneToOne của tiểu luận)
CREATE TABLE app_book (
    product_id  INTEGER PRIMARY KEY REFERENCES app_product(id) ON DELETE CASCADE,
    author      VARCHAR(255) NOT NULL,
    publisher   VARCHAR(255) DEFAULT '',
    isbn        VARCHAR(13)  DEFAULT ''
);
```

Cách kiểm tra schema thực tế:

```bash
docker-compose exec postgres psql -U postgres -d product_db -c "\d app_product"
docker-compose exec postgres psql -U postgres -d product_db -c "\d app_book"
docker-compose exec postgres psql -U postgres -d product_db -c "\d app_electronics"
docker-compose exec postgres psql -U postgres -d product_db -c "\d app_fashion"
```

---

## Checklist nộp bài (theo Ch.2 §2.10.7)

- [ ] Có Class Diagram đúng UML (export PNG/PDF từ VP hoặc PlantUML)
- [ ] Có Inheritance: `Book/Electronics/Fashion` kế thừa `Product`
- [ ] Có Composition: `Order` ◆— `OrderItem`, `Cart` ◆— `CartItem`
- [ ] Có Association với cardinality (`1..*`, `1..1`, `0..1`)
- [ ] Mapping rõ ràng sang database schema (SQL CREATE TABLE)
- [ ] Database tách riêng từng service (`product_db`, `cart_db`, `order_db`, …)
- [ ] (Khi hoàn thành task #4) Sử dụng cả MySQL và PostgreSQL

---

## File nộp đề xuất

```
tieuluan_v01_<lop>.<nhom>_<ten>.pdf
├── (LaTeX/Word document)
├── + class-diagram.png      (toàn hệ — render từ class-diagram.puml)
├── + er-diagram.png         (tất cả 11 database — render từ er-diagram.puml)
└── + (đính kèm) class-diagram.puml + er-diagram.puml để giảng viên kiểm tra source
```
