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
            autocommit=False
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

# --- Role-Specific Decorators ---
def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') not in ['staff', 'admin']:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/menu')
def menu():
    try:
        with db_transaction() as (conn, cursor):
            cursor.execute("SELECT * FROM products")
            menu_items = cursor.fetchall()
            return render_template('menu.html', menu_items=menu_items)
    except Exception as e:
        print(f"Error loading menu: {e}")
        flash('Error loading menu items.', 'danger')
        return render_template('menu.html', menu_items=[])

# --- Register ---
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
@login_required
def add_to_cart():
    data = request.get_json()
    product_id = data.get('id')
    user_id = session['user_id']

    try:
        with db_transaction() as (conn, cursor):
            # Check if the item is already in the user's cart
            cursor.execute(
                "SELECT * FROM user_carts WHERE user_id = %s AND product_id = %s",
                (user_id, product_id)
            )
            cart_item = cursor.fetchone()

            if cart_item:
                # If it exists, increment the quantity
                cursor.execute(
                    "UPDATE user_carts SET quantity = quantity + 1 WHERE user_id = %s AND product_id = %s",
                    (user_id, product_id)
                )
            else:
                # If not, insert a new record
                cursor.execute(
                    "INSERT INTO user_carts (user_id, product_id, quantity) VALUES (%s, %s, 1)",
                    (user_id, product_id)
                )
            
            # Load the updated cart data
            cart_data = _load_cart_from_db(cursor, user_id)

        return jsonify({
            'success': True,
            'message': 'Item added to cart successfully!',
            'cart': cart_data,
            'cart_count': sum(item['quantity'] for item in cart_data.values()),
            'cart_total': sum(item['price'] * item['quantity'] for item in cart_data.values())
        })
    except Exception as e:
        print(f"Error adding to cart: {e}")
        return jsonify({'error': 'Failed to add item to cart.'}), 500

@app.route('/cart')
@login_required
def cart():
    user_id = session['user_id']
    try:
        with db_transaction() as (conn, cursor):
            cart_items = _load_cart_from_db(cursor, user_id)
            total = sum(item['price'] * item['quantity'] for item in cart_items.values())
            return render_template('cart.html', cart=cart_items, total=total)
    except Exception as e:
        print(f"Error loading cart: {e}")
        flash('Error loading your cart.', 'danger')
        return render_template('cart.html', cart={}, total=0)

@app.route('/update_cart', methods=['POST'])
@login_required
def update_cart():
    data = request.get_json()
    action = data.get('action')
    product_id = data.get('item_id')
    user_id = session['user_id']

    try:
        with db_transaction() as (conn, cursor):
            if action == 'increase':
                cursor.execute(
                    "UPDATE user_carts SET quantity = quantity + 1 WHERE user_id = %s AND product_id = %s",
                    (user_id, product_id)
                )
            elif action == 'decrease':
                cursor.execute(
                    "UPDATE user_carts SET quantity = GREATEST(1, quantity - 1) WHERE user_id = %s AND product_id = %s",
                    (user_id, product_id)
                )
            elif action == 'remove':
                cursor.execute(
                    "DELETE FROM user_carts WHERE user_id = %s AND product_id = %s",
                    (user_id, product_id)
                )
            
            cart_data = _load_cart_from_db(cursor, user_id)
            
            return jsonify({
                'success': True,
                'cart': cart_data,
                'cart_count': sum(item['quantity'] for item in cart_data.values()),
                'cart_total': sum(item['price'] * item['quantity'] for item in cart_data.values())
            })
    except Exception as e:
        print(f"Error updating cart: {e}")
        return jsonify({'success': False, 'error': 'Failed to update cart.'}), 500

@app.route('/save-cart-session', methods=['POST'])
def save_cart_session():
    session['cart'] = request.get_json().get('cart', [])
    session.modified = True
    return '', 204

