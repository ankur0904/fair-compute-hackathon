from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import base64
import aiohttp
import asyncio
import nest_asyncio
import json

# Apply nest_asyncio
nest_asyncio.apply()

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

async def fetch(session, url, data):
    async with session.post(url, data=data) as response:
        return await response.text()

async def main(image_data: str, prompt: str = "Explain the image."):
    url = "http://8.12.5.48:11434/api/generate"
    data = json.dumps(
        {
            "model": "llava:7b-v1.6-mistral-q5_K_M",
            "prompt": prompt,
            "stream": False,
            "images": [image_data]
        }
    )
    headers = {"Content-Type": "application/json"}

    async with aiohttp.ClientSession(headers=headers) as session:
        response = await fetch(session, url, data)
        return response

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/app')
# @login_required
def index():
    if current_user.is_authenticated:
        return render_template('app.html')
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(request.args.get('next') or url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm-password']
        print(confirm_password)
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('signup'))
        
        if not User.query.filter_by(username=username).first():
            new_user = User(username=username, password=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username already exists', 'error')
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/process_image', methods=['POST'])
@login_required
def process_image():
    image = request.files['image']
    image_data = base64.b64encode(image.read()).decode('utf-8')
    
    question_type = request.form.get('questionType')
    question = request.form['question']
    
    # If a question type is selected, use it. Otherwise, use the manually input question
    if question_type:
        question = question_type
    # Run asynchronous task
    response = asyncio.run(main(image_data, question))
    response = json.loads(response)
    return jsonify({'result': response["response"], 'question': question})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
