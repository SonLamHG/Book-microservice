-- ========== catalog-service ==========
INSERT INTO app_category (id, name, description, created_at) VALUES
(1, 'Van hoc Viet Nam', 'Tieu thuyet, truyen ngan, tho ca Viet Nam', NOW()),
(2, 'Khoa hoc & Cong nghe', 'Sach ve khoa hoc, lap trinh, cong nghe', NOW()),
(3, 'Kinh te & Kinh doanh', 'Sach ve kinh te, quan tri, tai chinh', NOW()),
(4, 'Thieu nhi', 'Truyen tranh, sach giao duc cho tre em', NOW()),
(5, 'Ky nang song', 'Sach phat trien ban than, tam ly', NOW()),
(6, 'Dien thoai & May tinh bang', 'Smartphone, tablet, phu kien', NOW()),
(7, 'Laptop & PC', 'Laptop van phong, gaming, thiet bi tinh', NOW()),
(8, 'Thoi trang Nam', 'Ao, quan, giay nam', NOW()),
(9, 'Thoi trang Nu', 'Ao, quan, giay nu', NOW())
ON CONFLICT (id) DO NOTHING;

-- ========== product-service ==========
-- Step 1: insert into the shared Product table (15 books + 6 electronics + 6 fashion).
INSERT INTO app_product (id, name, price, stock, category_id, description, product_type, created_at) VALUES
-- Books (1..15)
(1,  'Truyen Kieu',                       85000.00, 50, 1, 'Kiet tac van hoc Viet Nam, tho luc bat truyen',          'book', NOW()),
(2,  'Tat Den',                           65000.00, 40, 1, 'Tieu thuyet hien thuc phe phan noi tieng',                'book', NOW()),
(3,  'Chi Pheo',                          55000.00, 45, 1, 'Truyen ngan kinh dien ve so phan nguoi nong dan',         'book', NOW()),
(4,  'Nha Gia Kim',                       79000.00, 60, 5, 'Tieu thuyet truyen cam hung ve hanh trinh theo duoi uoc mo','book', NOW()),
(5,  'Dac Nhan Tam',                      88000.00, 70, 5, 'Nghe thuat doi nhan xu the va tao anh huong',             'book', NOW()),
(6,  'Clean Code',                       350000.00, 30, 2, 'Huong dan viet code sach va de bao tri',                  'book', NOW()),
(7,  'Python Crash Course',              420000.00, 25, 2, 'Nhap mon lap trinh Python thuc hanh',                     'book', NOW()),
(8,  'Cha Giau Cha Ngheo',               110000.00, 55, 3, 'Bai hoc ve tai chinh ca nhan va dau tu',                  'book', NOW()),
(9,  'Nghi Giau Lam Giau',                95000.00, 40, 3, 'Bi quyet thanh cong va lam giau tu tu duy',               'book', NOW()),
(10, 'Doraemon Tap 1',                    25000.00,100, 4, 'Truyen tranh Doraemon kinh dien cho thieu nhi',           'book', NOW()),
(11, 'Conan Tap 1',                       25000.00, 90, 4, 'Truyen tranh trinh tham Tham tu lung danh Conan',         'book', NOW()),
(12, 'Design Patterns',                  480000.00, 20, 2, 'Mau thiet ke huong doi tuong kinh dien',                  'book', NOW()),
(13, 'Tuoi Tre Dang Gia Bao Nhieu',       75000.00, 35, 5, 'Cam nang song cho gioi tre Viet Nam',                     'book', NOW()),
(14, 'Sapiens',                          185000.00, 45, 2, 'Luoc su loai nguoi tu thoi tien su den hien dai',         'book', NOW()),
(15, 'Cho Toi Xin Mot Ve Di Tuoi Tho',    68000.00, 80, 4, 'Truyen dai cua Nguyen Nhat Anh ve tuoi tho',              'book', NOW()),
-- Electronics (16..21)
(16, 'iPhone 15 Pro 256GB',            27990000.00, 25, 6, 'Smartphone cao cap, chip A17 Pro, camera 48MP',         'electronics', NOW()),
(17, 'Samsung Galaxy S24 Ultra',       28990000.00, 20, 6, 'Flagship Android, but S Pen, zoom 100x',                'electronics', NOW()),
(18, 'iPad Air M2 11 inch',            16990000.00, 30, 6, 'Tablet Apple chip M2, man hinh Liquid Retina',          'electronics', NOW()),
(19, 'MacBook Air M3 13 inch',         28990000.00, 15, 7, 'Laptop sieu mong, chip M3, pin 18 gio',                 'electronics', NOW()),
(20, 'Dell XPS 15',                    42990000.00, 10, 7, 'Laptop cao cap cho cong viec sang tao, RTX 4060',       'electronics', NOW()),
(21, 'ASUS ROG Strix G16',             35990000.00, 12, 7, 'Laptop gaming RTX 4070, RAM 16GB',                      'electronics', NOW()),
-- Fashion (22..27)
(22, 'Ao so mi nam Owen',                450000.00, 80, 8, 'Ao so mi cong so nam, vai cotton',                       'fashion', NOW()),
(23, 'Quan tay nam Aristino',            650000.00, 60, 8, 'Quan tay nam cong so, vai wool blend',                   'fashion', NOW()),
(24, 'Giay tay nam DUNK',               1250000.00, 35, 8, 'Giay tay nam da bo that, de cao su',                     'fashion', NOW()),
(25, 'Ao thun nu Routine',               280000.00,100, 9, 'Ao thun nu basic, cotton 100%',                          'fashion', NOW()),
(26, 'Vay maxi nu Elise',                890000.00, 45, 9, 'Vay maxi du tiec, chat lieu lua mem',                    'fashion', NOW()),
(27, 'Tui xach nu Charles & Keith',     1990000.00, 25, 9, 'Tui xach cong so, da PU cao cap',                        'fashion', NOW())
ON CONFLICT (id) DO NOTHING;

