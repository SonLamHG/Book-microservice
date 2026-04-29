-- Seed data for the MySQL-hosted User Context databases.
-- Three sections, one per database. seed_all.sh extracts each section
-- and runs it against the matching DB on the `mysql` container.
--
-- MySQL syntax notes:
--   * `ON CONFLICT (id) DO NOTHING` (PostgreSQL) is rewritten as
--     `INSERT IGNORE INTO ...` (MySQL).
--   * NOW() is fine in both engines.
--   * MySQL AUTO_INCREMENT auto-advances past explicit IDs on InnoDB.

-- ========== customer-service ==========
INSERT IGNORE INTO app_customer (id, name, email, phone, address, auth_user_id, created_at) VALUES
(1, 'Nguyen Van A', 'nguyenvana@gmail.com', '0901234567', '123 Le Loi, Q1, TP.HCM', 5, NOW()),
(2, 'Tran Thi B', 'tranthib@gmail.com', '0912345678', '456 Nguyen Hue, Q1, TP.HCM', 6, NOW()),
(3, 'Le Van C', 'levanc@gmail.com', '0923456789', '789 Hai Ba Trung, Q3, TP.HCM', 7, NOW()),
(4, 'Pham Thi D', 'phamthid@gmail.com', '0934567890', '321 Tran Hung Dao, Q5, TP.HCM', 8, NOW()),
(5, 'Hoang E', 'hoange@gmail.com', '0945678901', '654 Vo Van Tan, Q3, TP.HCM', 9, NOW());

-- ========== staff-service ==========
INSERT IGNORE INTO app_staff (id, name, email, role, auth_user_id, created_at) VALUES
(1, 'Nhan Vien 1', 'staff1@bookstore.vn', 'staff', 3, NOW()),
(2, 'Nhan Vien 2', 'staff2@bookstore.vn', 'staff', 4, NOW());

-- ========== manager-service ==========
INSERT IGNORE INTO app_manager (id, name, email, department, auth_user_id, created_at) VALUES
(1, 'Quan Ly 1', 'manager1@bookstore.vn', 'Operations', 2, NOW());
