from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

SONGS_DIR = 'songs'
SONGS_FILE = 'songs_db.json'

os.makedirs(SONGS_DIR, exist_ok=True)

# Default baseline song if database is empty
DEFAULT_SONG = {
    "id": "1",
    "title": "Kesariya",
    "artist": "Arijit Singh",
    "album": "Brahmastra",
    "image": "https://upload.wikimedia.org/wikipedia/en/2/2f/Brahmastra_Teaser.jpg",
    "stream_url": "/songs/Kesariya.mp3"
}

def load_songs():
    songs = []
    
    # 1. Load songs from songs_db.json
    if os.path.exists(SONGS_FILE):
        try:
            with open(SONGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    songs = data
        except Exception as e:
            print("Error loading songs_db.json:", e)

    if not songs:
        songs = [DEFAULT_SONG]

    # 2. Auto-scan songs/ folder for any newly added .mp3 files
    if os.path.exists(SONGS_DIR):
        existing_filenames = [s.get('stream_url', '').split('/')[-1] for s in songs]
        for idx, filename in enumerate(os.listdir(SONGS_DIR), start=len(songs) + 1):
            if filename.lower().endswith(('.mp3', '.m4a', '.wav', '.aac')) and filename not in existing_filenames:
                clean_title = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').title()
                songs.append({
                    "id": str(idx),
                    "title": clean_title,
                    "artist": "Arijit Singh",
                    "album": "Single",
                    "image": "https://upload.wikimedia.org/wikipedia/en/2/2f/Brahmastra_Teaser.jpg",
                    "stream_url": f"/songs/{filename}"
                })
                
    return songs

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "app": "BeatPulse Clean Single-Song Engine",
        "message": "Self-hosted music server is active!"
    })

# Serve MP3 files directly from songs/ directory
@app.route('/songs/<path:filename>')
def serve_song(filename):
    file_path = os.path.join(SONGS_DIR, filename)
    if os.path.exists(file_path):
        return send_from_directory(SONGS_DIR, filename)
    
    return jsonify({
        "status": "error",
        "message": f"File '{filename}' not found. Please upload '{filename}' into the 'songs/' folder on GitHub!"
    }), 404

@app.route('/search', methods=['GET'])
def search_songs():
    query = request.args.get('q', '') or request.args.get('query', '')
    all_songs = load_songs()
    
    host_url = request.host_url.rstrip('/')
    formatted_songs = []
    for s in all_songs:
        song_copy = dict(s)
        url = song_copy.get('stream_url', '')
        if url.startswith('/'):
            song_copy['stream_url'] = f"{host_url}{url}"
        formatted_songs.append(song_copy)

    if not query:
        return jsonify({"status": "success", "count": len(formatted_songs), "results": formatted_songs})

    q_lower = query.lower()
    filtered = [
        s for s in formatted_songs 
        if q_lower in s.get('title', '').lower() or 
           q_lower in s.get('artist', '').lower()
    ]

    return jsonify({"status": "success", "count": len(filtered), "results": filtered if filtered else formatted_songs})

@app.route('/artist/top-hits', methods=['GET'])
def artist_top_hits():
    return search_songs()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
