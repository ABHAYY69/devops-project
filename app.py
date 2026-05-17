from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'campusbazaar-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///campusbazaar.db'
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    college = db.Column(db.String(100), nullable=False)
    items = db.relationship('Item', backref='seller', lazy=True)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(200), default='default.jpg')
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    sold = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Routes
@app.route('/')
def home():
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    query = Item.query.filter_by(sold=False)
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Item.title.ilike(f'%{search}%'))
    items = query.order_by(Item.date_posted.desc()).all()
    return render_template('index.html', items=items, category=category, search=search)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        college = request.form['college']
        if User.query.filter_by(email=email).first():
            flash('Email already exists!', 'danger')
            return redirect(url_for('register'))
        user = User(name=name, email=email, password=password, college=college)
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            flash('Welcome back!', 'success')
            return redirect(url_for('home'))
        flash('Invalid credentials!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/post', methods=['GET', 'POST'])
def post_item():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        price = float(request.form['price'])
        category = request.form['category']
        image_file = 'default.jpg'
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                image_file = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_file))
        item = Item(title=title, description=description, price=price,
                   category=category, image=image_file, user_id=session['user_id'])
        db.session.add(item)
        db.session.commit()
        flash('Item posted successfully!', 'success')
        return redirect(url_for('home'))
    return render_template('post_item.html')

@app.route('/item/<int:item_id>')
def item_detail(item_id):
    item = Item.query.get_or_404(item_id)
    return render_template('item_detail.html', item=item)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    items = Item.query.filter_by(user_id=session['user_id']).all()
    return render_template('dashboard.html', user=user, items=items)

@app.route('/mark_sold/<int:item_id>')
def mark_sold(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    item = Item.query.get_or_404(item_id)
    item.sold = True
    db.session.commit()
    flash('Item marked as sold!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/health')
def health():
    return {"status": "healthy"}, 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)