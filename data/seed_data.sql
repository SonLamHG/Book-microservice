-- ========== catalog-service ==========
DELETE FROM app_category;
DELETE FROM sqlite_sequence WHERE name='app_category';

INSERT INTO app_category (id, name, description, created_at) VALUES
(1, 'Literature', 'Classic and contemporary literary works', datetime('now')),
(2, 'Technology', 'Programming, software engineering and IT books', datetime('now')),
(3, 'Business', 'Business, finance, startup and investing books', datetime('now')),
(4, 'Children', 'Books and comics for younger readers', datetime('now')),
(5, 'Self Development', 'Habits, mindset and personal growth', datetime('now')),
(6, 'History', 'History, society and civilization books', datetime('now')),
(7, 'Biography', 'Life stories of influential people', datetime('now'));

-- ========== book-service ==========
DELETE FROM app_book;
DELETE FROM sqlite_sequence WHERE name='app_book';

INSERT INTO app_book (id, title, author, price, stock, category_id, isbn, description, created_at) VALUES
(1, 'The Alchemist', 'Paulo Coelho', 89000.00, 40, 1, '9780062315007', 'A modern classic about purpose and personal legend.', datetime('now')),
(2, 'Norwegian Wood', 'Haruki Murakami', 149000.00, 26, 1, '9780375704024', 'A nostalgic coming-of-age novel with emotional depth.', datetime('now')),
(3, 'To Kill a Mockingbird', 'Harper Lee', 139000.00, 30, 1, '9780061120084', 'A timeless novel about justice, empathy and childhood.', datetime('now')),
(4, 'Clean Code', 'Robert C. Martin', 350000.00, 18, 2, '9780132350884', 'A practical guide to writing clean and maintainable code.', datetime('now')),
(5, 'Python Crash Course', 'Eric Matthes', 420000.00, 15, 2, '9781593279288', 'A hands-on introduction to Python programming.', datetime('now')),
(6, 'Django for APIs', 'William S. Vincent', 280000.00, 14, 2, '9781735467245', 'Build web APIs with Django and Django REST Framework.', datetime('now')),
(7, 'System Design Interview', 'Alex Xu', 390000.00, 17, 2, '9781736049112', 'A practical guide to common system design problems.', datetime('now')),
(8, 'Refactoring', 'Martin Fowler', 410000.00, 11, 2, '9780134757599', 'Improve the design of existing code safely and systematically.', datetime('now')),
(9, 'Rich Dad Poor Dad', 'Robert Kiyosaki', 125000.00, 32, 3, '9781612680194', 'A popular personal finance and investing book.', datetime('now')),
(10, 'The Lean Startup', 'Eric Ries', 219000.00, 22, 3, '9780307887894', 'A startup method focused on validated learning and iteration.', datetime('now')),
(11, 'The Psychology of Money', 'Morgan Housel', 189000.00, 27, 3, '9780857197689', 'A book about behavior, money and long-term thinking.', datetime('now')),
(12, 'Zero to One', 'Peter Thiel', 179000.00, 20, 3, '9780804139298', 'A contrarian look at startups and creating new value.', datetime('now')),
(13, 'Doraemon Vol. 1', 'Fujiko F. Fujio', 25000.00, 80, 4, '9784088518310', 'A classic comic series opener loved by generations.', datetime('now')),
(14, 'Harry Potter and the Sorcerers Stone', 'J.K. Rowling', 168000.00, 25, 4, '9780590353427', 'A magical adventure and an iconic gateway to fantasy reading.', datetime('now')),
(15, 'The Little Prince', 'Antoine de Saint-Exupery', 99000.00, 24, 4, '9780156012195', 'A poetic story for children and adults alike.', datetime('now')),
(16, 'Atomic Habits', 'James Clear', 210000.00, 35, 5, '9780735211292', 'A bestselling guide to small habits creating big changes.', datetime('now')),
(17, 'Deep Work', 'Cal Newport', 185000.00, 23, 5, '9781455586691', 'A book on focused work in a distracted world.', datetime('now')),
(18, 'Mindset', 'Carol S. Dweck', 175000.00, 28, 5, '9780345472328', 'How a growth mindset shapes learning and achievement.', datetime('now')),
(19, 'Ikigai', 'Hector Garcia', 145000.00, 26, 5, '9780143130727', 'A reflective book on purpose, balance and long life.', datetime('now')),
(20, 'Sapiens', 'Yuval Noah Harari', 245000.00, 21, 6, '9780062316097', 'A broad history of humankind and the ideas that shaped it.', datetime('now')),
(21, 'Guns, Germs, and Steel', 'Jared Diamond', 229000.00, 14, 6, '9780393317558', 'A sweeping explanation of how societies evolved differently.', datetime('now')),
(22, 'Steve Jobs', 'Walter Isaacson', 265000.00, 18, 7, '9781451648539', 'A detailed biography of Steve Jobs and Apples rise.', datetime('now')),
(23, 'Educated', 'Tara Westover', 199000.00, 19, 7, '9780399590504', 'A memoir about education, family and self-invention.', datetime('now')),
(24, 'Elon Musk', 'Walter Isaacson', 295000.00, 12, 7, '9781982181284', 'A recent biography of Elon Musk and his companies.', datetime('now'));

