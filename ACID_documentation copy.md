# ACID Properties in The Donut Hole Project

This document provides an in-depth discussion of how the Donut Hole project adheres to the ACID (Atomicity, Consistency, Isolation, Durability) principles to ensure data integrity and reliable transaction processing.

## Atomicity

Atomicity ensures that all operations within a transaction are completed as a single, indivisible unit. Either all operations succeed, or none of them do. If any part of the transaction fails, the entire transaction is rolled back, and the database is left unchanged.

### Implementation in `main.py`

The primary mechanism for ensuring atomicity is the `db_transaction` context manager in `main.py`. This context manager wraps a series of database operations in a single transaction.

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

**Line-by-Line Explanation:**
- **`@contextmanager`**: A Python decorator that allows this function to be used in a `with` statement, which simplifies resource management (like database connections).
- **`def db_transaction():`**: Defines the function that manages the database transaction.
- **`conn = get_db_connection()`**: Establishes a connection to the MySQL database.
- **`if not conn:`**: Checks if the connection failed and raises an error to stop execution if it cannot connect.
- **`try:`**: Starts a block of code where errors will be caught and handled.
- **`cursor = conn.cursor(dictionary=True)`**: Creates a cursor object to execute SQL queries. `dictionary=True` ensures that results are returned as easy-to-use Python dictionaries.
- **`yield conn, cursor`**: This is the core of the context manager. It temporarily passes the connection and cursor objects to the code inside the `with` block. The function pauses here while the operations in the `with` block are executed.
- **`conn.commit()`**: If the code inside the `with` block runs without any errors, this line is executed to save all changes to the database permanently.
- **`except Exception as e:`**: If any error occurs within the `with` block, the program jumps to this section.
- **`conn.rollback()`**: This command undoes all the changes made during the transaction, ensuring the database is returned to its original state. This is the key to enforcing atomicity.
- **`finally:`**: This block of code will run regardless of whether an error occurred or not.
- **`cursor.close()` and `conn.close()`**: These lines clean up by closing the cursor and connection, freeing up database resources.

This context manager is used in critical operations like order placement in the `submit_checkout` function.

```python
@app.route('/submit_checkout', methods=['POST'])
@login_required
def submit_checkout():
    # ... (form data retrieval) ...
    try:
        with db_transaction() as (conn, cursor):
            # 1. Validate stock
            # 2. Create order
            # 3. Record transaction
            # 4. Clear user's cart
            # ... (all operations) ...
    except Exception as e:
        # ... (error handling) ...
```

If any of the steps within the `with db_transaction()` block fails (e.g., insufficient stock), the `conn.rollback()` in the context manager's `except` block is executed, undoing all previous operations within that transaction.

## Consistency

Consistency ensures that a transaction brings the database from one valid state to another. This is maintained through a combination of application logic and database constraints.

### Implementation in `donut_db.sql`

The database schema uses several constraints and triggers to enforce consistency.

**1. Preventing Negative Stock:**
The `prevent_negative_stock` trigger in `donut_db.sql` prevents the `stock_quantity` of a product from dropping below zero.

```sql
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
```

**Line-by-Line Explanation:**
- **`CREATE TRIGGER prevent_negative_stock`**: Creates a new trigger in the database named `prevent_negative_stock`.
- **`BEFORE UPDATE ON products`**: Specifies that this trigger should run automatically just before any row in the `products` table is updated.
- **`FOR EACH ROW`**: Indicates that the trigger logic should be applied to each individual row that is being modified.
- **`IF NEW.stock_quantity < 0 THEN`**: This is the condition that checks if the proposed new value for `stock_quantity` is less than zero. `NEW` refers to the incoming updated row data.
- **`SIGNAL SQLSTATE '45000'`**: If the condition is true, this command raises a generic SQL error, which stops the `UPDATE` operation from completing.
- **`SET MESSAGE_TEXT = ...`**: This assigns a custom, user-friendly error message to the error signal, making it clear why the operation failed.

**2. Returning Stock on Order Cancellation:**
The `return_stock_on_cancellation` trigger ensures that if an order is canceled, the stock for the items in that order is returned to the inventory.

```sql
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
```