# --- Login ---
def _load_cart_from_db(cursor, user_id):
    """Helper function to load cart from DB and store it in the session."""
    cursor.execute("""
        SELECT p.id, p.name, p.price, uc.quantity
        FROM user_carts uc
        JOIN products p ON uc.product_id = p.id
        WHERE uc.user_id = %s
    """, (user_id,))
    
    cart_items = cursor.fetchall()
    
    cart = {
        str(item['id']): {
            'id': item['id'],
            'name': item['name'],
            'price': float(item['price']),
            'quantity': item['quantity']
        } for item in cart_items
    }
    session['cart'] = cart
    session.modified = True
    return cart

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
                    
                    # Load user's cart from database into session
                    _load_cart_from_db(cursor, user['id'])

                    flash('Logged in successfully.', 'success')

                    if user['role'] == 'admin':
                        return redirect(url_for('admin'))
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
    user_id = session['user_id']
    try:
        with db_transaction() as (conn, cursor):
            # Fetch currencies
            cursor.execute("SELECT * FROM currencies")
            currencies = cursor.fetchall()
            
            # Fetch cart items from the database to ensure data is current
            cart_items = _load_cart_from_db(cursor, user_id)
            total = sum(item['price'] * item['quantity'] for item in cart_items.values())
            
            return render_template('checkout.html', currencies=currencies, cart=cart_items, total=total)
    except Exception as e:
        print(f"Error loading checkout: {e}")
        flash('Error loading checkout page.', 'danger')
        return redirect(url_for('cart'))

# --- Checkout ---
@app.route('/submit_checkout', methods=['POST'])
@login_required
def submit_checkout():
    name = request.form.get('name')
    address = request.form.get('address')
    payment_method = request.form.get('payment_method')
    cart_json = request.form.get('cart_data')
    
    try:
        cart_dict = json.loads(cart_json) if cart_json else {}
        cart = list(cart_dict.values()) # Convert dict to list of items
    except json.JSONDecodeError:
        flash("Invalid cart data.", "danger")
        return redirect(url_for('checkout'))

    if not name or not address or not payment_method or not cart:
        flash("Please complete the form and add items to your cart.", "danger")
        return redirect(url_for('checkout'))

    user_id = session['user_id']
    total = sum(item['price'] * item['quantity'] for item in cart)

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

            # Step 2: Create order and record transaction in one go
            cart_json_for_db = json.dumps(cart)
            cursor.callproc('create_order', (user_id, total, cart_json_for_db))

            # Fetch the last inserted ID from the orders table
            cursor.execute("SELECT LAST_INSERT_ID() as id")
            order_id_result = cursor.fetchone()
            order_id = order_id_result['id'] if order_id_result else None

            if not order_id:
                raise Exception("Failed to create order")

            # Step 3: Record transaction
            cursor.callproc('record_transaction', (order_id, total, payment_method, 'Success'))

            # Step 5: Clear user's cart from the database
            cursor.execute("DELETE FROM user_carts WHERE user_id = %s", (user_id,))

            # Step 6: Clear cart from session
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

# -- Admin --
@app.route('/admin')
@admin_required
def admin():
    editing_id = request.args.get('edit', type=int)
    try:
        with db_transaction() as (conn, cursor):
            # Fetch products
            cursor.execute(
                "SELECT id, name, price, stock_quantity, description, image, is_active "
                "FROM products ORDER BY id DESC"
            )
            products = cursor.fetchall()

            # Fetch users
            cursor.execute("SELECT id, name, email, role FROM users")
            users = cursor.fetchall()

            return render_template('admin.html', products=products, users=users, editing_id=editing_id)
            
    except Exception as e:
        print(f"Error loading admin panel: {e}")
        flash('Error loading admin panel.', 'danger')
        return render_template('admin.html', products=[], users=[], editing_id=editing_id)

@app.route('/add_product', methods=['POST'])
@admin_required
def add_product():
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
            cursor.callproc('add_product', (name, description, price, stock_qty, filename))
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

    return redirect(url_for('admin'))

@app.route('/edit_product/<int:product_id>', methods=['POST'])
@admin_required
def edit_product(product_id):
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

    return redirect(url_for('admin'))