-- ========== customer-service ==========
DELETE FROM app_customer;
DELETE FROM sqlite_sequence WHERE name='app_customer';

INSERT INTO app_customer (id, name, email, phone, address, auth_user_id, created_at) VALUES
(1, 'Nguyen Minh An', 'customer1@gmail.com', '0901000001', '12 Nguyen Hue, District 1, Ho Chi Minh City', 3, datetime('now')),
(2, 'Tran Thu Ha', 'customer2@gmail.com', '0901000002', '88 Tran Hung Dao, District 1, Ho Chi Minh City', 4, datetime('now')),
(3, 'Le Quang Huy', 'customer3@gmail.com', '0901000003', '45 Bach Dang, Binh Thanh, Ho Chi Minh City', 5, datetime('now')),
(4, 'Pham Bao Ngoc', 'customer4@gmail.com', '0901000004', '09 Le Loi, Hai Chau, Da Nang', 6, datetime('now')),
(5, 'Hoang Gia Bao', 'customer5@gmail.com', '0901000005', '72 Pham Ngu Lao, District 1, Ho Chi Minh City', 7, datetime('now')),
(6, 'Vo Thanh Nhi', 'customer6@gmail.com', '0901000006', '15 Ly Thuong Kiet, Ninh Kieu, Can Tho', 8, datetime('now')),
(7, 'Dang Tuan Kiet', 'customer7@gmail.com', '0901000007', '120 Nguyen Trai, Thanh Xuan, Ha Noi', 9, datetime('now')),
(8, 'Bui Khanh Linh', 'customer8@gmail.com', '0901000008', '31 Ho Tung Mau, Cau Giay, Ha Noi', 10, datetime('now')),
(9, 'Do Minh Chau', 'customer9@gmail.com', '0901000009', '210 Tran Phu, Hai Chau, Da Nang', 11, datetime('now')),
(10, 'Phan Duc Long', 'customer10@gmail.com', '0901000010', '56 Nguyen Van Cu, Ninh Kieu, Can Tho', 12, datetime('now'));

-- ========== staff-service ==========
DELETE FROM app_staff;
DELETE FROM sqlite_sequence WHERE name='app_staff';

INSERT INTO app_staff (id, name, email, role, auth_user_id, created_at) VALUES
(1, 'Staff User', 'staff@gmail.com', 'staff', 2, datetime('now'));

-- ========== manager-service ==========
DELETE FROM app_manager;
DELETE FROM sqlite_sequence WHERE name='app_manager';

INSERT INTO app_manager (id, name, email, department, auth_user_id, created_at) VALUES
(1, 'Admin User', 'admin@gmail.com', 'Administration', 1, datetime('now'));

-- ========== cart-service ==========
DELETE FROM app_cartitem;
DELETE FROM app_cart;
DELETE FROM sqlite_sequence WHERE name IN ('app_cart', 'app_cartitem');

INSERT INTO app_cart (id, customer_id, created_at) VALUES
(1, 1, datetime('now')),
(2, 2, datetime('now')),
(3, 3, datetime('now')),
(4, 4, datetime('now')),
(5, 5, datetime('now')),
(6, 6, datetime('now')),
(7, 7, datetime('now')),
(8, 8, datetime('now')),
(9, 9, datetime('now')),
(10, 10, datetime('now'));

INSERT INTO app_cartitem (id, cart_id, book_id, quantity) VALUES
(1, 1, 5, 1),
(2, 1, 19, 1),
(3, 2, 3, 1),
(4, 2, 18, 1),
(5, 3, 11, 1),
(6, 3, 16, 1),
(7, 4, 15, 1),
(8, 4, 13, 2),
(9, 5, 8, 1),
(10, 5, 12, 1),
(11, 6, 21, 1),
(12, 6, 24, 1),
(13, 7, 17, 1),
(14, 7, 12, 1),
(15, 8, 6, 1),
(16, 8, 14, 1),
(17, 9, 20, 1),
(18, 9, 2, 1),
(19, 10, 7, 1),
(20, 10, 18, 1);

-- ========== order-service ==========
DELETE FROM app_sagalog;
DELETE FROM app_orderitem;
DELETE FROM app_order;
DELETE FROM sqlite_sequence WHERE name IN ('app_order', 'app_orderitem', 'app_sagalog');

