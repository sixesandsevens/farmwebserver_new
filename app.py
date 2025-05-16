# app.py
import os, json, uuid
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, send_from_directory
)
from werkzeug.utils    import secure_filename
from flask_sqlalchemy  import SQLAlchemy
from flask_login       import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)

from models import db, User
from forms  import RegistrationForm, LoginForm, PasswordChangeForm

from flask import render_template, flash, redirect, url_for, current_app
from flask_mail import Mail, Message
from forms import FeedbackForm

from PIL import Image
import piexif
from io import BytesIO

from flask import Response, send_from_directory

app = Flask(__name__)

# at top of app.py, after app = Flask(...)
GALLERY_JSON = os.path.join(app.root_path, 'data', 'gallery.json')
STATIC_GALLERY = os.path.join(app.root_path, 'static', 'gallery')
os.makedirs(os.path.dirname(GALLERY_JSON), exist_ok=True)
os.makedirs(STATIC_GALLERY, exist_ok=True)
# initialize JSON if missing or empty
if not os.path.isfile(GALLERY_JSON) or os.path.getsize(GALLERY_JSON) == 0:
    with open(GALLERY_JSON, 'w') as f:
        json.dump([], f)

app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.secret_key = 'dev'
app.config['SECRET_KEY'] = 'your_secret_key'  # replace with a real one
app.config['SQLALCHEMY_DATABASE_URI'] = (
    'mysql+pymysql://'
    'sixesandsevens:absolute9497@'                           # your PA username & password
    'sixesandsevens.mysql.pythonanywhere-services.com/'      # <— note the trailing slash!
    'sixesandsevens$default'                                 # your actual database name
)
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 280
}

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config.update({
    'MAIL_SERVER': 'smtp.gmail.com',         # your SMTP server (Gmail in this example)
    'MAIL_PORT': 587,                        # TLS port
    'MAIL_USE_TLS': True,                    # enable TLS encryption
    'MAIL_USERNAME': 'chris.tanton86@gmail.com', # sender account username
    'MAIL_PASSWORD': 'cqcx wqpr ssaq dxsc',  # sender account password (or use env var)
    'MAIL_DEFAULT_SENDER': (                 # tuple(display name, email)
        'Farm Webserver',
        'your.email@gmail.com'
    )
})


#robots.txt

@app.route('/robots.txt')
def robots_txt():
    # if you put robots.txt in the static folder:
    return send_from_directory(app.static_folder, 'robots.txt', mimetype='text/plain')

@app.after_request
def add_robots_header(response):
    response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    return response


# Temporary—remove once you finish debugging
@app.route('/debug-gallery')
#@login_required
def debug_gallery():
    # absolute paths
    gallery_dir = os.path.join(app.root_path, 'static', 'gallery')
    json_file  = os.path.join(app.root_path, 'data', 'gallery.json')

    files = os.listdir(gallery_dir) if os.path.isdir(gallery_dir) else []
    try:
        data = json.load(open(json_file))
    except Exception as e:
        data = f"Error loading JSON: {e}"

    return jsonify(files=files, json=data)

# ← This binds the extension to your app immediately
mail = Mail(app)

UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads')
MAX_CONTENT_LENGTH=16 * 1024 * 1024

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Registration successful! You are now logged in.', 'success')
        return redirect(url_for('account'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # look up by email (matches your LoginForm)
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(request.args.get('next') or url_for('account'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = PasswordChangeForm()
    if form.validate_on_submit():
        # Check that the old password matches
        if current_user.check_password(form.old_password.data):
            # Update to the new password
            current_user.set_password(form.new_password.data)
            db.session.commit()
            # ← Flash success here
            flash('Password updated successfully.', 'success')
            # Redirect so refresh won’t re-submit the form
            return redirect(url_for('account'))
        else:
            # ← Flash failure here
            flash('Old password is incorrect.', 'danger')
    return render_template('account.html', form=form)


#mail

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    form = FeedbackForm()
    if form.validate_on_submit():
        msg = Message(
            subject=f"New Feedback from {form.name.data}",
            recipients=['chris.tanton86@gmail.com']   # where you want to receive feedback
        )
        msg.body = (
            f"Name: {form.name.data}\n"
            f"Email: {form.email.data}\n\n"
            f"Message:\n{form.message.data}"
        )
        mail.send(msg)
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('feedback'))
    return render_template('feedback.html', form=form)


# ---- FORUM / GALLERY / UPLOAD ----

@app.route('/')
def index():
    return render_template('index.html')

#gallery

@app.route('/gallery')
#@login_required
def gallery():
    # 1. List all valid image files
    files = [
        fn for fn in os.listdir(STATIC_GALLERY)
        if allowed_file(fn)
    ]

    # 2. Pair each filename with its mtime
    files_with_time = []
    for fn in files:
        path = os.path.join(STATIC_GALLERY, fn)
        mtime = os.path.getmtime(path)
        files_with_time.append((fn, mtime))

    # 3. Sort by mtime (oldest first; reverse=True for newest first)
    files_with_time.sort(key=lambda ft: ft[1])

    # 4. Build the URL list for your template
    images = [
        url_for('static', filename=f'gallery/{fn}')
        for fn, _ in files_with_time
    ]

    return render_template('gallery.html', images=images)

    # Build URLs
    images = [
        {
          "url": url_for('static', filename=f'gallery/{item["filename"]}'),
          "timestamp": item["timestamp"]
        }
        for item in data
    ]
    return render_template('gallery.html', images=images)

#gallery upload

@app.route('/gallery/upload', methods=['POST'])
#@login_required
def upload_to_gallery():
    file = request.files.get('file')
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        target = os.path.join(STATIC_GALLERY, filename)
        file.save(target)
        flash('Image uploaded successfully!', 'success')
    else:
        flash('Please select a valid image.', 'error')
    return redirect(url_for('gallery'))



# TinyMCE Image Upload

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
#@login_required
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

# dirty fix for image uploads
@app.route('/forum/static/<path:filename>')
def forum_static(filename):
    return send_from_directory(app.static_folder, filename)

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


import logging

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)

    with app.app_context():
        try:
            db.create_all()
            app.logger.info("Database tables created successfully.")
        except Exception as e:
            app.logger.error(f"Error creating database tables: {e}")
    app.run(debug=True)


def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions
