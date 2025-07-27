# The Donut Hole - Web Application Documentation

## Project Overview

The Donut Hole is a full-stack web application for an online donut shop. It's built with Python's Flask framework on the backend, a MySQL database for data persistence, and standard HTML, CSS, and JavaScript on the frontend. The application provides features for customers to browse products, manage a shopping cart, and place orders. It also includes an admin panel for managing products and users, and a staff panel for order fulfillment.

## Core Technologies

*   **Backend:** Python, Flask
*   **Database:** MySQL
*   **Frontend:** HTML, CSS, JavaScript
*   **Environment Management:** python-dotenv
*   **Deployment:** (Not specified, but can be deployed on any server that supports Python/WSGI)

## Features

### Customer-Facing Features

*   **Home Page:** Landing page for the application.
*   **Menu Page:** Displays all available products (donuts).
*   **Product Details:** (Implicit) Users can see details of each product.
*   **Shopping Cart:**
    *   Add items to the cart.
    *   Increase/decrease item quantities.
    *   Remove items from the cart.
    *   Cart data is persisted in the database, linked to the user's account.
*   **User Authentication:**
    *   User registration with email and password.
    *   User login.
    *   Password hashing for security.
    *   Login required for certain pages (e.g., cart, checkout, order history).
*   **Checkout Process:**
    *   Multi-currency support (PHP, USD, EUR).
    *   Users can enter their shipping information.
    *   Select a payment method (Cash on Delivery, GCash).
    *   The system validates stock before confirming an order.
*   **Order History:** Registered users can view their past orders.

### Admin Features

*   **Admin Panel:** A dedicated section for administrators to manage the store.
*   **Product Management:**
    *   Add new products with name, price, stock, description, and image.
    *   Edit existing products.
    *   Deactivate or delete products.
    *   Products with order history cannot be deleted, preventing data integrity issues.
*   **User Management:**
    *   View all registered users.
    *   Update user roles (customer, staff, admin).
    *   Delete users.
*   **Role-Based Access Control:** Only users with the 'admin' role can access the admin panel.

### Staff Features

*   **Staff Panel:** A dedicated section for staff members to manage incoming orders.
*   **Order Management:**
    *   View all customer orders and their details.
    *   Update the status of orders (e.g., 'Processing', 'Shipped', 'Delivered').
*   **Inventory Overview:** View current stock levels of all products.
*   **Role-Based Access Control:** Accessible to users with 'staff' or 'admin' roles.

## Database Schema

The application uses a MySQL database named `donut_hole`. The schema consists of the following tables:

*   `users`: Stores user information, credentials, and roles (`customer`, `staff`, `admin`).
*   `products`: Contains details about the donuts, including price and stock levels.
*   `user_carts`: Persists shopping cart contents for each user.
*   `orders`: Header table for customer orders with status tracking.
*   `order_items`: Line items for each order, linking products to orders.
*   `currencies`: Stores currency information for the checkout process.
*   `transactions`: Records payment transactions for each order.
*   `product_updates`: An archive table that logs all changes made to products.
*   `phased_out_products`: An archive table for products that have been deleted.
*   `low_stock_products`: A log table that records when a product's stock falls below a certain threshold.

### Stored Procedures & Triggers

The database makes extensive use of stored procedures and triggers to enforce business logic and maintain data integrity:

*   **Stored Procedures:**
    *   `get_user_orders`: Retrieves all orders for a specific user.
    *   `add_product`: Adds a new product.
    *   `update_product_stock`: Decrements stock when an order is placed.
    *   `create_order`: Creates a new order.
    *   `add_order_item`: Adds an item to an order.
    *   `record_transaction`: Records a payment transaction.
*   **Triggers:**
    *   `product_update`: Archives product changes into the `product_updates` table.
    *   `deleted_products_archive`: Archives deleted products into the `phased_out_products` table.
    *   `prevent_negative_stock`: Prevents product stock from going below zero on update.
    *   `prevent_negative_new_product`: Ensures new products have a stock greater than 0 on insert.
    *   `low_stock_alerts`: Logs when product stock falls below a certain threshold into the `low_stock_products` table.
*   **Database Roles:** The database implements Role-Based Access Control (RBAC) with `customer_role`, `staff_role`, and `admin_role` to enforce security at the database level.

## Setup and Installation

1.  **Prerequisites:**
    *   Python 3.x
    *   MySQL Server

2.  **Clone the repository:**
    ```bash
    git clone https://github.com/riiapangilinan/TheDonutHole.git
    cd TheDonutHole
    ```

3.  **Set up the database:**
    *   Connect to your MySQL server.
    *   Execute the `donut_db.sql` script to create the database, tables, and seed initial data.
    ```bash
    mysql -u your_username -p < donut_db.sql
    ```

4.  **Create an Environment File:**
    *   Create a file named `.env` in the root of the project directory.
    *   Add the following environment variables to the `.env` file, replacing the placeholder values with your actual database credentials:
    ```
    DB_HOST=localhost
    DB_USER=your_db_user
    DB_PASSWORD=your_db_password
    DB_NAME=donut_hole
    ```

5.  **Install dependencies:**
    *   It is recommended to use a virtual environment.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```
    *   Install the required packages from `requirements.txt` (or install them manually):
    ```bash
    pip install Flask mysql-connector-python Werkzeug python-dotenv
    ```

6.  **Configure the application:**
    *   Open `main.py` and change the `app.secret_key` to a unique, secret string.

7.  **Run the application:**
    ```bash
    python main.py
    ```
    The application will be available at `http://127.0.0.1:5000`.

## Application Structure

*   `main.py`: The main Flask application file containing all routes and business logic.
*   `templates/`: Directory for HTML templates.
    *   `base.html`: Base template that other templates extend.
    *   Other HTML files for different pages (e.g., `index.html`, `menu.html`, `login.html`, etc.).
*   `assets/`: Directory for static files.
    *   `css/`: Stylesheets.
    *   `js/`: JavaScript files.
    *   `images/`: Images used in the application.
*   `donut_db.sql`: The database schema and initial data.
*   `requirements.txt`: Lists Python dependencies.
*   `.env`: (Locally created) Stores environment variables for database configuration.

## How to Use

1.  **Register as a new user** or log in with the default admin credentials:
    *   **Email:** `admin@donuthole.com`
    *   **Password:** `admin` (Note: The password hash is provided in the SQL file, the actual password is not stored)
2.  **As a customer:**
    *   Browse the menu.
    *   Add items to your cart.
    *   Go to the cart page to review your items.
    *   Proceed to checkout, fill in your details, and place the order.
    *   View your order history.
3.  **As an admin:**
    *   Log in with the admin account. You will be redirected to the admin panel.
    *   Manage products (add, edit, delete).
    *   Manage users (update roles, delete).
4.  **As a staff member:**
    *   Log in with a staff account. You will be redirected to the staff panel.
    *   View all customer orders.
    *   Update order statuses to reflect the fulfillment process.