INSERT INTO app_order (id, customer_id, total_amount, status, shipping_address, payment_method, shipping_method, created_at) VALUES
(1, 1, 560000.00, 'COMPLETED', '12 Nguyen Hue, District 1, Ho Chi Minh City', 'COD', 'STANDARD', '2025-10-12 10:00:00'),
(2, 1, 465000.00, 'COMPLETED', '12 Nguyen Hue, District 1, Ho Chi Minh City', 'CREDIT_CARD', 'EXPRESS', '2025-12-05 14:30:00'),
(3, 1, 565000.00, 'COMPLETED', '12 Nguyen Hue, District 1, Ho Chi Minh City', 'PAYPAL', 'STANDARD', '2026-02-01 09:15:00'),
(4, 1, 555000.00, 'SHIPPING', '12 Nguyen Hue, District 1, Ho Chi Minh City', 'CREDIT_CARD', 'EXPRESS', '2026-03-28 16:45:00'),
(5, 2, 299000.00, 'COMPLETED', '88 Tran Hung Dao, District 1, Ho Chi Minh City', 'COD', 'STANDARD', '2025-10-13 10:00:00'),
(6, 2, 334000.00, 'COMPLETED', '88 Tran Hung Dao, District 1, Ho Chi Minh City', 'CREDIT_CARD', 'EXPRESS', '2025-12-06 14:30:00'),
(7, 2, 284000.00, 'COMPLETED', '88 Tran Hung Dao, District 1, Ho Chi Minh City', 'PAYPAL', 'STANDARD', '2026-02-02 09:15:00'),
(8, 2, 264000.00, 'SHIPPING', '88 Tran Hung Dao, District 1, Ho Chi Minh City', 'CREDIT_CARD', 'EXPRESS', '2026-03-29 16:45:00'),
(9, 3, 335000.00, 'COMPLETED', '45 Bach Dang, Binh Thanh, Ho Chi Minh City', 'COD', 'STANDARD', '2025-10-14 10:00:00'),
(10, 3, 408000.00, 'COMPLETED', '45 Bach Dang, Binh Thanh, Ho Chi Minh City', 'CREDIT_CARD', 'EXPRESS', '2025-12-07 14:30:00'),
(11, 3, 364000.00, 'COMPLETED', '45 Bach Dang, Binh Thanh, Ho Chi Minh City', 'PAYPAL', 'STANDARD', '2026-02-03 09:15:00'),
(12, 3, 364000.00, 'SHIPPING', '45 Bach Dang, Binh Thanh, Ho Chi Minh City', 'CREDIT_CARD', 'EXPRESS', '2026-03-30 16:45:00'),
(13, 4, 193000.00, 'COMPLETED', '09 Le Loi, Hai Chau, Da Nang', 'COD', 'STANDARD', '2025-10-15 10:00:00'),
(14, 4, 277000.00, 'COMPLETED', '09 Le Loi, Hai Chau, Da Nang', 'CREDIT_CARD', 'EXPRESS', '2025-12-08 14:30:00'),
(15, 4, 174000.00, 'COMPLETED', '09 Le Loi, Hai Chau, Da Nang', 'PAYPAL', 'STANDARD', '2026-02-04 09:15:00'),
(16, 4, 307000.00, 'SHIPPING', '09 Le Loi, Hai Chau, Da Nang', 'CREDIT_CARD', 'EXPRESS', '2026-03-31 16:45:00'),
(17, 5, 475000.00, 'COMPLETED', '72 Pham Ngu Lao, District 1, Ho Chi Minh City', 'COD', 'STANDARD', '2025-10-16 10:00:00'),
(18, 5, 639000.00, 'COMPLETED', '72 Pham Ngu Lao, District 1, Ho Chi Minh City', 'CREDIT_CARD', 'EXPRESS', '2025-12-09 14:30:00'),
(19, 5, 469000.00, 'COMPLETED', '72 Pham Ngu Lao, District 1, Ho Chi Minh City', 'PAYPAL', 'STANDARD', '2026-02-05 09:15:00'),
(20, 5, 569000.00, 'SHIPPING', '72 Pham Ngu Lao, District 1, Ho Chi Minh City', 'CREDIT_CARD', 'EXPRESS', '2026-04-01 16:45:00'),
(21, 6, 510000.00, 'COMPLETED', '15 Ly Thuong Kiet, Ninh Kieu, Can Tho', 'COD', 'STANDARD', '2025-10-17 10:00:00'),
(22, 6, 428000.00, 'COMPLETED', '15 Ly Thuong Kiet, Ninh Kieu, Can Tho', 'CREDIT_CARD', 'EXPRESS', '2025-12-10 14:30:00'),
(23, 6, 484000.00, 'COMPLETED', '15 Ly Thuong Kiet, Ninh Kieu, Can Tho', 'PAYPAL', 'STANDARD', '2026-02-06 09:15:00'),
(24, 6, 444000.00, 'SHIPPING', '15 Ly Thuong Kiet, Ninh Kieu, Can Tho', 'CREDIT_CARD', 'EXPRESS', '2026-04-02 16:45:00'),
(25, 7, 335000.00, 'COMPLETED', '120 Nguyen Trai, Thanh Xuan, Ha Noi', 'COD', 'STANDARD', '2025-10-18 10:00:00'),
(26, 7, 404000.00, 'COMPLETED', '120 Nguyen Trai, Thanh Xuan, Ha Noi', 'CREDIT_CARD', 'EXPRESS', '2025-12-11 14:30:00'),
(27, 7, 364000.00, 'COMPLETED', '120 Nguyen Trai, Thanh Xuan, Ha Noi', 'PAYPAL', 'STANDARD', '2026-02-07 09:15:00'),
(28, 7, 324000.00, 'SHIPPING', '120 Nguyen Trai, Thanh Xuan, Ha Noi', 'CREDIT_CARD', 'EXPRESS', '2026-04-03 16:45:00'),
(29, 8, 400000.00, 'COMPLETED', '31 Ho Tung Mau, Cau Giay, Ha Noi', 'COD', 'STANDARD', '2025-10-19 10:00:00'),
(30, 8, 588000.00, 'COMPLETED', '31 Ho Tung Mau, Cau Giay, Ha Noi', 'CREDIT_CARD', 'EXPRESS', '2025-12-12 14:30:00'),
(31, 8, 478000.00, 'COMPLETED', '31 Ho Tung Mau, Cau Giay, Ha Noi', 'PAYPAL', 'STANDARD', '2026-02-08 09:15:00'),
(32, 8, 260000.00, 'SHIPPING', '31 Ho Tung Mau, Cau Giay, Ha Noi', 'CREDIT_CARD', 'EXPRESS', '2026-04-04 16:45:00'),
(33, 9, 334000.00, 'COMPLETED', '210 Tran Phu, Hai Chau, Da Nang', 'COD', 'STANDARD', '2025-10-20 10:00:00'),
(34, 9, 378000.00, 'COMPLETED', '210 Tran Phu, Hai Chau, Da Nang', 'CREDIT_CARD', 'EXPRESS', '2025-12-13 14:30:00'),
(35, 9, 338000.00, 'COMPLETED', '210 Tran Phu, Hai Chau, Da Nang', 'PAYPAL', 'STANDARD', '2026-02-09 09:15:00'),
(36, 9, 318000.00, 'SHIPPING', '210 Tran Phu, Hai Chau, Da Nang', 'CREDIT_CARD', 'EXPRESS', '2026-04-05 16:45:00'),
(37, 10, 560000.00, 'COMPLETED', '56 Nguyen Van Cu, Ninh Kieu, Can Tho', 'COD', 'STANDARD', '2025-10-21 10:00:00'),
(38, 10, 405000.00, 'COMPLETED', '56 Nguyen Van Cu, Ninh Kieu, Can Tho', 'CREDIT_CARD', 'EXPRESS', '2025-12-14 14:30:00'),
(39, 10, 575000.00, 'COMPLETED', '56 Nguyen Van Cu, Ninh Kieu, Can Tho', 'PAYPAL', 'STANDARD', '2026-02-10 09:15:00'),
(40, 10, 629000.00, 'SHIPPING', '56 Nguyen Van Cu, Ninh Kieu, Can Tho', 'CREDIT_CARD', 'EXPRESS', '2026-04-06 16:45:00');

