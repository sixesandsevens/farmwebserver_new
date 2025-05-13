from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import os
import json
import uuid
import bleach
from flask import send_from_directory
from datetime import datetime
from flask import jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_login import LoginManager
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from forms import RegistrationForm, LoginForm  # Adjust import based on your project structure
from models import db  # Import db from models
from models import User  # ✅ if User is in models.py
from forms import RegistrationForm, LoginForm

app = Flask(__name__)
app.secret_key = 'dev'
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure key
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://sixesandsevens:Absolute9497@sixesandsevens.mysql.pythonanywhere-services.com'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


# File paths
THREADS_FILE = 'data/forum_threads.json'
USER_FILE = 'data/users.json'
UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('data', exist_ok=True)


# Define the User model

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

#initialize flask-login

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to 'login' view if not authenticated

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#Create Registration and Login Forms

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


#Protect Routes with @login_required

@app.route('/forum/post', methods=['GET', 'POST'])
@login_required
def post_to_forum():
    # Your existing code for posting to the forum
    pass

@app.route('/gallery/upload', methods=['GET', 'POST'])
@login_required
def upload_to_gallery():
    # Your existing code for uploading to the gallery
    pass



# Ensure the uploads directory exists
def load_json(path, fallback):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return fallback

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def load_threads():
    return load_json(THREADS_FILE, [])

def save_threads(data):
    save_json(THREADS_FILE, data)

def load_users():
    return load_json(USER_FILE, [])

def save_users(data):
    save_json(USER_FILE, data)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/gallery')
def gallery():
    gallery_dir = os.path.join(app.static_folder, 'gallery')
    images = []
    if os.path.isdir(gallery_dir):
        for fn in sorted(os.listdir(gallery_dir)):
            if fn.lower().endswith(('.png','.jpg','.jpeg','.gif')):
                images.append(url_for('static', filename=f'gallery/{fn}'))
    return render_template('gallery.html', images=images)

@app.route('/forum')
def forum():
    threads = load_threads()
    return render_template('forum.html', threads=threads)

@app.route('/upload-image', methods=['POST'])
def upload_image():
    file = request.files.get('file')
    if not file:
        return jsonify(error='No file provided'), 400
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    # url_for with a leading slash, no _external needed
    image_url = url_for('static', filename=f'uploads/{filename}')
    return jsonify(location=image_url)

@app.route('/forum/new', methods=['GET', 'POST'])
def new_thread():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        username = request.form.get('author', 'Anonymous')
        timestamp = datetime.now().strftime('%B %d, %Y at %I:%M %p')

        threads = load_threads()
        threads.append({
            'id': str(uuid.uuid4()),
            'title': title,
            'author': username,
            'timestamp': timestamp,
            'posts': [
                { 'author': username, 'content': content, 'timestamp': timestamp }
            ]
        })
        save_threads(threads)
        return redirect(url_for('forum'))
    return render_template('new_thread.html')

# ... other routes, including forum() and thread(thread_id) ...


@app.route('/forum/thread/<thread_id>')
def view_thread(thread_id):
    threads = load_threads()
    thread = next((t for t in threads if t['id'] == thread_id), None)
    if not thread:
        return 'Thread not found', 404
    return render_template('thread.html', thread=thread)

@app.route('/forum/thread/<thread_id>/reply', methods=['POST'])
def reply(thread_id):
    print(f"Incoming reply to thread_id: {thread_id}")
    print(f"Form data: {request.form}")

    content = request.form.get('content', '').strip()
    username = request.form.get('author', 'Anonymous').strip()
    timestamp = datetime.now().strftime('%B %d, %Y at %I:%M %p')

    threads = load_threads()
    found = False
    for thread in threads:
        if str(thread['id']) == thread_id:
            thread['posts'].append({
                'author': username,
                'content': content,
                'timestamp': timestamp
            })
            found = True
            print(f"Reply saved to thread: {thread['title']}")
            break

    if not found:
        print(f"No thread found with ID: {thread_id}")

    save_threads(threads)
    return redirect(url_for('view_thread', thread_id=thread_id))

# login removed
def login():
    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']
        for user in load_users():
            if user['username'] == identifier or user['email'] == identifier:
                if check_password_hash(user['password'], password):
                    session['username'] = user['username']
                    return redirect(url_for('forum'))
        flash('Invalid login.')
    return render_template('login.html')

# register removed
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        users = load_users()
        if any(u['username'] == username or u['email'] == email for u in users):
            flash('User already exists.')
            return redirect(url_for('register'))
        users.append({'username': username, 'email': email, 'password': password})
        save_users(users)
        flash('Registration successful.')
        return redirect(url_for('login'))
    return render_template('register.html')

# logout removed
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/chickens')
def chickens():
    return render_template('chickens.html')

@app.route('/disorientation')
def disorientation():
    return render_template('disorientation.html')

@app.route('/spaces')
def spaces():
    return render_template('spaces.html')

@app.route('/zines')
def zines():
    return render_template('zines.html')

@app.route('/garbage')
def garbage():
    return render_template('garbage.html')

@app.route('/workdays')
def workdays():
    return render_template('workdays.html')

@app.route('/camps')
def camps():
    return render_template('camps.html')

# ... dirty fix for image uploads ...

@app.route('/forum/static/<path:filename>')
def forum_static(filename):
    return send_from_directory(app.static_folder, filename) 


if __name__ == '__main__':
    app.run(debug=True)



