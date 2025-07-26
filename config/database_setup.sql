-- Create database
CREATE DATABASE IF NOT EXISTS database_card_store;

-- Create dedicated user (password will be set from .env)
CREATE USER IF NOT EXISTS 'signal_automation'@'localhost' IDENTIFIED BY 'PLACEHOLDER_PASSWORD';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON database_card_store.affiliates TO 'signal_automation'@'localhost';
GRANT SELECT, UPDATE ON database_card_store.orders TO 'signal_automation'@'localhost';

-- Create affiliates table
USE database_card_store;

CREATE TABLE IF NOT EXISTS affiliates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    token CHAR(12) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_phone (phone_number),
    INDEX idx_token (token)
);

-- Create orders table (if not exists from n8n)
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client VARCHAR(255),
    total DECIMAL(10,2),
    ip_address VARCHAR(45),
    affiliate_token CHAR(12),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notified BOOLEAN DEFAULT FALSE,
    INDEX idx_affiliate_token (affiliate_token),
    INDEX idx_notified (notified),
    INDEX idx_created_at (created_at)
);

FLUSH PRIVILEGES;
