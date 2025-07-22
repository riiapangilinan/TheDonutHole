from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error
from werkzeug.utils import secure_filename
import os

app = Flask(__name__, static_folder='assets', static_url_path='/assets')
app.secret_key = 'your_secret_key_here'

# Configure upload folder for product images
UPLOAD_FOLDER = os.path.join(app.static_folder, 'images')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='admin',
            password='DLSU1234',  # change to your pw
            database='donut_hole'
        )
        return connection
    except Error as e:
        print("MySQL connection error:", e)
        return None

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
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE is_active = TRUE")
    menu_items = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('menu.html', menu_items=menu_items)

# --- Register ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('Email already registered.', 'danger')
        else:
            cursor.execute("INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                           (name, email, password))
            conn.commit()
            flash('Registered successfully. Please login.', 'success')
            return redirect(url_for('login'))

        cursor.close()
        conn.close()

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
            'id': int(product_id),  # Needed for order_items insert
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
    item_id = str(data.get('item_id'))  # Keep as string to match session keys

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

# --- Login ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['email'] = user['email']
            session['name'] = user['name']
            session['role'] = user['role']  # Store role in session

            flash('Logged in successfully.', 'success')

            # Role-based redirect
            if user['role'] == 'admin':
                return redirect(url_for('admin_panel'))
            else:
                return redirect(url_for('home'))
        else:
            flash('Invalid email or password.', 'danger')

        cursor.close()
        conn.close()

    return render_template('login.html')


# --- Logout ---
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
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            o.id AS order_id,
            o.created_at,
            o.status,
            o.total,
            t.payment_method,
            t.status AS transaction_status
        FROM orders o
        LEFT JOIN transactions t ON o.id = t.order_id
        WHERE o.user_id = %s
        ORDER BY o.created_at DESC
    """, (user_id,))
    
    orders = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('order_history.html', orders=orders)

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/checkout')
@login_required
def checkout():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM currencies")
    currencies = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('checkout.html', currencies=currencies)


@app.route('/submit_checkout', methods=['POST'])
@login_required
def submit_checkout():
    import json

    name = request.form.get('name')
    address = request.form.get('address')
    payment_method = request.form.get('payment_method')
    cart_json = request.form.get('cart_data')
    cart = json.loads(cart_json) if cart_json else {}

    if not name or not address or not payment_method or not cart:
        flash("Please complete the form and add items to your cart.", "danger")
        return redirect(url_for('checkout'))

    user_id = session['user_id']
    total = sum(item['price'] * item['quantity'] for item in cart)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Create order and get order_id
        args = (user_id, 'Paid', total, 0)
        result_args = cursor.callproc('create_order', args)
        order_id = result_args[3]

        # Add order items and update stock
        for item in cart:
            cursor.callproc('add_order_item', (order_id, item['id'], item['quantity'], item['price']))
            cursor.callproc('update_product_stock', (item['id'], item['quantity']))

        # Record transaction
        cursor.callproc('record_transaction', (order_id, total, payment_method, 'Success'))

        conn.commit()
        flash("Order placed successfully!", "success")

    except Exception as e:
        conn.rollback()
        print("Checkout error:", e)
        flash("Error placing order.", "danger")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('order_history'))

# -- Admin Side --
@app.route('/admin_panel')
@login_required
def admin_panel():
    if session.get('role') != 'admin':
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('home'))

    editing_id = request.args.get('edit', type=int)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, name, price, stock_quantity, description, image, is_active"
        " FROM products ORDER BY id DESC"
    )
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_products.html', products=products, editing_id=editing_id)

@app.route('/add_product', methods=['POST'])
@login_required
def add_product():
    if session.get('role') != 'admin':
        flash('Unauthorized', 'danger')
        return redirect(url_for('admin_panel'))

    # Retrieve form data
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
        # Insert into DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (name, price, stock_quantity, description, image, is_active) "
            "VALUES (%s, %s, %s, %s, %s, TRUE)",
            (name, price, stock_qty, description, filename)
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash('Product added successfully!', 'success')

    except mysql.connector.Error as err:
        # Handle database errors
        flash(f"Error: {err}", 'danger')
        return redirect(url_for('admin_panel'))

    return redirect(url_for('admin_panel'))

@app.route('/edit_product/<int:product_id>', methods=['POST'])
@login_required
def edit_product(product_id):
    if session.get('role') != 'admin':
        flash('Unauthorized', 'danger')
        return redirect(url_for('admin_panel'))

    # Retrieve form data
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

    # Update DB
    conn = get_db_connection()
    cursor = conn.cursor()
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
    conn.commit()
    cursor.close()
    conn.close()

    flash('Product updated successfully!', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/delete_product/<int:product_id>')
@login_required
def delete_product(product_id):
    if session.get('role') != 'admin':
        flash('Unauthorized', 'danger')
        return redirect(url_for('admin_panel'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id=%s", (product_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Product deleted successfully!', 'success')
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(debug=True)