@app.route('/delete_product/<int:product_id>')
@admin_required
def delete_product(product_id):
    try:
        with db_transaction() as (conn, cursor):
            # Check if product exists and has any order history
            cursor.execute("SELECT name FROM products WHERE id = %s", (product_id,))
            product = cursor.fetchone()
            
            if not product:
                flash('Product not found.', 'danger')
                return redirect(url_for('admin'))
            
            cursor.execute("SELECT COUNT(*) as order_count FROM order_items WHERE product_id = %s", (product_id,))
            order_check = cursor.fetchone()
            
            if order_check['order_count'] > 0:
                flash(f'Cannot delete {product["name"]} - it has order history. Consider deactivating instead.', 'warning')
                return redirect(url_for('admin'))
            
            cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
            flash(f'Product "{product["name"]}" deleted successfully!', 'success')

    except Exception as e:
        print(f"Error deleting product: {e}")
        flash("Error deleting product.", 'danger')

    return redirect(url_for('admin'))

# --- Staff Routes ---
@app.route('/staff')
@staff_required
def staff():
    try:
        with db_transaction() as (conn, cursor):
            # Fetch orders with associated products
            cursor.execute("""
                SELECT 
                    o.id, o.total, o.status, o.created_at, 
                    u.name as user_name, u.email as user_email,
                    p.name as product_name, oi.quantity, oi.price
                FROM orders o
                JOIN users u ON o.user_id = u.id
                LEFT JOIN order_items oi ON o.id = oi.order_id
                LEFT JOIN products p ON oi.product_id = p.id
                ORDER BY o.created_at DESC, o.id
            """)
            
            order_details = cursor.fetchall()
            
            orders_dict = {}
            for item in order_details:
                order_id = item['id']
                if order_id not in orders_dict:
                    orders_dict[order_id] = {
                        'id': order_id,
                        'total': item['total'],
                        'status': item['status'],
                        'created_at': item['created_at'],
                        'user_name': item['user_name'],
                        'user_email': item['user_email'],
                        'products': []
                    }
                
                if item['product_name']:
                    orders_dict[order_id]['products'].append({
                        'name': item['product_name'],
                        'quantity': item['quantity'],
                        'price': item['price']
                    })

            orders = list(orders_dict.values())

            # Fetch inventory
            cursor.execute("SELECT id, name, price, stock_quantity, description, image, is_active FROM products ORDER BY name")
            products = cursor.fetchall()

            return render_template('staff.html', orders=orders, products=products)
    except Exception as e:
        print(f"Error loading staff page: {e}")
        flash('Error loading staff page.', 'danger')
        return redirect(url_for('home'))

@app.route('/staff/order/<int:order_id>/update', methods=['POST'])
@staff_required
def update_order_status(order_id):
    new_status = request.form.get('status')
    if not new_status:
        flash('No status provided.', 'danger')
        return redirect(url_for('staff'))

    try:
        with db_transaction() as (conn, cursor):
            cursor.execute(
                "UPDATE orders SET status = %s WHERE id = %s",
                (new_status, order_id)
            )
            flash(f'Order #{order_id} status updated to {new_status}.', 'success')
    except Exception as e:
        print(f"Error updating order status: {e}")
        flash('Error updating order status.', 'danger')
    
    return redirect(url_for('staff'))

# --- Admin Routes ---
@app.route('/admin/user/<int:user_id>/role', methods=['POST'])
@admin_required
def update_user_role(user_id):
    new_role = request.form.get('role')
    if not new_role in ['customer', 'staff', 'admin']:
        flash('Invalid role specified.', 'danger')
        return redirect(url_for('admin'))
    
    try:
        with db_transaction() as (conn, cursor):
            cursor.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
            flash('User role updated successfully.', 'success')
    except Exception as e:
        print(f"Error updating user role: {e}")
        flash('Error updating user role.', 'danger')
        
    return redirect(url_for('admin'))

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    if user_id == session.get('user_id'):
        flash("You cannot delete your own account.", 'danger')
        return redirect(url_for('admin'))
        
    try:
        with db_transaction() as (conn, cursor):
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            flash('User deleted successfully.', 'success')
    except Exception as e:
        print(f"Error deleting user: {e}")
        flash('Error deleting user.', 'danger')
        
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
