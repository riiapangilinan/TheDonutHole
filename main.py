from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error
from werkzeug.utils import secure_filename
import os
import json
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='assets', static_url_path='/assets')
app.secret_key = 'your_secret_key_here'

# Configure upload folder for product images
UPLOAD_FOLDER = os.path.join(app.static_folder, 'images')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            autocommit=False  # Important: Disable autocommit for transaction control
        )
        return connection
    except Error as e:
        print("MySQL connection error:", e)
        return None

# Context manager for database transactions
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

# --- Login Required Decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/menu')
def menu():
    try:
        with db_transaction() as (conn, cursor):
            cursor.execute("SELECT * FROM products WHERE is_active = TRUE")
            menu_items = cursor.fetchall()
            return render_template('menu.html', menu_items=menu_items)
    except Exception as e:
        print(f"Error loading menu: {e}")
        flash('Error loading menu items.', 'danger')
        return render_template('menu.html', menu_items=[])

# --- Enhanced Register with Transaction ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        try:
            with db_transaction() as (conn, cursor):
                # Check if email already exists
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                existing_user = cursor.fetchone()

                if existing_user:
                    flash('Email already registered.', 'danger')
                    return render_template('register.html')
                
                # Insert new user
                cursor.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                    (name, email, password)
                )
                flash('Registered successfully. Please login.', 'success')
                return redirect(url_for('login'))
                
        except Exception as e:
            print(f"Registration error: {e}")
            flash('Registration failed. Please try again.', 'danger')

    return render_template('register.html')

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    data = request.get_json()
    product_id = str(data.get('id'))
    name = data.get('name')
    price = float(data.get('price'))

    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']

    if product_id in cart:
        cart[product_id]['quantity'] += 1
    else:
        cart[product_id] = {
            'id': int(product_id),
            'name': name,
            'price': price,
            'quantity': 1
        }

    session['cart'] = cart
    session.modified = True
    return jsonify({'message': f"Added {name} to cart!"})

@app.route('/cart')
@login_required
def cart():
    cart_items = session.get('cart', {})
    total = sum(item['price'] * item['quantity'] for item in cart_items.values())
    return render_template('cart.html', cart=cart_items, total=total)

@app.route('/update_cart', methods=['POST'])
@login_required
def update_cart():
    data = request.get_json()
    action = data.get('action')
    item_id = str(data.get('item_id'))

    cart = session.get('cart', {})

    if item_id in cart:
        if action == 'increase':
            cart[item_id]['quantity'] += 1
        elif action == 'decrease':
            cart[item_id]['quantity'] = max(1, cart[item_id]['quantity'] - 1)
        elif action == 'remove':
            del cart[item_id]

    session['cart'] = cart
    session.modified = True

    return jsonify({
        'success': True,
        'cart': cart,
        'cart_count': sum(item['quantity'] for item in cart.values()),
        'cart_total': sum(item['price'] * item['quantity'] for item in cart.values())
    })

@app.route('/save-cart-session', methods=['POST'])
def save_cart_session():
    session['cart'] = request.get_json().get('cart', [])
    session.modified = True
    return '', 204

# --- Enhanced Login with Transaction ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            with db_transaction() as (conn, cursor):
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                user = cursor.fetchone()

                if user and check_password_hash(user['password_hash'], password):
                    session['user_id'] = user['id']
                    session['email'] = user['email']
                    session['name'] = user['name']
                    session['role'] = user['role']

                    flash('Logged in successfully.', 'success')

                    if user['role'] == 'admin':
                        return redirect(url_for('admin_panel'))
                    else:
                        return redirect(url_for('home'))
                else:
                    flash('Invalid email or password.', 'danger')
                    
        except Exception as e:
            print(f"Login error: {e}")
            flash('Login failed. Please try again.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/order_history')