INSERT INTO app_orderitem (id, order_id, book_id, quantity, price) VALUES
(1, 1, 4, 1, 350000.00),
(2, 1, 16, 1, 210000.00),
(3, 2, 6, 1, 280000.00),
(4, 2, 17, 1, 185000.00),
(5, 3, 7, 1, 390000.00),
(6, 3, 18, 1, 175000.00),
(7, 4, 8, 1, 410000.00),
(8, 4, 19, 1, 145000.00),
(9, 5, 1, 1, 89000.00),
(10, 5, 16, 1, 210000.00),
(11, 6, 2, 1, 149000.00),
(12, 6, 17, 1, 185000.00),
(13, 7, 3, 1, 139000.00),
(14, 7, 19, 1, 145000.00),
(15, 8, 1, 1, 89000.00),
(16, 8, 18, 1, 175000.00),
(17, 9, 9, 1, 125000.00),
(18, 9, 16, 1, 210000.00),
(19, 10, 10, 1, 219000.00),
(20, 10, 11, 1, 189000.00),
(21, 11, 12, 1, 179000.00),
(22, 11, 17, 1, 185000.00),
(23, 12, 11, 1, 189000.00),
(24, 12, 18, 1, 175000.00),
(25, 13, 13, 1, 25000.00),
(26, 13, 14, 1, 168000.00),
(27, 14, 15, 1, 99000.00),
(28, 14, 1, 2, 89000.00),
(29, 15, 13, 1, 25000.00),
(30, 15, 2, 1, 149000.00),
(31, 16, 14, 1, 168000.00),
(32, 16, 3, 1, 139000.00),
(33, 17, 4, 1, 350000.00),
(34, 17, 9, 1, 125000.00),
(35, 18, 5, 1, 420000.00),
(36, 18, 10, 1, 219000.00),
(37, 19, 6, 1, 280000.00),
(38, 19, 11, 1, 189000.00),
(39, 20, 7, 1, 390000.00),
(40, 20, 12, 1, 179000.00),
(41, 21, 20, 1, 245000.00),
(42, 21, 22, 1, 265000.00),
(43, 22, 21, 1, 229000.00),
(44, 22, 23, 1, 199000.00),
(45, 23, 24, 1, 295000.00),
(46, 23, 11, 1, 189000.00),
(47, 24, 20, 1, 245000.00),
(48, 24, 23, 1, 199000.00),
(49, 25, 16, 1, 210000.00),
(50, 25, 9, 1, 125000.00),
(51, 26, 17, 1, 185000.00),
(52, 26, 10, 1, 219000.00),
(53, 27, 18, 1, 175000.00),
(54, 27, 11, 1, 189000.00),
(55, 28, 19, 1, 145000.00),
(56, 28, 12, 1, 179000.00),
(57, 29, 4, 1, 350000.00),
(58, 29, 13, 2, 25000.00),
(59, 30, 5, 1, 420000.00),
(60, 30, 14, 1, 168000.00),
(61, 31, 6, 1, 280000.00),
(62, 31, 15, 2, 99000.00),
(63, 32, 16, 1, 210000.00),
(64, 32, 13, 2, 25000.00),
(65, 33, 1, 1, 89000.00),
(66, 33, 20, 1, 245000.00),
(67, 34, 2, 1, 149000.00),
(68, 34, 21, 1, 229000.00),
(69, 35, 3, 1, 139000.00),
(70, 35, 23, 1, 199000.00),
(71, 36, 1, 1, 89000.00),
(72, 36, 21, 1, 229000.00),
(73, 37, 4, 1, 350000.00),
(74, 37, 16, 1, 210000.00),
(75, 38, 6, 1, 280000.00),
(76, 38, 9, 1, 125000.00),
(77, 39, 7, 1, 390000.00),
(78, 39, 17, 1, 185000.00),
(79, 40, 8, 1, 410000.00),
(80, 40, 10, 1, 219000.00);

