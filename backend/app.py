# app.py
from flask import Flask, jsonify, redirect, request, send_from_directory, session
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
from authlib.common.security import generate_token
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
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

# MongoDB setup
mongo_uri = os.getenv("MONGO_URI")
mongo_client = MongoClient(mongo_uri)
db = mongo_client.get_database()
comments_collection = db.comments

# --- Auth Routes ---
@app.route('/login')
def login():
    session['nonce'] = nonce
    return oauth.flask_app.authorize_redirect('http://localhost:8000/authorize', nonce=nonce)
 # --- Redirect to Dex for authorization ---
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
            f'https://api.nytimes.com/svc/search/v2/articlesearch.json'
            f'?q={keyword}&page={page_num}&api-key={api_key}'
        )
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Comment System ---
@app.route('/api/comments')
def get_comments():
    url = request.args.get('url')
    if not url:
        return jsonify([])
    # find all comments for the given URL and return them as JSON
    docs = comments_collection.find({'url': url})
    out = []
    for d in docs:
        out.append({
            '_id': str(d['_id']),
            'url': d['url'],
            'user': d.get('user', 'anonymous'),
            'text': d.get('text', ''),
            'removed': d.get('removed', False),
            'parentId': d.get('parentId')
        })
    return jsonify(out)

# route for posting comments
@app.route('/api/comments', methods=['POST'])
def post_comment():
    data = request.get_json()
    # check for required fields
    if not data.get('url') or not data.get('text'):
        return jsonify({'error': 'Missing fields'}), 400
    comment = {
        'url': data['url'],
        'user': data.get('user', 'anonymous'),
        'text': data['text']
    }
    # attach parentId if this is a reply
    if data.get('parentId'):
        comment['parentId'] = data['parentId']
    # ensure removed flag is always present
    comment['removed'] = False
    comments_collection.insert_one(comment)
    return jsonify({'status': 'ok'})

# route for counting comments
@app.route('/api/comment-counts')
def comment_counts():
    counts = {}
    # count comments for each URL``
    for doc in comments_collection.find():
        url = doc['url']
        counts[url] = counts.get(url, 0) + 1
    return jsonify(counts)

# --- Moderator‐only soft delete ---
@app.route('/api/comments/<comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    user = session.get('user', {})
    # only the moderator@example.com account may delete, maybe admin too later but the rubric doesn't say TA
    if user.get('email') != 'moderator@hw3.com':
        return jsonify({'error': 'Forbidden'}), 403
    # instead of removing, mark removed=true
    result = comments_collection.update_one(
        {'_id': ObjectId(comment_id)},
        {'$set': {'removed': True}}
    )
    # if we found a comment, return its id
    if result.matched_count:
        return jsonify({'status': 'soft-deleted', 'id': comment_id})
    return jsonify({'error': 'Not found'}), 404

# --- Frontend Serving ---
@app.route('/<path:path>')
@app.route('/')
def serve_frontend(path=''):
    if path and os.path.exists(os.path.join(static_path, path)):
        return send_from_directory(static_path, path)
    return send_from_directory(template_path, 'index.html')

# --- Run App ---
if __name__ == '__main__':
    app.run(
      host='0.0.0.0',
      port=int(os.getenv('PORT', 8000)),
      debug=os.getenv('FLASK_ENV') != 'production'
    )