@login_required
def order_history():
    user_id = session['user_id']
    
    try:
        with db_transaction() as (conn, cursor):
            cursor.callproc('get_user_orders', (user_id,))
            # Stored procedures return iterators. We need to fetch results from the correct one.
            for result in cursor.stored_results():
                orders = result.fetchall()
            return render_template('order_history.html', orders=orders)
            
    except Exception as e:
        print(f"Error loading order history: {e}")
        flash('Error loading order history.', 'danger')
        return render_template('order_history.html', orders=[])

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/checkout')
@login_required
def checkout():
    try:
        with db_transaction() as (conn, cursor):
            cursor.execute("SELECT * FROM currencies")
            currencies = cursor.fetchall()
            return render_template('checkout.html', currencies=currencies)
    except Exception as e:
        print(f"Error loading checkout: {e}")
        flash('Error loading checkout page.', 'danger')
        return redirect(url_for('cart'))

# --- Enhanced Checkout with Comprehensive Transaction Management ---
@app.route('/submit_checkout', methods=['POST'])
@login_required
def submit_checkout():
    name = request.form.get('name')
    address = request.form.get('address')
    payment_method = request.form.get('payment_method')
    cart_json = request.form.get('cart_data')
    
    try:
        cart = json.loads(cart_json) if cart_json else {}
    except json.JSONDecodeError:
        flash("Invalid cart data.", "danger")
        return redirect(url_for('checkout'))

    if not name or not address or not payment_method or not cart:
        flash("Please complete the form and add items to your cart.", "danger")
        return redirect(url_for('checkout'))

    user_id = session['user_id']
    total = sum(item['price'] * item['quantity'] for item in cart)
    cart_items_json = json.dumps(cart)

    try:
        with db_transaction() as (conn, cursor):
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

            # Step 2: Create order using stored procedure
            # The new create_order procedure handles the transaction
            cursor.callproc('create_order', (user_id, total, None))
            
            # Fetch the last inserted ID
            cursor.execute("SELECT LAST_INSERT_ID() as id")
            order_id_result = cursor.fetchone()
            order_id = order_id_result['id'] if order_id_result else None

            if not order_id:
                raise Exception("Failed to create order")

            # Step 3: Add order items and update stock (can be moved into create_order)
            for item in cart:
                # Add order item
                cursor.callproc('add_order_item', (order_id, item['id'], item['quantity'], item['price']))
                
                # Update product stock
                cursor.callproc('update_product_stock', (item['id'], item['quantity']))

            # Step 4: Record transaction
            cursor.callproc('record_transaction', (order_id, total, payment_method, 'Success'))

            # Step 5: Clear cart from session
            session.pop('cart', None)
            session.modified = True

            flash("Order placed successfully! Your order number is " + str(order_id), "success")
            return redirect(url_for('order_history'))

    except mysql.connector.Error as db_error:
        print(f"Database error during checkout: {db_error}")
        # Check for the custom error message from the trigger
        if "Stock is lesser than indicated quantity" in str(db_error.msg):
            flash("Some items in your cart are out of stock. Please update your cart.", "danger")
        else:
            flash("Database error occurred while processing your order.", "danger")
        return redirect(url_for('checkout'))
        
    except Exception as e:
        print(f"Checkout error: {e}")
        flash(f"Error placing order: {str(e)}", "danger")
        return redirect(url_for('checkout'))

# -- Enhanced Admin Side with Transactions --
@app.route('/admin_panel')
@login_required
def admin_panel():
    if session.get('role') != 'admin':
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('home'))

    editing_id = request.args.get('edit', type=int)
    
    try:
        with db_transaction() as (conn, cursor):
            cursor.execute(
                "SELECT id, name, price, stock_quantity, description, image, is_active "
                "FROM products ORDER BY id DESC"
            )
            products = cursor.fetchall()
            return render_template('admin_products.html', products=products, editing_id=editing_id)
            
    except Exception as e:
        print(f"Error loading admin panel: {e}")
        flash('Error loading products.', 'danger')
        return render_template('admin_products.html', products=[], editing_id=editing_id)

