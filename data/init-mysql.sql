-- Bootstrap MySQL with the four User-Context databases.
-- Runs once on first container init from /docker-entrypoint-initdb.d/.
CREATE DATABASE IF NOT EXISTS auth_db     CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS customer_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS staff_db    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS manager_db  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
