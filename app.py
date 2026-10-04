from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

SONGS_FILE = 'songs_db.json'

def load_songs():
    if os.path.exists(SONGS_FILE):
        try:
            with open(SONGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print("Error loading songs_db.json:", e)
    return []

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "app": "SonicFlow Backend (Arijit Singh 100 Songs Dedicated Engine)",
        "message": "Engine is active!"
    })

@app.route('/search', methods=['GET'])
def search_songs():
    query = request.args.get('q', '') or request.args.get('query', '')
    songs = load_songs()
    
    if not query:
        return jsonify({"status": "success", "count": len(songs), "results": songs})

    q_lower = query.lower()
    filtered = [
        s for s in songs 
        if q_lower in s.get('title', '').lower() or 
           q_lower in s.get('artist', '').lower() or 
           q_lower in s.get('album', '').lower()
    ]

    return jsonify({"status": "success", "count": len(filtered), "results": filtered if filtered else songs})

@app.route('/artist/top-hits', methods=['GET'])
def artist_top_hits():
    artist_name = request.args.get('name', '') or request.args.get('q', '') or 'Arijit Singh'
    songs = load_songs()
    
    # Filter Arijit Singh songs from the database
    filtered = [s for s in songs if artist_name.lower() in s.get('artist', '').lower()]
    results = filtered if filtered else songs

    return jsonify({"status": "success", "artist": artist_name, "count": len(results), "results": results})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