@app.route('/add_product', methods=['POST'])
@login_required
def add_product():
    if session.get('role') != 'admin':
        flash('Unauthorized', 'danger')
        return redirect(url_for('admin_panel'))

    name = request.form.get('name')
    price = request.form.get('price')
    stock_qty = request.form.get('stock_quantity', type=int) or 0
    description = request.form.get('description')

    # Handle file upload
    image_file = request.files.get('image')
    filename = None
    if image_file and image_file.filename:
        filename = secure_filename(image_file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(save_path)

    try:
        with db_transaction() as (conn, cursor):
            cursor.execute(
                "INSERT INTO products (name, price, stock_quantity, description, image, is_active) "
                "VALUES (%s, %s, %s, %s, %s, TRUE)",
                (name, price, stock_qty, description, filename)
            )
            flash('Product added successfully!', 'success')

    except mysql.connector.Error as err:
        print(f"Database error adding product: {err}")
        if "Indicated Stock is lesser than 0" in str(err):
            flash("Product stock must be greater than 0.", 'danger')
        else:
            flash(f"Database error: {err}", 'danger')
    except Exception as e:
        print(f"Error adding product: {e}")
        flash("Error adding product.", 'danger')

    return redirect(url_for('admin_panel'))

@app.route('/edit_product/<int:product_id>', methods=['POST'])
@login_required
def edit_product(product_id):
    if session.get('role') != 'admin':
        flash('Unauthorized', 'danger')
        return redirect(url_for('admin_panel'))

    name = request.form.get('name')
    price = request.form.get('price')
    stock_qty = request.form.get('stock_quantity', type=int)
    description = request.form.get('description')
    is_active = 1 if request.form.get('is_active') == 'on' else 0

    # Handle optional file upload
    image_file = request.files.get('image')
    filename = None
    if image_file and image_file.filename:
        filename = secure_filename(image_file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(save_path)

    try:
        with db_transaction() as (conn, cursor):
            if filename:
                cursor.execute(
                    "UPDATE products SET name=%s, price=%s, stock_quantity=%s, description=%s, image=%s, is_active=%s WHERE id=%s",
                    (name, price, stock_qty, description, filename, is_active, product_id)
                )
            else:
                cursor.execute(
                    "UPDATE products SET name=%s, price=%s, stock_quantity=%s, description=%s, is_active=%s WHERE id=%s",
                    (name, price, stock_qty, description, is_active, product_id)
                )
            flash('Product updated successfully!', 'success')

    except mysql.connector.Error as err:
        print(f"Database error updating product: {err}")
        if "Stock is lesser than indicated quantity" in str(err):
            flash("Cannot set stock to negative value.", 'danger')
        else:
            flash(f"Database error: {err}", 'danger')
    except Exception as e:
        print(f"Error updating product: {e}")
        flash("Error updating product.", 'danger')

    return redirect(url_for('admin_panel'))

@app.route('/delete_product/<int:product_id>')
@login_required
def delete_product(product_id):
    if session.get('role') != 'admin':
        flash('Unauthorized', 'danger')
        return redirect(url_for('admin_panel'))

    try:
        with db_transaction() as (conn, cursor):
            # Check if product exists and has any order history
            cursor.execute("SELECT name FROM products WHERE id = %s", (product_id,))
            product = cursor.fetchone()
            
            if not product:
                flash('Product not found.', 'danger')
                return redirect(url_for('admin_panel'))
            
            cursor.execute("SELECT COUNT(*) as order_count FROM order_items WHERE product_id = %s", (product_id,))
            order_check = cursor.fetchone()
            
            if order_check['order_count'] > 0:
                flash(f'Cannot delete {product["name"]} - it has order history. Consider deactivating instead.', 'warning')
                return redirect(url_for('admin_panel'))
            
            cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
            flash(f'Product "{product["name"]}" deleted successfully!', 'success')

    except Exception as e:
        print(f"Error deleting product: {e}")
        flash("Error deleting product.", 'danger')

    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(debug=True)
