from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import textwrap
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure SQLAlchemy to use SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = SQLAlchemy(app)


# Define the User model for the SQLite database
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)


# Create the database tables if they don't exist
with app.app_context():
    db.create_all()


# Function to fetch YouTube transcript
def get_transcript(youtube_video_url):
    if 'v=' in youtube_video_url:
        video_id = youtube_video_url.split('v=')[1].split('&')[0]
    else:
        video_id = youtube_video_url.split('/')[-1]
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        if isinstance(transcript, list):  # Ensure transcript is a list of dictionaries
            return transcript
        else:
            raise ValueError(f"Unexpected transcript format: {transcript}")
    except Exception as e:
        return str(e)


# Function to split transcript into chunks
def chunk_transcript(transcript, chunk_size=8000):
    try:
        transcript_text = [entry['text'] for entry in transcript if isinstance(entry, dict) and 'text' in entry]
        chunks = []
        chunk = ''
        for entry in transcript_text:
            if len(chunk + entry) < chunk_size:
                chunk += entry + ' '
            else:
                chunks.append(chunk)
                chunk = entry + ' '
        if chunk:
            chunks.append(chunk)
        return chunks
    except Exception as e:
        flash(f"Error chunking transcript: {str(e)}", "danger")
        return []


# Function to convert text into Markdown
def to_markdown(text):
    text = text.replace('•', '  *')
    return textwrap.indent(text, '> ', predicate=lambda _: True)


# Function to generate notes using Generative AI in chunks
def generate_notes_in_chunks(transcript_chunks, model):
    all_notes = ''
    for i, chunk in enumerate(transcript_chunks):
        try:
            response = model.generate_content(
                f"Role: you are a professional notes maker for exams. "
                f"Task: Make full detailed notes on the following chunk: {chunk}"
            )
            print(f"Response for chunk {i}: {response}")  # Debugging line
            if response and hasattr(response, 'text'):
                all_notes += response.text + '\n\n'
            else:
                all_notes += f"Error generating notes for chunk {i}.\n\n"
        except Exception as e:
            all_notes += f"Error in chunk {i}: {str(e)}\n\n"
        time.sleep(1)  # Avoid hitting API rate limits
    return all_notes


# Signup function (register new user)
def sign_up(email, password, username):
    try:
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully! You can now log in.', 'success')
        return True
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return None


# Login function (authenticate user)
def login(email, password):
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        session['logged_in'] = True
        session['user_id'] = user.id
        session['username'] = user.username
        flash('Login successful! Welcome back.', 'success')
        return True
    else:
        flash('Invalid credentials. Please try again.', 'danger')
        return None


# Route for home page
@app.route('/')
def index():
    if 'logged_in' in session and session['logged_in']:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


# Route for signup page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        username = request.form.get('username')
        if email and password and username:
            success = sign_up(email, password, username)
            if success:
                return redirect(url_for('login_route'))
        else:
            flash('Please fill out all fields', 'warning')
    return render_template('signup.html')


# Route for login page
@app.route('/login', methods=['GET', 'POST'])
def login_route():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email and password:
            success = login(email, password)
            if success:
                return redirect(url_for('dashboard'))
        else:
            flash('Please provide valid credentials', 'warning')
    return render_template('login.html')


# Route for dashboard
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login_route'))

    if request.method == 'POST':
        google_api_key = request.form.get('google_api_key')
        youtube_url = request.form.get('youtube_url')

        if google_api_key and youtube_url:
            try:
                # Configure Generative AI model
                genai.configure(api_key=google_api_key)
                model = genai.GenerativeModel(model_name="gemini-1.5-pro")

                # Fetch transcript
                transcript = get_transcript(youtube_url)
                if isinstance(transcript, list):
                    transcript_chunks = chunk_transcript(transcript)
                    notes = generate_notes_in_chunks(transcript_chunks, model)
                    notes_markdown = to_markdown(notes)
                    session['notes'] = notes_markdown  # Store generated notes in session
                    return redirect(url_for('notes_display'))
                else:
                    flash(f"Error fetching transcript: {transcript}", "danger")
            except Exception as e:
                flash(f"Error: {str(e)}", "danger")
        else:
            flash("Please provide both API key and YouTube URL", "warning")
    return render_template('dashboard.html')


# Route to display generated notes
@app.route('/notes')
def notes_display():
    if 'notes' in session:
        notes = session['notes']
        return render_template('notesdisplay.html', notes=notes)
    else:
        flash("No notes available to display", "warning")
        return redirect(url_for('dashboard'))


# Route for logout
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", 'success')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