INSERT INTO app_sagalog (id, order_id, step, status, details, created_at)
SELECT id, id, 'CREATE_ORDER', 'SUCCESS', 'Order record created', created_at FROM app_order
UNION ALL
SELECT 40 + id, id, 'FETCH_BOOK_PRICE', 'SUCCESS', printf('Calculated total %.2f', total_amount), created_at FROM app_order
UNION ALL
SELECT 80 + id, id, 'RESERVE_PAYMENT', 'SUCCESS', 'Payment reserved successfully', created_at FROM app_order
UNION ALL
SELECT 120 + id, id, 'RESERVE_SHIPMENT', 'SUCCESS', 'Shipment reserved successfully', created_at FROM app_order
UNION ALL
SELECT 160 + id, id, 'CONFIRM_ORDER', 'SUCCESS', CASE WHEN status = 'COMPLETED' THEN 'Order completed successfully' ELSE 'Order confirmed and in shipping' END, created_at FROM app_order;

-- ========== pay-service ==========
DELETE FROM app_payment;
DELETE FROM sqlite_sequence WHERE name='app_payment';

INSERT INTO app_payment (id, order_id, amount, method, status, created_at) VALUES
(1, 1, 560000.00, 'COD', 'COMPLETED', '2025-10-12 10:00:00'),
(2, 2, 465000.00, 'CREDIT_CARD', 'COMPLETED', '2025-12-05 14:30:00'),
(3, 3, 565000.00, 'PAYPAL', 'COMPLETED', '2026-02-01 09:15:00'),
(4, 4, 555000.00, 'CREDIT_CARD', 'COMPLETED', '2026-03-28 16:45:00'),
(5, 5, 299000.00, 'COD', 'COMPLETED', '2025-10-13 10:00:00'),
(6, 6, 334000.00, 'CREDIT_CARD', 'COMPLETED', '2025-12-06 14:30:00'),
(7, 7, 284000.00, 'PAYPAL', 'COMPLETED', '2026-02-02 09:15:00'),
(8, 8, 264000.00, 'CREDIT_CARD', 'COMPLETED', '2026-03-29 16:45:00'),
(9, 9, 335000.00, 'COD', 'COMPLETED', '2025-10-14 10:00:00'),
(10, 10, 408000.00, 'CREDIT_CARD', 'COMPLETED', '2025-12-07 14:30:00'),
(11, 11, 364000.00, 'PAYPAL', 'COMPLETED', '2026-02-03 09:15:00'),
(12, 12, 364000.00, 'CREDIT_CARD', 'COMPLETED', '2026-03-30 16:45:00'),
(13, 13, 193000.00, 'COD', 'COMPLETED', '2025-10-15 10:00:00'),
(14, 14, 277000.00, 'CREDIT_CARD', 'COMPLETED', '2025-12-08 14:30:00'),
(15, 15, 174000.00, 'PAYPAL', 'COMPLETED', '2026-02-04 09:15:00'),
(16, 16, 307000.00, 'CREDIT_CARD', 'COMPLETED', '2026-03-31 16:45:00'),
(17, 17, 475000.00, 'COD', 'COMPLETED', '2025-10-16 10:00:00'),
(18, 18, 639000.00, 'CREDIT_CARD', 'COMPLETED', '2025-12-09 14:30:00'),
(19, 19, 469000.00, 'PAYPAL', 'COMPLETED', '2026-02-05 09:15:00'),
(20, 20, 569000.00, 'CREDIT_CARD', 'COMPLETED', '2026-04-01 16:45:00'),
(21, 21, 510000.00, 'COD', 'COMPLETED', '2025-10-17 10:00:00'),
(22, 22, 428000.00, 'CREDIT_CARD', 'COMPLETED', '2025-12-10 14:30:00'),
(23, 23, 484000.00, 'PAYPAL', 'COMPLETED', '2026-02-06 09:15:00'),
(24, 24, 444000.00, 'CREDIT_CARD', 'COMPLETED', '2026-04-02 16:45:00'),
(25, 25, 335000.00, 'COD', 'COMPLETED', '2025-10-18 10:00:00'),
(26, 26, 404000.00, 'CREDIT_CARD', 'COMPLETED', '2025-12-11 14:30:00'),
(27, 27, 364000.00, 'PAYPAL', 'COMPLETED', '2026-02-07 09:15:00'),
(28, 28, 324000.00, 'CREDIT_CARD', 'COMPLETED', '2026-04-03 16:45:00'),
(29, 29, 400000.00, 'COD', 'COMPLETED', '2025-10-19 10:00:00'),
(30, 30, 588000.00, 'CREDIT_CARD', 'COMPLETED', '2025-12-12 14:30:00'),
(31, 31, 478000.00, 'PAYPAL', 'COMPLETED', '2026-02-08 09:15:00'),
(32, 32, 260000.00, 'CREDIT_CARD', 'COMPLETED', '2026-04-04 16:45:00'),
(33, 33, 334000.00, 'COD', 'COMPLETED', '2025-10-20 10:00:00'),
(34, 34, 378000.00, 'CREDIT_CARD', 'COMPLETED', '2025-12-13 14:30:00'),
(35, 35, 338000.00, 'PAYPAL', 'COMPLETED', '2026-02-09 09:15:00'),
(36, 36, 318000.00, 'CREDIT_CARD', 'COMPLETED', '2026-04-05 16:45:00'),
(37, 37, 560000.00, 'COD', 'COMPLETED', '2025-10-21 10:00:00'),
(38, 38, 405000.00, 'CREDIT_CARD', 'COMPLETED', '2025-12-14 14:30:00'),
(39, 39, 575000.00, 'PAYPAL', 'COMPLETED', '2026-02-10 09:15:00'),
(40, 40, 629000.00, 'CREDIT_CARD', 'COMPLETED', '2026-04-06 16:45:00');

