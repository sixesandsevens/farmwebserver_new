import os
import json
import uuid
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, send_from_directory
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin,
    login_user, logout_user, login_required, current_user
)

# pull in your models and forms
from models import db, User
from forms import RegistrationForm, LoginForm, PasswordChangeForm

app = Flask(__name__)
app.secret_key = 'dev'
app.config['SECRET_KEY'] = 'your_secret_key'  # replace with a real one
app.config['SQLALCHEMY_DATABASE_URI'] = (
    'mysql+pymysql://sixesandsevens:Absolute9497@'
    'sixesandsevens.mysql.pythonanywhere-services.com'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# initialise extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# helper JSON I/O
def load_json(path, fallback):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return fallback

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

THREADS_FILE = 'data/forum_threads.json'
USER_FILE    = 'data/users.json'
UPLOAD_DIR   = os.path.join(app.static_folder, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs('data', exist_ok=True)


# ---- AUTH ROUTES ----

@app.route('/register', methods=['GET','POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # double-check uniqueness
        if User.query.filter_by(username=form.username.data).first():
            flash("Username taken.", "danger")
        elif User.query.filter_by(email=form.email.data).first():
            flash("Email already registered.", "danger")
        else:
            user = User(
                username=form.username.data,
                email=form.email.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash("Registered! Please log in.", "success")
            return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('forum'))
        flash("Invalid credentials.", "danger")
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/account', methods=['GET','POST'])
@login_required
def account():
    form = PasswordChangeForm()
    if form.validate_on_submit():
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash("Password updated.", "success")
    return render_template('account.html', form=form)


# ---- FORUM / GALLERY / UPLOAD ----

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


@app.route('/gallery/upload', methods=['GET','POST'])
@login_required
def upload_to_gallery():
    # your existing gallery-upload logic here
    pass


@app.route('/upload-image', methods=['POST'])
def upload_image():
    file = request.files.get('file')
    if not file:
        return jsonify(error='No file provided'), 400
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    image_url = url_for('static', filename=f'uploads/{filename}')
    return jsonify(location=image_url)


@app.route('/forum')
def forum():
    threads = load_json(THREADS_FILE, [])
    return render_template('forum.html', threads=threads)


@app.route('/forum/post', methods=['GET','POST'])
@login_required
def post_to_forum():
    # your existing forum-post logic here
    pass


@app.route('/forum/new', methods=['GET','POST'])
def new_thread():
    if request.method == 'POST':
        title   = request.form['title']
        content = request.form['content']
        author  = request.form.get('author','Anonymous')
        ts      = datetime.now().strftime('%B %d, %Y at %I:%M %p')
        threads = load_json(THREADS_FILE, [])
        threads.append({
            'id': str(uuid.uuid4()),
            'title': title,
            'author': author,
            'timestamp': ts,
            'posts': [{ 'author': author, 'content': content, 'timestamp': ts }]
        })
        save_json(THREADS_FILE, threads)
        return redirect(url_for('forum'))
    return render_template('new_thread.html')


@app.route('/forum/thread/<thread_id>')
def view_thread(thread_id):
    threads = load_json(THREADS_FILE, [])
    thread  = next((t for t in threads if t['id']==thread_id), None)
    if not thread:
        return 'Thread not found', 404
    return render_template('thread.html', thread=thread)


@app.route('/forum/thread/<thread_id>/reply', methods=['POST'])
def reply(thread_id):
    content = request.form.get('content','').strip()
    author  = request.form.get('author','Anonymous').strip()
    ts      = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    threads = load_json(THREADS_FILE, [])
    for t in threads:
        if t['id']==thread_id:
            t['posts'].append({'author':author,'content':content,'timestamp':ts})
            break
    save_json(THREADS_FILE, threads)
    return redirect(url_for('view_thread', thread_id=thread_id))


@app.route('/forum/static/<path:filename>')
def forum_static(filename):
    return send_from_directory(app.static_folder, filename)



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
    # create tables if missing
    with app.app_context():
        db.create_all()
    app.run(debug=True)