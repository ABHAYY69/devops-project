from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO, emit, join_room
from datetime import datetime
import os
import boto3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'campusbazaar-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://dbadmin:CampusBazaar123!@campusbazaar-db.c7a4u6ccqv2r.ap-south-1.rds.amazonaws.com:5432/campusbazaar'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
AWS_BUCKET = 'campusbazaar-images-756269935915'
AWS_REGION = 'ap-south-1'
AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
socketio = SocketIO(app, cors_allowed_origins='*')

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

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])
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
                s3 = boto3.client('s3', region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
                s3.upload_fileobj(file, AWS_BUCKET, image_file, ExtraArgs={'ContentType': file.content_type})
        item = Item(title=title, description=description, price=price,
                   category=category, image=image_file, user_id=session['user_id'])
        db.session.add(item)
        db.session.commit()
        flash('Item posted successfully!', 'success')
        return redirect(url_for('home'))
    return render_template('post_item.html')

@app.route('/mark_sold/<int:item_id>')
def mark_sold(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    item = Item.query.get_or_404(item_id)
    item.sold = True
    db.session.commit()
    flash('Item marked as sold!', 'success')
    return redirect(url_for('dashboard'))
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

@app.route('/inbox')
def inbox():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    # Get all unique conversations
    sent = db.session.query(Message.receiver_id).filter_by(sender_id=user_id).distinct()
    received = db.session.query(Message.sender_id).filter_by(receiver_id=user_id).distinct()
    contact_ids = set([r[0] for r in sent] + [r[0] for r in received])
    contacts = User.query.filter(User.id.in_(contact_ids)).all()
    # Count unread
    unread_count = Message.query.filter_by(receiver_id=user_id, read=False).count()
    return render_template('inbox.html', contacts=contacts, unread_count=unread_count)

@app.route('/chat/<int:user_id>')
def chat(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    other_user = User.query.get_or_404(user_id)
    my_id = session['user_id']
    messages = Message.query.filter(
        ((Message.sender_id == my_id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == my_id))
    ).order_by(Message.timestamp.asc()).all()
    # Mark as read
    Message.query.filter_by(sender_id=user_id, receiver_id=my_id, read=False).update({'read': True})
    db.session.commit()
    return render_template('chat.html', other_user=other_user, messages=messages, my_id=my_id)

@app.route('/chat/start/<int:item_id>')
def start_chat(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    item = Item.query.get_or_404(item_id)
    return redirect(url_for('chat', user_id=item.user_id))

@socketio.on('send_message')
def handle_message(data):
    sender_id = session.get('user_id')
    receiver_id = data['receiver_id']
    content = data['content']
    msg = Message(sender_id=sender_id, receiver_id=receiver_id, content=content)
    db.session.add(msg)
    db.session.commit()
    room = f"chat_{min(sender_id, receiver_id)}_{max(sender_id, receiver_id)}"
    emit('receive_message', {
        'sender_id': sender_id,
        'content': content,
        'timestamp': msg.timestamp.strftime('%H:%M')
    }, room=room)

@socketio.on('join')
def on_join(data):
    sender_id = session.get('user_id')
    receiver_id = data['receiver_id']
    room = f"chat_{min(sender_id, receiver_id)}_{max(sender_id, receiver_id)}"
    join_room(room)

@app.route('/health')
def health():
    return {"status": "healthy"}, 200
# Admin credentials (only you!)
ADMIN_EMAIL = "admin@campusbazaar.com"
ADMIN_PASSWORD = "admin123"

@app.route('/admin')
def admin():
    if session.get('is_admin') != True:
        return redirect(url_for('admin_login'))
    users = User.query.all()
    items = Item.query.all()
    sold_items = Item.query.filter_by(sold=True).all()
    return render_template('admin.html', users=users, items=items, sold_items=sold_items)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['email'] == ADMIN_EMAIL and request.form['password'] == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin'))
        flash('Invalid admin credentials!', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/delete_item/<int:item_id>')
def admin_delete_item(item_id):
    if session.get('is_admin') != True:
        return redirect(url_for('admin_login'))
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Item deleted!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete_user/<int:user_id>')
def admin_delete_user(user_id):
    if session.get('is_admin') != True:
        return redirect(url_for('admin_login'))
    user = User.query.get_or_404(user_id)
    Item.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    flash('User deleted!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('home'))
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)