-- ========== catalog-service ==========
INSERT INTO app_category (id, name, description, created_at) VALUES
(1, 'Van hoc Viet Nam', 'Tieu thuyet, truyen ngan, tho ca Viet Nam', NOW()),
(2, 'Khoa hoc & Cong nghe', 'Sach ve khoa hoc, lap trinh, cong nghe', NOW()),
(3, 'Kinh te & Kinh doanh', 'Sach ve kinh te, quan tri, tai chinh', NOW()),
(4, 'Thieu nhi', 'Truyen tranh, sach giao duc cho tre em', NOW()),
(5, 'Ky nang song', 'Sach phat trien ban than, tam ly', NOW())
ON CONFLICT (id) DO NOTHING;

-- ========== book-service ==========
INSERT INTO app_book (id, title, author, price, stock, category_id, isbn, description, created_at) VALUES
(1, 'Truyen Kieu', 'Nguyen Du', 85000.00, 50, 1, '9786041234501', 'Kiet tac van hoc Viet Nam, tho luc bat truyen', NOW()),
(2, 'Tat Den', 'Ngo Tat To', 65000.00, 40, 1, '9786041234502', 'Tieu thuyet hien thuc phe phan noi tieng', NOW()),
(3, 'Chi Pheo', 'Nam Cao', 55000.00, 45, 1, '9786041234503', 'Truyen ngan kinh dien ve so phan nguoi nong dan', NOW()),
(4, 'Nha Gia Kim', 'Paulo Coelho', 79000.00, 60, 5, '9786041234504', 'Tieu thuyet truyen cam hung ve hanh trinh theo duoi uoc mo', NOW()),
(5, 'Dac Nhan Tam', 'Dale Carnegie', 88000.00, 70, 5, '9786041234505', 'Nghe thuat doi nhan xu the va tao anh huong', NOW()),
(6, 'Clean Code', 'Robert C. Martin', 350000.00, 30, 2, '9786041234506', 'Huong dan viet code sach va de bao tri', NOW()),
(7, 'Python Crash Course', 'Eric Matthes', 420000.00, 25, 2, '9786041234507', 'Nhap mon lap trinh Python thuc hanh', NOW()),
(8, 'Cha Giau Cha Ngheo', 'Robert Kiyosaki', 110000.00, 55, 3, '9786041234508', 'Bai hoc ve tai chinh ca nhan va dau tu', NOW()),
(9, 'Nghi Giau Lam Giau', 'Napoleon Hill', 95000.00, 40, 3, '9786041234509', 'Bi quyet thanh cong va lam giau tu tu duy', NOW()),
(10, 'Doraemon Tap 1', 'Fujiko F. Fujio', 25000.00, 100, 4, '9786041234510', 'Truyen tranh Doraemon kinh dien cho thieu nhi', NOW()),
(11, 'Conan Tap 1', 'Gosho Aoyama', 25000.00, 90, 4, '9786041234511', 'Truyen tranh trinh tham Tham tu lung danh Conan', NOW()),
(12, 'Design Patterns', 'Gang of Four', 480000.00, 20, 2, '9786041234512', 'Mau thiet ke huong doi tuong kinh dien', NOW()),
(13, 'Tuoi Tre Dang Gia Bao Nhieu', 'Rosie Nguyen', 75000.00, 35, 5, '9786041234513', 'Cam nang song cho gioi tre Viet Nam', NOW()),
(14, 'Sapiens', 'Yuval Noah Harari', 185000.00, 45, 2, '9786041234514', 'Luoc su loai nguoi tu thoi tien su den hien dai', NOW()),
(15, 'Cho Toi Xin Mot Ve Di Tuoi Tho', 'Nguyen Nhat Anh', 68000.00, 80, 4, '9786041234515', 'Truyen dai cua Nguyen Nhat Anh ve tuoi tho', NOW())
ON CONFLICT (id) DO NOTHING;

-- ========== customer-service ==========
INSERT INTO app_customer (id, name, email, phone, address, auth_user_id, created_at) VALUES
(1, 'Nguyen Van A', 'nguyenvana@gmail.com', '0901234567', '123 Le Loi, Q1, TP.HCM', 5, NOW()),
(2, 'Tran Thi B', 'tranthib@gmail.com', '0912345678', '456 Nguyen Hue, Q1, TP.HCM', 6, NOW()),
(3, 'Le Van C', 'levanc@gmail.com', '0923456789', '789 Hai Ba Trung, Q3, TP.HCM', 7, NOW()),
(4, 'Pham Thi D', 'phamthid@gmail.com', '0934567890', '321 Tran Hung Dao, Q5, TP.HCM', 8, NOW()),
(5, 'Hoang E', 'hoange@gmail.com', '0945678901', '654 Vo Van Tan, Q3, TP.HCM', 9, NOW())
ON CONFLICT (id) DO NOTHING;

-- ========== staff-service ==========
INSERT INTO app_staff (id, name, email, role, auth_user_id, created_at) VALUES
(1, 'Nhan Vien 1', 'staff1@bookstore.vn', 'staff', 3, NOW()),
(2, 'Nhan Vien 2', 'staff2@bookstore.vn', 'staff', 4, NOW())
ON CONFLICT (id) DO NOTHING;

-- ========== manager-service ==========
INSERT INTO app_manager (id, name, email, department, auth_user_id, created_at) VALUES
(1, 'Quan Ly 1', 'manager1@bookstore.vn', 'Operations', 2, NOW())
ON CONFLICT (id) DO NOTHING;

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
