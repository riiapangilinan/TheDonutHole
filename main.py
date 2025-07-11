from flask import Flask, render_template, redirect, url_for, request, session, flash
from functools import wraps

from flask import jsonify
import json

app = Flask(__name__, static_folder='assets', static_url_path='/assets')
app.secret_key = 'your_secret_key_here' 

users = {
    'admin@thedonuthole.com': {'password': '123', 'name': 'Admin'},
    'staff@thedonuthole.com': {'password': '123', 'name': 'Staff'},
    'riia@gmail.com': {'password': '123', 'name': 'Riia'}
}

menu_items = [
    {
        'id': 1,
        'name': 'Original Glazed',
        'price': 35.00,
        'image': 'menu-1.png',
        'description': 'A timeless classic with a golden, melt-in-your-mouth glaze that’s perfectly sweet, fluffy.'
    },
    {
        'id': 2,
        'name': 'Hazelnut Drizzle',
        'price': 70.00,
        'image': 'menu-2.png',
        'description': 'Rich, roasted hazelnut glaze cascading over a delicate donut.'
    },
    {
        'id': 3,
        'name': 'Creme Brulee',
        'price': 80.00,
        'image': 'menu-3.png',
        'description': 'Luscious, custard-filled delight topped with a caramelized sugar that cracks perfectly with every bite.'
    },
    {
        'id': 4,
        'name': 'Orange Pistachio',
        'price': 80.00,
        'image': 'menu-4.png',
        'description': 'Zesty orange-infused glaze, topped with crunchy crushed pistachios.'
    },
    {
        'id': 5,
        'name': 'Fruit Punch Summer',
        'price': 70.00,
        'image': 'menu-5.png',
        'description': 'A sun-kissed celebration of juicy strawberries, blueberries, and raspberries for the summer.'
    },
    {
        'id': 6,
        'name': 'Bundles',
        'price': 150.00,
        'image': 'menu-6.png',
        'description': 'Build-your-own boxes—perfect for gifting, parties, or treating yourself to a sweet sampler.'
    }
]

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    if 'cart' not in session:
        session['cart'] = []
    
    data = request.get_json()
    item_id = data.get('item_id')
    
    # Find the item in the menu
    item = next((item for item in menu_items if item['id'] == item_id), None)
    
    if item:
        # Check if item already in cart
        cart_item = next((i for i in session['cart'] if i['id'] == item_id), None)
        
        if cart_item:
            cart_item['quantity'] += 1
        else:
            session['cart'].append({
                'id': item['id'],
                'name': item['name'],
                'price': item['price'],
                'quantity': 1
            })
        
        session.modified = True
        return jsonify({
            'success': True,
            'cart_count': sum(item['quantity'] for item in session['cart'])
        })
    
    return jsonify({'success': False}), 400

@app.route('/get_cart', methods=['GET'])
@login_required
def get_cart():
    return jsonify(session.get('cart', []))

@app.route('/update_cart', methods=['POST'])
@login_required
def update_cart():
    data = request.get_json()
    action = data.get('action')
    item_id = data.get('item_id')
    
    if action == 'increase':
        for item in session['cart']:
            if item['id'] == item_id:
                item['quantity'] += 1
                break
    elif action == 'decrease':
        for item in session['cart']:
            if item['id'] == item_id:
                if item['quantity'] > 1:
                    item['quantity'] -= 1
                else:
                    session['cart'] = [i for i in session['cart'] if i['id'] != item_id]
                break
    elif action == 'remove':
        session['cart'] = [i for i in session['cart'] if i['id'] != item_id]
    
    session.modified = True
    return jsonify({
        'success': True,
        'cart': session['cart'],
        'cart_count': sum(item['quantity'] for item in session['cart']),
        'cart_total': sum(item['price'] * item['quantity'] for item in session['cart'])
    })

# Update the menu route to use the same menu_items as in the home page
@app.route('/menu')
def menu():
    return render_template('menu.html', menu_items=menu_items)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email in users and users[email]['password'] == password:
            session['email'] = email
            session['name'] = users[email]['name']
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html', auth_page=True)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if email in users:
            flash('Email already registered', 'danger')
        elif password != confirm_password:
            flash('Passwords do not match', 'danger')
        else:
            users[email] = {'password': password, 'name': name}
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html', auth_page=True)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)