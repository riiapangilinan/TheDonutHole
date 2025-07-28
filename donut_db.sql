-- Create and use database
CREATE DATABASE IF NOT EXISTS donut_hole;
USE donut_hole;

-- Drop existing tables if needed
DROP TABLE IF EXISTS transactions, order_items, orders, currencies, products, users, user_carts, product_updates, phased_out_products, low_stock_products;

-- USERS
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('customer', 'staff', 'admin') DEFAULT 'customer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- PRODUCTS
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INT,
    description TEXT,
    image VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE
);

-- USER CARTS
CREATE TABLE user_carts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE(user_id, product_id)
);

-- ORDERS
CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    total DECIMAL(10, 2) DEFAULT 0.00,
    status ENUM('Paid', 'Cancelled', 'Shipped') DEFAULT 'Paid',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ORDER ITEMS
CREATE TABLE order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT,
    product_id INT,
    quantity INT DEFAULT 1,
    price DECIMAL(10, 2),
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- CURRENCIES
CREATE TABLE currencies (
    code VARCHAR(5) PRIMARY KEY,
    symbol VARCHAR(5),
    exchange_rate_to_php DECIMAL(10, 4) DEFAULT 1.0000,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- TRANSACTIONS
CREATE TABLE transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT,
    amount DECIMAL(10,2),
    payment_method VARCHAR(50),
    status ENUM('Success', 'Failed') DEFAULT 'Success',
    paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

INSERT INTO products (name, price, stock_quantity, description, image) VALUES
('Original Glazed', 55.00, 20, 'A timeless classic with a golden, melt-in-your-mouth glaze that’s perfectly sweet, fluffy.', 'menu-1.png'),
('Hazelnut Drizzle', 70.00, 20, 'Rich, roasted hazelnut glaze cascading over a delicate donut.', 'menu-2.png'),
('Creme Brulee', 80.00, 20, 'Luscious, custard-filled delight topped with a caramelized sugar that cracks perfectly with every bite.', 'menu-3.png'),
('Orange Pistachio', 80.00, 20, 'Zesty orange-infused glaze, topped with crunchy crushed pistachios.', 'menu-4.png'),
('Fruit Punch Summer', 70.00, 20, 'A celebration of juicy strawberries, blueberries, and raspberries for the summer.', 'menu-5.png'),
('Bundles', 370.00, 10, 'A sunshine-filled box with 2 classic Glazed + 4 of our hottest summer specialties.', 'menu-6.png');

INSERT INTO currencies (code, symbol, exchange_rate_to_php) VALUES
('PHP', '₱', 1.0000),
('USD', '$', 56.0000),
('EUR', '€', 61.0000);


-- STORED PROCEDURES --

DROP PROCEDURE IF EXISTS get_user_orders;
DELIMITER //
CREATE PROCEDURE get_user_orders(IN p_user_id INT)
BEGIN
    SELECT
        o.id as order_id,
        o.total,
        o.status,
        o.created_at,
        t.payment_method,
        t.status as transaction_status
    FROM orders o
    LEFT JOIN transactions t ON o.id = t.order_id
    WHERE o.user_id = p_user_id
    ORDER BY o.created_at DESC;
END //
DELIMITER ;


DROP PROCEDURE IF EXISTS add_product;
DELIMITER //
CREATE PROCEDURE add_product(IN pname VARCHAR(255), IN pdesc TEXT, IN pprice DECIMAL(10,2), IN pstock INT, IN p_image VARCHAR(255))
BEGIN
    INSERT INTO products (name, description, price, stock_quantity, image, is_active)
    VALUES (pname, pdesc, pprice, pstock, p_image, TRUE);
END //
DELIMITER ;


DROP PROCEDURE IF EXISTS create_order;
DELIMITER //
CREATE PROCEDURE create_order(
    IN p_user_id INT, 
    IN p_total DECIMAL(10,2), 
    IN p_items JSON
)
BEGIN
    DECLARE p_order_id INT;
    DECLARE i INT DEFAULT 0;
    DECLARE item_count INT;
    DECLARE p_id INT;
    DECLARE p_qty INT;
    DECLARE p_price DECIMAL(10, 2);


    IF (SELECT COUNT(*) FROM users WHERE id = p_user_id) = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'User does not exist.';
    END IF;

    INSERT INTO orders (user_id, total, status) VALUES (p_user_id, p_total, 'Paid');
    SET p_order_id = LAST_INSERT_ID();

    SET item_count = JSON_LENGTH(p_items);

    WHILE i < item_count DO
        SET p_id = JSON_UNQUOTE(JSON_EXTRACT(p_items, CONCAT('$[', i, '].id')));
        SET p_qty = JSON_UNQUOTE(JSON_EXTRACT(p_items, CONCAT('$[', i, '].quantity')));
        SET p_price = JSON_UNQUOTE(JSON_EXTRACT(p_items, CONCAT('$[', i, '].price')));

        INSERT INTO order_items (order_id, product_id, quantity, price)
        VALUES (p_order_id, p_id, p_qty, p_price);

        UPDATE products SET stock_quantity = stock_quantity - p_qty WHERE id = p_id;

        SET i = i + 1;
    END WHILE;

    SELECT p_order_id as order_id;

END //
DELIMITER ;


DROP PROCEDURE IF EXISTS record_transaction;
DELIMITER //
CREATE PROCEDURE record_transaction(IN oid INT, IN amt DECIMAL(10,2), IN pmethod VARCHAR(50), IN tstatus ENUM('Success', 'Failed'))
BEGIN
    INSERT INTO transactions (order_id, amount, payment_method, status)
    VALUES (oid, amt, pmethod, tstatus);
END //
DELIMITER ;

-- TRIGGERS --

-- 1. Product Edit Archive
CREATE TABLE product_updates(
	edit_id int AUTO_INCREMENT PRIMARY KEY,
    id int,
	name varchar(100),
	price decimal(10,2),
	stock_quantity int,
	description text,
	image varchar(255),
    edit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
DELIMITER //
CREATE TRIGGER product_update
AFTER UPDATE ON products
FOR EACH ROW
BEGIN
	INSERT INTO product_updates (id, name, price, stock_quantity, description, image)
    VALUES (NEW.id, NEW.name, NEW.price, NEW.stock_quantity, NEW.description, NEW.image);
END
// DELIMITER ;

-- 2. Product Deletion Archive
CREATE TABLE phased_out_products(
	deletion_id int AUTO_INCREMENT PRIMARY KEY,
    id int,
	name varchar(100),
	price decimal(10,2),
	description text,
	image varchar(255),
    deletion_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
DELIMITER //
CREATE TRIGGER deleted_products_archive
BEFORE DELETE ON products
FOR EACH ROW
BEGIN
	INSERT INTO phased_out_products (id, name, price, description, image)
    VALUES (OLD.id, OLD.name, OLD.price, OLD.description, OLD.image);
END
// DELIMITER ;

-- 3. Prevent Negative Stock
DELIMITER //
CREATE TRIGGER prevent_negative_stock
BEFORE UPDATE ON products
FOR EACH ROW
BEGIN
	IF NEW.stock_quantity < 0 THEN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'Stock is lesser than indicated quantity';
    END IF;
END
// DELIMITER ;

-- 4. No negative stock when publishing new product
DELIMITER //
CREATE TRIGGER prevent_negative_new_product
BEFORE INSERT ON products
FOR EACH ROW
BEGIN
	IF NEW.stock_quantity < 1 THEN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'Indicated Stock is less than 0';
    END IF;
END
// DELIMITER ;

-- 5. Low Stock Product Log
CREATE TABLE low_stock_products(
	entry_id int AUTO_INCREMENT PRIMARY KEY,
    id int,
	name varchar(100),
    stock_quantity int,
    report_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

DELIMITER //
CREATE TRIGGER low_stock_alerts
AFTER UPDATE ON products
FOR EACH ROW
BEGIN
	IF NEW.stock_quantity <= 3 THEN
    INSERT INTO low_stock_products (id, name, stock_quantity)
    VALUES (NEW.id, NEW.name, NEW.stock_quantity);
    END IF;
END
// DELIMITER ;

-- 6. Return Stock on Cancellation
DELIMITER //
CREATE TRIGGER return_stock_on_cancellation
AFTER UPDATE ON orders
FOR EACH ROW
BEGIN
    IF NEW.status = 'Cancelled' AND OLD.status != 'Cancelled' THEN
        UPDATE products p
        JOIN order_items oi ON p.id = oi.product_id
        SET p.stock_quantity = p.stock_quantity + oi.quantity
        WHERE oi.order_id = NEW.id;
    END IF;
END;
// DELIMITER ;

INSERT INTO users (email, name, password_hash, role)
VALUES (
  'admin@donuthole.com',
  'Admin User',
  'scrypt:32768:8:1$tif99edtaUE11gTf$ada67857cc2bf16e3b66f8aec54d3747d3b02373499abd98178d4c10b1b5463db9a4f7f9eb6901ef783fdc913b7998b64c68c70d311916d381d57f559cfc3590', 
  'admin'
);

-- ROLE-BASED ACCESS CONTROL --

-- Drop roles if they exist for a reset
DROP ROLE IF EXISTS 'customer_role', 'staff_role', 'admin_role';

-- Create the new roles
CREATE ROLE 'customer_role', 'staff_role', 'admin_role';

-- Grant permissions to roles

-- A. customer_role Permissions
GRANT SELECT ON donut_hole.products TO 'customer_role';
GRANT SELECT ON donut_hole.currencies TO 'customer_role';
GRANT EXECUTE ON PROCEDURE donut_hole.create_order TO 'customer_role';
GRANT EXECUTE ON PROCEDURE donut_hole.get_user_orders TO 'customer_role';

-- B. staff_role Permissions
GRANT 'customer_role' TO 'staff_role';
GRANT SELECT ON donut_hole.orders TO 'staff_role';
GRANT SELECT ON donut_hole.order_items TO 'staff_role';
GRANT SELECT ON donut_hole.users TO 'staff_role';
GRANT UPDATE(status) ON donut_hole.orders TO 'staff_role';

-- C. admin_role Permissions
GRANT 'staff_role' TO 'admin_role';
GRANT SELECT, INSERT, UPDATE, DELETE ON donut_hole.products TO 'admin_role';
GRANT SELECT, INSERT, UPDATE, DELETE ON donut_hole.users TO 'admin_role';
GRANT SELECT, UPDATE ON donut_hole.currencies TO 'admin_role';
GRANT SELECT ON donut_hole.product_updates TO 'admin_role';
GRANT SELECT ON donut_hole.phased_out_products TO 'admin_role';
GRANT SELECT ON donut_hole.low_stock_products TO 'admin_role';
GRANT SELECT ON donut_hole.transactions TO 'admin_role';
GRANT EXECUTE ON PROCEDURE donut_hole.add_product TO 'admin_role';

FLUSH PRIVILEGES;
