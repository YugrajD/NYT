# app.py
from flask import Flask, jsonify, redirect, request, send_from_directory, session
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
from authlib.common.security import generate_token
from dotenv import load_dotenv
import os
import requests

# Load environment variables
load_dotenv()

# Static paths
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
@app.route('/login')
def login():
    session['nonce'] = nonce
    return oauth.flask_app.authorize_redirect('http://localhost:8000/authorize', nonce=nonce)

@app.route('/authorize')
def authorize():
    token = oauth.flask_app.authorize_access_token()
    user_info = oauth.flask_app.parse_id_token(token, nonce=session.get('nonce'))
    session['user'] = user_info
    return redirect('http://localhost:5173/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/api/me')
def get_user():
    if 'user' in session:
        return jsonify(session['user'])
    return jsonify({}), 401

# --- NYT Articles Endpoint ---
@app.route('/api/articles')
def get_articles():
    api_key = os.getenv('NYT_API_KEY')
    keyword = 'Davis OR Sacramento'
    page_num = request.args.get('page', default=0, type=int)

    try:
        resp = requests.get(
            f'https://api.nytimes.com/svc/search/v2/articlesearch.json?q={keyword}&page={page_num}&api-key={api_key}'
        )
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Comment System ---
comments_store = {}

@app.route('/api/comments')
def get_comments():
    url = request.args.get('url')
    return jsonify(comments_store.get(url, []))

@app.route('/api/comments', methods=['POST'])
def post_comment():
    data = request.get_json()
    url = data['url']
    comment = {"user": data['user'], "text": data['text']}
    comments_store.setdefault(url, []).append(comment)
    return jsonify({"status": "ok"})

# --- Frontend Serving ---
@app.route('/<path:path>')
@app.route('/')
def serve_frontend(path=''):
    if path and os.path.exists(os.path.join(static_path, path)):
        return send_from_directory(static_path, path)
    return send_from_directory(template_path, 'index.html')

# --- Run App ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8000)), debug=os.getenv('FLASK_ENV') != 'production')