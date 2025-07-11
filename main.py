# main.py
from flask import Flask, render_template, redirect, url_for, request, session, flash
from functools import wraps

app = Flask(__name__, static_folder='assets', static_url_path='/assets')
app.secret_key = 'your_secret_key_here'  # Change this to a real secret key in production

# Mock user database (replace with real database in production)
users = {
    'admin@thedonuthole.com': {'password': '123', 'name': 'Admin'},
    'staff@thedonuthole.com': {'password': '123', 'name': 'Staff'},
    'riia@gmail.com': {'password': '123', 'name': 'Riia'}
}

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