import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth
import pyrebase
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import textwrap


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
        st.error(f"Error fetching transcript: {e}")
        return []

# Function to convert text into Markdown
def to_markdown(text):
    text = text.replace('•', '  *')
    return textwrap.indent(text, '> ', predicate=lambda _: True)

# Function to generate notes using Generative AI
def generate_notes(transcript, model):
    transcript_text = ' '.join([entry['text'] for entry in transcript])

    response = model.generate_content("Make full detailed notes on the given transcript DON'T MISS ANYTHING: use 8000 tokens " + transcript_text)

    if response and hasattr(response, 'text'):
        return response.text
    else:
        st.error("Failed to generate notes.")
        return ""

# Streamlit app interface
st.title("Noteworthy")
# Initialize Firebase app (use your own Firebase credentials)
if not firebase_admin._apps:  # Check if Firebase app is already initialized
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


# Function to store user data in Firestore
def store_user_data(user_id, email, username):
    try:
        db.collection('users').document(user_id).set({
            'email': email,
            'username': username
        })
        st.success(f"User  registered successfully!")
    except Exception as e:
        st.error(f"Internal Error: Don't worry, we're here to help. Try again or contact us")


# Sign Up Function
def sign_up(email, password, username):
    try:
        user = auth.create_user_with_email_and_password(email, password)
        store_user_data(user['localId'], email, username)
    except Exception as e:
        st.error(f"Huh😕.This isn’t supposed to happen. Please try signing in again or contact us.")


# Login Function
def login(email, password):
    try:
        user = auth.sign_in_with_email_and_password(email, password)
        st.success(f"Logged in as {email}")
        return user
    except Exception as e:
        st.error(f"Huh😕.This isn’t supposed to happen. Please try to login again or contact us.")
        return None


# Streamlit App Interface
st.title("Stop Scribbling, Start Clicking")

# Initialize session state for 'logged_in'
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# Sidebar for API key input
st.sidebar.title("API & Settings")
if st.session_state['logged_in']:
    google_api_key = st.sidebar.text_input("Enter your Google API Key", type="password")
    st.sidebar.warning(
        "Disclaimer: You are responsible for managing your API usage. Be mindful of API costs and quotas when using the service.")

    # Button for Google API Key link
    if st.sidebar.button("Get Google API Key"):
        st.sidebar.markdown("[Click here to create an API key](https://console.cloud.google.com/apis/credentials)",
                    unsafe_allow_html=True)

    # Disclaimer for users
    st.sidebar.warning("Need an API key? Click here to get started.")


else:
    st.sidebar.write("Please log in to access the API key input.")


# Check if user is logged in
if not st.session_state['logged_in']:
    st.header("Welcome! Please Log In or Sign Up")

    # Login/Signup options
    option = st.selectbox("Choose an option", ["Login", "Sign Up"])

    if option == "Sign Up":
        st.subheader("Sign Up")
        signup_email = st.text_input("Enter your email")
        signup_password = st.text_input("Enter your password", type="password")
        signup_username = st.text_input("Enter your username")
        if st.button("Sign Up"):
            if signup_email and signup_password and signup_username:
                sign_up(signup_email, signup_password, signup_username)
            else:
                st.warning("Please fill out all fields.")

    if option == "Login":
        st.subheader("Login")
        login_email = st.text_input("Enter your email")
        login_password = st.text_input("Enter your password", type="password")
        if st.button("Login"):
            user = login(login_email, login_password)
            if user:
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = user['localId']
else:
    st.success(f"Welcome ! You are logged in.")


    # Input for YouTube URL
    youtube_url = st.text_input("Enter YouTube video URL")

    # Button to generate notes
    if st.button("Generate Notes"):
        if google_api_key and youtube_url:
            try:
                # Configure the Generative AI model
                genai.configure(api_key=google_api_key)
                model = genai.GenerativeModel(model_name="gemini-1.5-pro")

                # Fetch transcript
                transcript = get_transcript(youtube_url)

                if transcript:
                    # Generate notes
                    notes = generate_notes(transcript, model)

                    # Display the generated notes
                    if notes:
                        st.markdown(to_markdown(notes))
                else:
                    st.error("Give it another shot, or contact us")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Please provide both a valid API key (in the sidebar) and YouTube URL.")

    # Logout button
    if st.button("Logout"):
        st.session_state['logged_in'] = False
        st.success("You have been logged out.")
