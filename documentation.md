# The Donut Hole - Project Documentation

## 1. Project Overview

The Donut Hole is a full-stack web application for an online donut shop. It's built with Python's Flask framework on the backend, a MySQL database for data persistence, and standard HTML, CSS, and JavaScript on the frontend. The application provides features for customers to browse products, manage a shopping cart, and place orders. It also includes an admin panel for managing products, and a staff panel for viewing orders.

## 2. Database Schema

The application uses a MySQL database named `donut_hole`. The schema is designed to support all the functionalities of the online store, from user management to order processing.

### 2.1. Tables

- **`users`**: Stores user information, including credentials and roles (`customer`, `staff`, `admin`).
- **`products`**: Contains details about the donuts, including price, stock levels, and an `is_active` flag to control visibility.
- **`user_carts`**: Manages the items in each user's shopping cart.
- **`orders`**: Header table for customer orders, containing information like total amount and status.
- **`order_items`**: Line items for each order, linking products to orders.
- **`currencies`**: Stores currency information and exchange rates to support multi-currency display at checkout.
- **`transactions`**: Records payment transactions for each order.
- **`product_updates`**: An archive table that logs all updates made to products, used for auditing purposes.
- **`phased_out_products`**: An archive table that stores products that have been deleted from the main `products` table.
- **`low_stock_products`**: A log table that records when a product's stock falls below a certain threshold (<= 3).

### 2.2. Stored Procedures

The database utilizes stored procedures to encapsulate and centralize key business logic.

- **`get_user_orders(p_user_id)`**: Retrieves the order history for a specific user.
- **`add_product(pname, pdesc, pprice, pstock, p_image)`**: Adds a new product to the `products` table, including its name, description, price, stock quantity, and image filename.
- **`create_order(p_user_id, p_total, p_items)`**: Creates a new order, adds the corresponding items to `order_items`, and decrements the stock for each product. This is an atomic transaction.
- **`record_transaction(...)`**: Records a payment transaction and links it to an order.
- **`update_user_role(p_user_id, p_new_role)`**: Updates the role of a user.

### 2.3. Triggers

Triggers are used to enforce data integrity and automate logging.

- **`product_update`**: After any update on the `products` table, this trigger archives the new state of the product into the `product_updates` table.
- **`deleted_products_archive`**: Before a product is deleted, this trigger saves the old product data into the `phased_out_products` table.
- **`prevent_negative_stock`**: Before a product's stock is updated, this trigger checks if the new quantity would be negative and, if so, raises an error to prevent the update.
- **`prevent_negative_new_product`**: Before a new product is inserted, this trigger ensures its initial stock is not less than 1.
- **`low_stock_alerts`**: After a product's stock is updated, if the new quantity is 3 or less, this trigger logs the product details into the `low_stock_products` table.
- **`return_stock_on_cancellation`**: After an order's status is updated to `Cancelled`, this trigger automatically returns the quantities of the order items back to the main `products` stock.

## 3. COMMIT/ROLLBACK Implementation (Transaction Management)

The application ensures data integrity and atomicity for critical database operations, especially during the checkout process, by using transactions with `COMMIT` and `ROLLBACK`.

This is primarily managed in `main.py` through the `db_transaction` context manager:

```python
@contextmanager
def db_transaction():
    """Context manager that handles database transactions with automatic rollback on errors"""
    conn = get_db_connection()
    if not conn:
        raise Exception("Failed to connect to database")
    
    try:
        cursor = conn.cursor(dictionary=True)
        yield conn, cursor
        conn.commit()
        print("Transaction committed successfully")
    except Exception as e:
        conn.rollback()
        print(f"Transaction rolled back due to error: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
```

### How it Works:

1.  **`autocommit=False`**: The database connection is initialized with `autocommit` turned off. This means that changes to the database are not saved immediately.
2.  **`try...except` Block**: All database operations within a `with db_transaction():` block are executed within a `try` block.
3.  **`conn.commit()`**: If all operations within the block complete without any errors, `conn.commit()` is called. This saves all the changes made during the transaction to the database.
4.  **`conn.rollback()`**: If any exception occurs (e.g., a database error, a validation failure like the `prevent_negative_stock` trigger firing), the `except` block is executed. `conn.rollback()` is called, which undoes all changes made since the transaction began. This ensures the database is left in a consistent state.

This is crucial in the `/submit_checkout` route, where multiple database operations (validating stock, creating an order, adding order items, updating stock, recording a transaction, and clearing the cart) must all succeed or fail together as a single atomic unit.

## 4. Role-Based Access Control (RBAC)

The application implements a robust Role-Based Access Control (RBAC) system to manage user permissions. This is enforced at both the database level and the application (Flask) level.

### 4.1. Roles

There are three defined roles in the system:

- **`customer`**: The default role for registered users. They can browse products, manage their cart, place orders, and view their own order history.
- **`staff`**: An intermediate role with more permissions than a customer. They can view all customer orders and manage their status.
- **`admin`**: The highest-level role. Admins have full control over the application, including product management and user management.

### 4.2. Database-Level RBAC

In `donut_db.sql`, SQL roles (`customer_role`, `staff_role`, `admin_role`) are created and granted specific permissions on tables and stored procedures.

- **`customer_role`**: Can `SELECT` from `products` and `currencies`, and `EXECUTE` procedures related to creating orders and viewing their own history.
- **`staff_role`**: Inherits all permissions from `customer_role` and can additionally `SELECT` from `orders`, `order_items`, and `users`, and `UPDATE` the status of orders.
- **`admin_role`**: Inherits all permissions from `staff_role` and has full `SELECT, INSERT, UPDATE, DELETE` rights on `products` and `users`, and access to administrative tables and procedures.

### 4.3. Application-Level RBAC

In `main.py`, Flask function decorators are used to protect routes and ensure that only users with the appropriate role can access certain pages.

- **`@login_required`**: Ensures a user is logged in before they can access a route.
- **`@staff_required`**: Restricts access to users with the `staff` or `admin` role.
- **`@admin_required`**: Restricts access to users with the `admin` role only.

These decorators check the `role` stored in the user's session upon login and redirect them with an error message if they do not have the required permissions. This dual-layer security model ensures that access control is enforced consistently throughout the application.
