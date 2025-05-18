from flask import Flask, jsonify, redirect, request, send_from_directory, session, url_for
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
from authlib.common.security import generate_token
from dotenv import load_dotenv
import os
import requests

# Load environment variables
load_dotenv()

# Paths for static/prod frontend
static_path = os.getenv('STATIC_PATH', 'static')
template_path = os.getenv('TEMPLATE_PATH', 'templates')

# Initialize Flask
app = Flask(__name__, static_folder=static_path, template_folder=template_path)
CORS(app, supports_credentials=True)
app.secret_key = os.urandom(24)

# --- OAuth Setup for Dex ---
oauth = OAuth(app)
nonce = generate_token()

oauth.register(
    name=os.getenv('OIDC_CLIENT_NAME'),
    client_id=os.getenv('OIDC_CLIENT_ID'),
    client_secret=os.getenv('OIDC_CLIENT_SECRET'),
    authorization_endpoint="http://localhost:5556/auth",
    token_endpoint="http://dex:5556/token",
    jwks_uri="http://dex:5556/keys",
    userinfo_endpoint="http://dex:5556/userinfo",
    device_authorization_endpoint="http://dex:5556/device/code",
    client_kwargs={'scope': 'openid email profile'}
)

# --- Auth Routes ---
@app.route('/')
def home():
    user = session.get('user')
    if user:
        return f"<h2>Logged in as {user['email']}</h2><a href='/logout'>Logout</a>"
    return '<a href="/login">Login with Dex</a>'

@app.route('/login')
def login():
    session['nonce'] = nonce
    redirect_uri = 'http://localhost:8000/authorize'
    return oauth.flask_app.authorize_redirect(redirect_uri, nonce=nonce)

@app.route('/authorize')
def authorize():
    token = oauth.flask_app.authorize_access_token()
    nonce = session.get('nonce')
    user_info = oauth.flask_app.parse_id_token(token, nonce=nonce)
    session['user'] = user_info
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# --- NYT Articles Endpoint ---
@app.route('/api/articles')
def get_articles():
    api_key = os.getenv('NYT_API_KEY')
    keyword = 'Davis OR Sacramento'
    page_num = request.args.get('page', default=0, type=int)

    nyt_url = f'https://api.nytimes.com/svc/search/v2/articlesearch.json?q={keyword}&page={page_num}&api-key={api_key}'

    try:
        nyt_response = requests.get(nyt_url)
        return jsonify(nyt_response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Current User Info ---
@app.route('/api/me')
def get_current_user():
    user = session.get('user')
    if user:
        return jsonify(user)
    return jsonify({}), 401

# --- Serve frontend (production mode) ---
@app.route('/<path:path>')
@app.route('/')
def serve_frontend(path=''):
    if path and os.path.exists(os.path.join(static_path, path)):
        return send_from_directory(static_path, path)
    return send_from_directory(template_path, 'index.html')

# --- Start the app ---
if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)), debug=debug_mode)