-- ========== ship-service ==========
DELETE FROM app_shipment;
DELETE FROM sqlite_sequence WHERE name='app_shipment';

INSERT INTO app_shipment (id, order_id, address, method, status, tracking_number, created_at) VALUES
(1, 1, '12 Nguyen Hue, District 1, Ho Chi Minh City', 'STANDARD', 'DELIVERED', 'TRK-00001', '2025-10-12 10:00:00'),
(2, 2, '12 Nguyen Hue, District 1, Ho Chi Minh City', 'EXPRESS', 'DELIVERED', 'TRK-00002', '2025-12-05 14:30:00'),
(3, 3, '12 Nguyen Hue, District 1, Ho Chi Minh City', 'STANDARD', 'DELIVERED', 'TRK-00003', '2026-02-01 09:15:00'),
(4, 4, '12 Nguyen Hue, District 1, Ho Chi Minh City', 'EXPRESS', 'SHIPPED', 'TRK-00004', '2026-03-28 16:45:00'),
(5, 5, '88 Tran Hung Dao, District 1, Ho Chi Minh City', 'STANDARD', 'DELIVERED', 'TRK-00005', '2025-10-13 10:00:00'),
(6, 6, '88 Tran Hung Dao, District 1, Ho Chi Minh City', 'EXPRESS', 'DELIVERED', 'TRK-00006', '2025-12-06 14:30:00'),
(7, 7, '88 Tran Hung Dao, District 1, Ho Chi Minh City', 'STANDARD', 'DELIVERED', 'TRK-00007', '2026-02-02 09:15:00'),
(8, 8, '88 Tran Hung Dao, District 1, Ho Chi Minh City', 'EXPRESS', 'SHIPPED', 'TRK-00008', '2026-03-29 16:45:00'),
(9, 9, '45 Bach Dang, Binh Thanh, Ho Chi Minh City', 'STANDARD', 'DELIVERED', 'TRK-00009', '2025-10-14 10:00:00'),
(10, 10, '45 Bach Dang, Binh Thanh, Ho Chi Minh City', 'EXPRESS', 'DELIVERED', 'TRK-00010', '2025-12-07 14:30:00'),
(11, 11, '45 Bach Dang, Binh Thanh, Ho Chi Minh City', 'STANDARD', 'DELIVERED', 'TRK-00011', '2026-02-03 09:15:00'),
(12, 12, '45 Bach Dang, Binh Thanh, Ho Chi Minh City', 'EXPRESS', 'SHIPPED', 'TRK-00012', '2026-03-30 16:45:00'),
(13, 13, '09 Le Loi, Hai Chau, Da Nang', 'STANDARD', 'DELIVERED', 'TRK-00013', '2025-10-15 10:00:00'),
(14, 14, '09 Le Loi, Hai Chau, Da Nang', 'EXPRESS', 'DELIVERED', 'TRK-00014', '2025-12-08 14:30:00'),
(15, 15, '09 Le Loi, Hai Chau, Da Nang', 'STANDARD', 'DELIVERED', 'TRK-00015', '2026-02-04 09:15:00'),
(16, 16, '09 Le Loi, Hai Chau, Da Nang', 'EXPRESS', 'SHIPPED', 'TRK-00016', '2026-03-31 16:45:00'),
(17, 17, '72 Pham Ngu Lao, District 1, Ho Chi Minh City', 'STANDARD', 'DELIVERED', 'TRK-00017', '2025-10-16 10:00:00'),
(18, 18, '72 Pham Ngu Lao, District 1, Ho Chi Minh City', 'EXPRESS', 'DELIVERED', 'TRK-00018', '2025-12-09 14:30:00'),
(19, 19, '72 Pham Ngu Lao, District 1, Ho Chi Minh City', 'STANDARD', 'DELIVERED', 'TRK-00019', '2026-02-05 09:15:00'),
(20, 20, '72 Pham Ngu Lao, District 1, Ho Chi Minh City', 'EXPRESS', 'SHIPPED', 'TRK-00020', '2026-04-01 16:45:00'),
(21, 21, '15 Ly Thuong Kiet, Ninh Kieu, Can Tho', 'STANDARD', 'DELIVERED', 'TRK-00021', '2025-10-17 10:00:00'),
(22, 22, '15 Ly Thuong Kiet, Ninh Kieu, Can Tho', 'EXPRESS', 'DELIVERED', 'TRK-00022', '2025-12-10 14:30:00'),
(23, 23, '15 Ly Thuong Kiet, Ninh Kieu, Can Tho', 'STANDARD', 'DELIVERED', 'TRK-00023', '2026-02-06 09:15:00'),
(24, 24, '15 Ly Thuong Kiet, Ninh Kieu, Can Tho', 'EXPRESS', 'SHIPPED', 'TRK-00024', '2026-04-02 16:45:00'),
(25, 25, '120 Nguyen Trai, Thanh Xuan, Ha Noi', 'STANDARD', 'DELIVERED', 'TRK-00025', '2025-10-18 10:00:00'),
(26, 26, '120 Nguyen Trai, Thanh Xuan, Ha Noi', 'EXPRESS', 'DELIVERED', 'TRK-00026', '2025-12-11 14:30:00'),
(27, 27, '120 Nguyen Trai, Thanh Xuan, Ha Noi', 'STANDARD', 'DELIVERED', 'TRK-00027', '2026-02-07 09:15:00'),
(28, 28, '120 Nguyen Trai, Thanh Xuan, Ha Noi', 'EXPRESS', 'SHIPPED', 'TRK-00028', '2026-04-03 16:45:00'),
(29, 29, '31 Ho Tung Mau, Cau Giay, Ha Noi', 'STANDARD', 'DELIVERED', 'TRK-00029', '2025-10-19 10:00:00'),
(30, 30, '31 Ho Tung Mau, Cau Giay, Ha Noi', 'EXPRESS', 'DELIVERED', 'TRK-00030', '2025-12-12 14:30:00'),
(31, 31, '31 Ho Tung Mau, Cau Giay, Ha Noi', 'STANDARD', 'DELIVERED', 'TRK-00031', '2026-02-08 09:15:00'),
(32, 32, '31 Ho Tung Mau, Cau Giay, Ha Noi', 'EXPRESS', 'SHIPPED', 'TRK-00032', '2026-04-04 16:45:00'),
(33, 33, '210 Tran Phu, Hai Chau, Da Nang', 'STANDARD', 'DELIVERED', 'TRK-00033', '2025-10-20 10:00:00'),
(34, 34, '210 Tran Phu, Hai Chau, Da Nang', 'EXPRESS', 'DELIVERED', 'TRK-00034', '2025-12-13 14:30:00'),
(35, 35, '210 Tran Phu, Hai Chau, Da Nang', 'STANDARD', 'DELIVERED', 'TRK-00035', '2026-02-09 09:15:00'),
(36, 36, '210 Tran Phu, Hai Chau, Da Nang', 'EXPRESS', 'SHIPPED', 'TRK-00036', '2026-04-05 16:45:00'),
(37, 37, '56 Nguyen Van Cu, Ninh Kieu, Can Tho', 'STANDARD', 'DELIVERED', 'TRK-00037', '2025-10-21 10:00:00'),
(38, 38, '56 Nguyen Van Cu, Ninh Kieu, Can Tho', 'EXPRESS', 'DELIVERED', 'TRK-00038', '2025-12-14 14:30:00'),
(39, 39, '56 Nguyen Van Cu, Ninh Kieu, Can Tho', 'STANDARD', 'DELIVERED', 'TRK-00039', '2026-02-10 09:15:00'),
(40, 40, '56 Nguyen Van Cu, Ninh Kieu, Can Tho', 'EXPRESS', 'SHIPPED', 'TRK-00040', '2026-04-06 16:45:00');

