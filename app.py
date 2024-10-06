from flask import Flask, render_template, request, redirect, session, flash, url_for
import firebase_admin
from firebase_admin import credentials, firestore, auth as firebase_auth
import pyrebase
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import textwrap
import time
import textwrap
from markdown import Markdown

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Initialize Firebase app
if not firebase_admin._apps:
    cred = credentials.Certificate(
        r"C:\Users\msaur\PycharmProjects\Main Character\noteworthy-6b16e-firebase-adminsdk-8bubu-2fd7c2affe.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Pyrebase configuration (replace with your Firebase web API details)
firebase_config = {
    "apiKey": "AIzaSyAMMhi9ZduX9PHiB7nRKP0Bh9Q2TZFigRI",
    "authDomain": "noteworthy-6b16e.firebaseapp.com",
    "databaseURL": "https://noteworthy.firebaseio.com",
    "projectId": "noteworthy-6b16e",
    "storageBucket": "noteworthy-6b16e.appspot.com",
    "messagingSenderId": "324159317808",
    "appId": "1:324159317808:web:9f85cb518521198fc74af5",
    "measurementId": "G-H36V5X6CGQ"
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()




def to_markdown(text):
    # Convert bullet points to markdown style
    text = text.replace('•', '  *')  # Two spaces before the bullet
    # Indent all text for blockquote formatting
    return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))



# Function to fetch YouTube transcript
def get_transcript(youtube_video_url):
    if 'v=' in youtube_video_url:
        video_id = youtube_video_url.split('v=')[1].split('&')[0]
    else:
        video_id = youtube_video_url.split('/')[-1]

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        return transcript
    except Exception as e:
        return str(e)

# Function to split transcript into chunks
def chunk_transcript(transcript, chunk_size=8000):
    transcript_text = [entry['text'] for entry in transcript]
    chunks = []
    chunk = ''
    for entry in transcript_text:
        if len(chunk + entry) < chunk_size:
            chunk += entry + ' '
        else:
            chunks.append(chunk)
            chunk = entry + ' '
    if chunk:  # Add any remaining text
        chunks.append(chunk)
    return chunks

# Function to convert text into Markdown
def to_markdown(text):
    text = text.replace('•', '  *')
    return textwrap.indent(text, '> ', predicate=lambda _: True)

# Function to generate notes using Generative AI in chunks
def generate_notes_in_chunks(transcript_chunks, model):
    all_notes = ''
    for i, chunk in enumerate(transcript_chunks):
        try:
            response = model.generate_content("Role: you are a professional notes maker who is making notes for exams ,back story: you have assigned the task to make notes of topic including important points, and also making a conclusion,include everything important in that topic.,task: Make full detailed notes on the following topic(transcript) chunk: " + chunk)
            if response and hasattr(response, 'text'):
                all_notes += response.text + '\n\n'
            else:
                all_notes += "Error generating notes for chunk {i}.\n\n"
        except Exception as e:
            all_notes += f"Error in chunk {i}: {str(e)}\n\n"
        time.sleep(1)  # Introduce a small delay to avoid hitting rate limits
    return all_notes

# Function to store user data in Firestore
def store_user_data(user_id, email, username):
    try:
        db.collection('users').document(user_id).set({
            'email': email,
            'username': username
        })
    except Exception as e:
        flash(f"Error: {e}", "danger")

# Sign Up Function
def sign_up(email, password, username):
    try:
        user = auth.create_user_with_email_and_password(email, password)
        store_user_data(user['localId'], email, username)
        return user
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return None

# Login Function
def login(email, password):
    try:
        user = auth.sign_in_with_email_and_password(email, password)
        return user
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return None

# Route for home page
@app.route('/')
def index():
    if 'logged_in' in session and session['logged_in']:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# Route for sign-up
# Sign Up Function
def sign_up(email, password, username):
    try:
        # Try to create a new user
        user = auth.create_user_with_email_and_password(email, password)
        # Store user data in Firestore
        store_user_data(user['localId'], email, username)
        flash('Account created successfully! You can now log in.', 'success')
        return user
    except Exception as e:
        error_message = str(e)
        if 'EMAIL_EXISTS' in error_message:
            flash('This email is already registered. Please use another email.', 'danger')
        elif 'WEAK_PASSWORD' in error_message:
            flash('Password should be at least 6 characters long.', 'danger')
        else:
            flash(f"An error occurred: {error_message}", 'danger')
        return None

# Login Function
def login(email, password):
    try:
        # Try to authenticate the user
        user = auth.sign_in_with_email_and_password(email, password)
        flash('Login successful! Welcome back.', 'success')
        return user
    except Exception as e:
        error_message = str(e)
        if 'INVALID_PASSWORD' in error_message:
            flash('Incorrect password. Please try again.', 'danger')
        elif 'EMAIL_NOT_FOUND' in error_message:
            flash('No account found with this email. Please sign up first.', 'danger')
        else:
            flash(f"An error occurred: {error_message}", 'danger')
        return None

# Route for sign-up
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        username = request.form.get('username')
        if email and password and username:
            user = sign_up(email, password, username)
            if user:
                session['logged_in'] = True
                session['user_id'] = user['localId']
                return redirect(url_for('dashboard'))
        else:
            flash('Please fill out all fields', 'warning')
    return render_template('signup.html')

# Route for login
@app.route('/login', methods=['GET', 'POST'])
def login_route():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email and password:
            user = login(email, password)
            if user:
                session['logged_in'] = True
                session['user_id'] = user['localId']
                return redirect(url_for('dashboard'))
        else:
            flash('Please provide valid credentials', 'warning')
    return render_template('login.html')


# Dashboard route
# Dashboard route to take API key and URL input
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
                if transcript:
                    # Split transcript into chunks
                    transcript_chunks = chunk_transcript(transcript)

                    # Generate notes for each chunk
                    notes = generate_notes_in_chunks(transcript_chunks, model)

                    # Render notes in Markdown and store in session to pass to the next page
                    notes_markdown = to_markdown(notes)
                    session['notes'] = notes_markdown  # Save generated notes in session

                    # Redirect to the notes display page
                    return redirect(url_for('notes_display'))
                else:
                    flash("Error fetching transcript", "danger")
            except Exception as e:
                flash(f"Error: {e}", "danger")
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
    flash("You have been logged out.", "success")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