-- Step 2: insert subtype rows.
INSERT INTO app_book (product_id, author, publisher, isbn) VALUES
(1,  'Nguyen Du',           'NXB Van Hoc',         '9786041234501'),
(2,  'Ngo Tat To',           'NXB Van Hoc',         '9786041234502'),
(3,  'Nam Cao',              'NXB Van Hoc',         '9786041234503'),
(4,  'Paulo Coelho',         'NXB Hoi Nha Van',     '9786041234504'),
(5,  'Dale Carnegie',        'NXB Tre',             '9786041234505'),
(6,  'Robert C. Martin',     'NXB Cong Thuong',     '9786041234506'),
(7,  'Eric Matthes',         'NXB Bach Khoa',       '9786041234507'),
(8,  'Robert Kiyosaki',      'NXB Lao Dong',        '9786041234508'),
(9,  'Napoleon Hill',        'NXB Tong Hop',        '9786041234509'),
(10, 'Fujiko F. Fujio',      'NXB Kim Dong',        '9786041234510'),
(11, 'Gosho Aoyama',         'NXB Kim Dong',        '9786041234511'),
(12, 'Gang of Four',         'NXB Cong Thuong',     '9786041234512'),
(13, 'Rosie Nguyen',         'NXB Hoi Nha Van',     '9786041234513'),
(14, 'Yuval Noah Harari',    'NXB The Gioi',        '9786041234514'),
(15, 'Nguyen Nhat Anh',      'NXB Tre',             '9786041234515')
ON CONFLICT (product_id) DO NOTHING;

INSERT INTO app_electronics (product_id, brand, warranty_months) VALUES
(16, 'Apple',   12),
(17, 'Samsung', 12),
(18, 'Apple',   12),
(19, 'Apple',   12),
(20, 'Dell',    24),
(21, 'ASUS',    24)
ON CONFLICT (product_id) DO NOTHING;

INSERT INTO app_fashion (product_id, size, color, material) VALUES
(22, 'L',   'Trang',   'Cotton'),
(23, '32',  'Den',     'Wool blend'),
(24, '42',  'Nau',     'Da bo'),
(25, 'M',   'Trang',   'Cotton'),
(26, 'S',   'Hong',    'Lua'),
(27, 'One', 'Den',     'Da PU')
ON CONFLICT (product_id) DO NOTHING;

-- (customer-service, staff-service, manager-service moved to data/seed_data_mysql.sql
--  — those three databases now live on MySQL, see Ch.2.10.4 polyglot persistence split.)

-- ========== cart-service ==========
INSERT INTO app_cart (id, customer_id, created_at) VALUES
(1, 1, NOW()),
(2, 3, NOW())
ON CONFLICT (id) DO NOTHING;

