-- create test databases
CREATE DATABASE IF NOT EXISTS `test_db`;

GRANT ALL PRIVILEGES ON test_db.* TO 'embark'@'%';