-- ========== comment-rate-service ==========
DELETE FROM app_review;
DELETE FROM sqlite_sequence WHERE name='app_review';

INSERT INTO app_review (id, book_id, customer_id, rating, comment, created_at) VALUES
(1, 4, 1, 5, 'Good examples and a clear structure for learning.', '2026-03-01 19:30:00'),
(2, 16, 1, 5, 'A useful book for building better routines and focus.', '2026-03-02 19:30:00'),
(3, 6, 1, 5, 'Practical and directly useful for real software work.', '2026-03-03 19:30:00'),
(4, 17, 1, 4, 'Motivating without feeling too abstract.', '2026-03-04 19:30:00'),
(5, 1, 2, 5, 'Strong storytelling and characters that stay with you.', '2026-03-03 19:30:00'),
(6, 16, 2, 5, 'Actionable advice that is easy to put into practice.', '2026-03-04 19:30:00'),
(7, 2, 2, 4, 'Very readable and memorable from beginning to end.', '2026-03-05 19:30:00'),
(8, 17, 2, 5, 'A useful book for building better routines and focus.', '2026-03-06 19:30:00'),
(9, 9, 3, 5, 'Easy to apply and full of useful business insights.', '2026-03-05 19:30:00'),
(10, 16, 3, 4, 'Motivating without feeling too abstract.', '2026-03-06 19:30:00'),
(11, 10, 3, 5, 'A solid book if you want better money and startup thinking.', '2026-03-07 19:30:00'),
(12, 11, 3, 5, 'Easy to apply and full of useful business insights.', '2026-03-08 19:30:00'),
(13, 13, 4, 4, 'A charming pick for family reading time.', '2026-03-07 19:30:00'),
(14, 14, 4, 5, 'Simple, engaging and full of imagination.', '2026-03-08 19:30:00'),
(15, 15, 4, 5, 'Fun, light and very easy to recommend to younger readers.', '2026-03-09 19:30:00'),
(16, 1, 4, 5, 'Very readable and memorable from beginning to end.', '2026-03-10 19:30:00'),
(17, 4, 5, 5, 'Helpful if you want to build stronger engineering habits.', '2026-03-09 19:30:00'),
(18, 9, 5, 5, 'Easy to apply and full of useful business insights.', '2026-03-10 19:30:00'),
(19, 5, 5, 5, 'Good examples and a clear structure for learning.', '2026-03-11 19:30:00'),
(20, 10, 5, 4, 'A solid book if you want better money and startup thinking.', '2026-03-12 19:30:00'),
(21, 20, 6, 5, 'Broad and insightful, with a lot to think about.', '2026-03-11 19:30:00'),
(22, 22, 6, 5, 'Readable and informative with strong narrative flow.', '2026-03-12 19:30:00'),
(23, 21, 6, 4, 'Dense in places, but very rewarding overall.', '2026-03-13 19:30:00'),
(24, 23, 6, 5, 'A detailed life story with many memorable moments.', '2026-03-14 19:30:00'),
(25, 16, 7, 5, 'Motivating without feeling too abstract.', '2026-03-13 19:30:00'),
(26, 9, 7, 4, 'A solid book if you want better money and startup thinking.', '2026-03-14 19:30:00'),
(27, 17, 7, 5, 'Actionable advice that is easy to put into practice.', '2026-03-15 19:30:00'),
(28, 10, 7, 5, 'Balanced advice with examples that feel realistic.', '2026-03-16 19:30:00'),
(29, 4, 8, 4, 'Helpful if you want to build stronger engineering habits.', '2026-03-15 19:30:00'),
(30, 13, 8, 5, 'Fun, light and very easy to recommend to younger readers.', '2026-03-16 19:30:00'),
(31, 5, 8, 5, 'Good examples and a clear structure for learning.', '2026-03-17 19:30:00'),
(32, 14, 8, 5, 'Simple, engaging and full of imagination.', '2026-03-18 19:30:00'),
(33, 1, 9, 5, 'A thoughtful novel with a warm emotional core.', '2026-03-17 19:30:00'),
(34, 20, 9, 5, 'A strong overview of history written in an engaging way.', '2026-03-18 19:30:00'),
(35, 2, 9, 5, 'Strong storytelling and characters that stay with you.', '2026-03-19 19:30:00'),
(36, 21, 9, 4, 'Broad and insightful, with a lot to think about.', '2026-03-20 19:30:00'),
(37, 4, 10, 5, 'Good examples and a clear structure for learning.', '2026-03-19 19:30:00'),
(38, 16, 10, 5, 'A useful book for building better routines and focus.', '2026-03-20 19:30:00'),
(39, 6, 10, 4, 'Practical and directly useful for real software work.', '2026-03-21 19:30:00'),
(40, 9, 10, 5, 'Balanced advice with examples that feel realistic.', '2026-03-22 19:30:00');