INSERT INTO app_cartitem (id, cart_id, book_id, quantity) VALUES
(1, 1, 4, 2),
(2, 1, 6, 1),
(3, 2, 10, 3)
ON CONFLICT (id) DO NOTHING;

-- ========== order-service ==========
INSERT INTO app_order (id, customer_id, total_amount, status, shipping_address, payment_method, shipping_method, created_at) VALUES
(1, 1, 280000.00, 'COMPLETED', '123 Le Loi, Q1, TP.HCM', 'COD', 'STANDARD', NOW()),
(2, 2, 350000.00, 'COMPLETED', '456 Nguyen Hue, Q1, TP.HCM', 'CREDIT_CARD', 'EXPRESS', NOW()),
(3, 1, 174000.00, 'PENDING', '123 Le Loi, Q1, TP.HCM', 'COD', 'STANDARD', NOW())
ON CONFLICT (id) DO NOTHING;

INSERT INTO app_orderitem (id, order_id, book_id, quantity, price) VALUES
(1, 1, 1, 1, 85000.00),
(2, 1, 3, 1, 55000.00),
(3, 1, 5, 1, 88000.00),
(4, 1, 15, 1, 68000.00),
(5, 2, 6, 1, 350000.00),
(6, 3, 4, 1, 79000.00),
(7, 3, 9, 1, 95000.00)
ON CONFLICT (id) DO NOTHING;

INSERT INTO app_sagalog (id, order_id, step, status, details, created_at) VALUES
(1, 1, 'CREATE_ORDER', 'SUCCESS', 'Order created', NOW()),
(2, 1, 'RESERVE_PAYMENT', 'SUCCESS', 'Payment reserved', NOW()),
(3, 1, 'RESERVE_SHIPMENT', 'SUCCESS', 'Shipment reserved', NOW()),
(4, 1, 'CONFIRM_ORDER', 'SUCCESS', 'Order confirmed', NOW()),
(5, 2, 'CREATE_ORDER', 'SUCCESS', 'Order created', NOW()),
(6, 2, 'RESERVE_PAYMENT', 'SUCCESS', 'Payment reserved', NOW()),
(7, 2, 'RESERVE_SHIPMENT', 'SUCCESS', 'Shipment reserved', NOW()),
(8, 2, 'CONFIRM_ORDER', 'SUCCESS', 'Order confirmed', NOW()),
(9, 3, 'CREATE_ORDER', 'SUCCESS', 'Order created', NOW())
ON CONFLICT (id) DO NOTHING;

-- ========== pay-service ==========
INSERT INTO app_payment (id, order_id, amount, method, status, created_at) VALUES
(1, 1, 280000.00, 'COD', 'COMPLETED', NOW()),
(2, 2, 350000.00, 'CREDIT_CARD', 'COMPLETED', NOW()),
(3, 3, 174000.00, 'COD', 'RESERVED', NOW())
ON CONFLICT (id) DO NOTHING;

-- ========== ship-service ==========
INSERT INTO app_shipment (id, order_id, address, method, status, tracking_number, created_at) VALUES
(1, 1, '123 Le Loi, Q1, TP.HCM', 'STANDARD', 'DELIVERED', 'TRK-SEED0001', NOW()),
(2, 2, '456 Nguyen Hue, Q1, TP.HCM', 'EXPRESS', 'DELIVERED', 'TRK-SEED0002', NOW()),
(3, 3, '123 Le Loi, Q1, TP.HCM', 'STANDARD', 'RESERVED', 'TRK-SEED0003', NOW())
ON CONFLICT (id) DO NOTHING;

-- ========== comment-rate-service ==========
INSERT INTO app_review (id, book_id, customer_id, rating, comment, created_at) VALUES
(1, 1, 1, 5, 'Tac pham kinh dien, rat hay!', NOW()),
(2, 1, 2, 4, 'Truyen tho rat dep, nen doc', NOW()),
(3, 6, 1, 5, 'Sach lap trinh tuyet voi, must read', NOW()),
(4, 6, 3, 4, 'Rat huu ich cho lap trinh vien', NOW()),
(5, 4, 2, 5, 'Cuon sach truyen cam hung', NOW()),
(6, 5, 4, 4, 'Dac Nhan Tam rat thuc te', NOW()),
(7, 10, 5, 5, 'Con trai toi rat thich Doraemon', NOW()),
(8, 15, 3, 5, 'Nguyen Nhat Anh viet rat cam dong', NOW())
ON CONFLICT (id) DO NOTHING;
