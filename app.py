from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

SONGS_DIR = 'songs'
SONGS_FILE = 'songs_db.json'

os.makedirs(SONGS_DIR, exist_ok=True)

def load_songs():
    songs = []
    
    # 1. Safe JSON load
    if os.path.exists(SONGS_FILE):
        try:
            with open(SONGS_FILE, 'r', encoding='utf-8') as f:
                content = json.load(f)
                if isinstance(content, list):
                    songs.extend(content)
        except Exception as e:
            print("JSON Load Error:", e)

    # 2. Safe directory scan
    if os.path.exists(SONGS_DIR):
        existing = [s.get('stream_url', '').split('/')[-1] for s in songs]
        try:
            for idx, filename in enumerate(os.listdir(SONGS_DIR), start=len(songs) + 1):
                if filename.lower().endswith(('.mp3', '.m4a', '.wav')) and filename not in existing:
                    clean_title = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').title()
                    songs.append({
                        "id": str(idx),
                        "title": clean_title,
                        "artist": "Arijit Singh",
                        "album": "Single",
                        "image": "https://upload.wikimedia.org/wikipedia/en/2/2f/Brahmastra_Teaser.jpg",
                        "stream_url": f"/songs/{filename}"
                    })
        except Exception as e:
            print("Dir Scan Error:", e)
            
    return songs

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "app": "BeatPulse Server",
        "message": "Backend is running!"
    })

@app.route('/songs/<path:filename>')
def serve_song(filename):
    return send_from_directory(SONGS_DIR, filename)

@app.route('/search', methods=['GET'])
def search_songs():
    query = request.args.get('q', '') or request.args.get('query', '')
    all_songs = load_songs()
    host_url = request.host_url.rstrip('/')
    
    formatted = []
    for s in all_songs:
        sc = dict(s)
        if sc.get('stream_url', '').startswith('/'):
            sc['stream_url'] = f"{host_url}{sc['stream_url']}"
        formatted.append(sc)

    if not query:
        return jsonify({"status": "success", "count": len(formatted), "results": formatted})

    q_lower = query.lower()
    filtered = [s for s in formatted if q_lower in s.get('title', '').lower() or q_lower in s.get('artist', '').lower()]
    return jsonify({"status": "success", "count": len(filtered), "results": filtered if filtered else formatted})

@app.route('/artist/top-hits', methods=['GET'])
def artist_top_hits():
    return search_songs()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