**Line-by-Line Explanation:**
- **`CREATE TRIGGER return_stock_on_cancellation`**: Creates a trigger named `return_stock_on_cancellation`.
- **`AFTER UPDATE ON orders`**: This trigger runs automatically after a row in the `orders` table has been updated.
- **`IF NEW.status = 'Cancelled' AND OLD.status != 'Cancelled' THEN`**: This condition checks if the order's status has just been changed to 'Cancelled'. `NEW` refers to the state of the row after the update, and `OLD` refers to the state before the update. This ensures the stock is only returned once.
- **`UPDATE products p ...`**: This command updates the `products` table.
- **`JOIN order_items oi ON p.id = oi.product_id`**: It joins the `products` table with `order_items` to find out which products and quantities were in the cancelled order.
- **`SET p.stock_quantity = p.stock_quantity + oi.quantity`**: This line adds the quantity of the items from the cancelled order back to the product's stock.
- **`WHERE oi.order_id = NEW.id`**: This ensures that only the products associated with the just-cancelled order are updated.

### Implementation in `main.py`

The application code also performs checks to ensure consistency before committing a transaction. In `submit_checkout`, the application validates stock availability before attempting to create an order.

```python
# Step 1: Validate stock availability for all items before proceeding
for item in cart:
    cursor.execute(
        "SELECT stock_quantity FROM products WHERE id = %s AND is_active = TRUE",
        (item['id'],)
    )
    product = cursor.fetchone()
    
    if not product:
        raise Exception(f"Product {item['name']} is no longer available")
    
    if product['stock_quantity'] < item['quantity']:
        raise Exception(f"Insufficient stock for {item['name']}. Available: {product['stock_quantity']}, Requested: {item['quantity']}")
```

**Line-by-Line Explanation:**
- **`for item in cart:`**: This loop iterates through each item currently in the user's shopping cart.
- **`cursor.execute(...)`**: This executes an SQL query to fetch the current `stock_quantity` for the product ID of the cart item. It also checks if the product `is_active` to ensure it's available for purchase.
- **`product = cursor.fetchone()`**: This retrieves the result of the query.
- **`if not product:`**: This checks if the query returned any result. If not, it means the product either doesn't exist or has been deactivated, so an exception is raised.
- **`if product['stock_quantity'] < item['quantity']:`**: This is the critical consistency check. It compares the available stock with the quantity the user wants to buy.
- **`raise Exception(...)`**: If there is not enough stock, an exception is raised with a detailed error message. This exception will be caught by the `db_transaction` context manager, triggering a `rollback` and preventing the order from being placed.

## Isolation

Isolation ensures that concurrent transactions do not interfere with each other. The database manages this through locking mechanisms. While the specific isolation level (e.g., `READ COMMITTED`, `REPEATABLE READ`) is determined by the MySQL server's configuration, the application's transaction management allows the database to enforce this isolation.

The use of transactions in `main.py` via the `db_transaction` context manager ensures that the operations within one transaction are isolated from others. For example, if two users try to buy the last remaining donut at the same time, the database's locking mechanism, working with the transactions, will prevent a race condition where both orders are processed. One transaction will acquire a lock on the product's row, update the stock, and commit. The second transaction will then see the updated (zero) stock and fail, preventing the stock from going negative.

## Durability

Durability guarantees that once a transaction has been committed, it will remain so, even in the event of a power loss, crash, or other system failure.

### Implementation

This is primarily handled by the MySQL database system itself. When the `conn.commit()` call in the `db_transaction` context manager is successful, MySQL ensures that the changes are written to its transaction logs and then to the database files on disk. This ensures that the data is durable and will survive system restarts. The application relies on the database's durability guarantees.

By using `autocommit=False` in the database connection and explicitly calling `conn.commit()`, the application ensures that it uses the database's built-in mechanisms for durability.

```python
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            # ... (connection details) ...
            autocommit=False
        )
        return connection
    # ... (error handling) ...
```

**Line-by-Line Explanation:**
- **`autocommit=False`**: This is the most important setting for enabling transaction control. It tells the database connection not to automatically save every single SQL statement as a separate transaction. Instead, changes are held in a pending state until the application explicitly calls `conn.commit()`. This allows the application to group multiple database operations into a single, atomic transaction.

This configuration is crucial for ensuring that transactions are managed correctly and that durability is maintained.
