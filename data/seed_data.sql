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
-- The product / book / electronics / fashion catalogue and the demo
-- cart / order / review rows are now generated from the real Amazon Books
-- dataset (Kaggle) instead of being hand-written here.
--
-- See:  ai-service/data/seed_data_books.sql   (produced by `make preprocess`)
-- which data/seed_all.sh loads into product_db immediately after this file.
