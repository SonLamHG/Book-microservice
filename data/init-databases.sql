-- PostgreSQL — bootstrap per-service databases.
-- The four User-Context databases (auth_db, customer_db, staff_db,
-- manager_db) live on the MySQL container instead — see data/init-mysql.sql.
CREATE DATABASE catalog_db;
CREATE DATABASE product_db;
CREATE DATABASE cart_db;
CREATE DATABASE order_db;
CREATE DATABASE payment_db;
CREATE DATABASE shipping_db;
CREATE DATABASE comment_db;
CREATE DATABASE advisory_db;
