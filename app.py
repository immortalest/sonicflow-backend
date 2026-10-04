from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

SONGS_FILE = 'songs_db.json'

# Sample initial songs database with high-quality working MP3s
INITIAL_SONGS = [
    {
        "id": "1",
        "title": "Kesariya",
        "artist": "Arijit Singh, Pritam",
        "album": "Brahmastra",
        "image": "https://upload.wikimedia.org/wikipedia/en/2/2f/Brahmastra_Teaser.jpg",
        "stream_url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        "duration": 372
    },
    {
        "id": "2",
        "title": "Tere Ishq Mein",
        "artist": "Arijit Singh, Mithoon",
        "album": "Single",
        "image": "https://upload.wikimedia.org/wikipedia/en/2/2f/Brahmastra_Teaser.jpg",
        "stream_url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
        "duration": 423
    },
    {
        "id": "3",
        "title": "Chaleya",
        "artist": "Arijit Singh, Anirudh Ravichander",
        "album": "Jawan",
        "image": "https://upload.wikimedia.org/wikipedia/en/2/2f/Brahmastra_Teaser.jpg",
        "stream_url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
        "duration": 315
    }
]

def load_songs():
    if not os.path.exists(SONGS_FILE):
        with open(SONGS_FILE, 'w') as f:
            json.dump(INITIAL_SONGS, f, indent=4)
        return INITIAL_SONGS
    try:
        with open(SONGS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return INITIAL_SONGS

def save_songs(songs):
    with open(SONGS_FILE, 'w') as f:
        json.dump(songs, f, indent=4)

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "app": "SonicFlow Backend (Option 3 - Cloud Storage Engine)",
        "message": "Direct Cloud MP3 Storage Engine is running smoothly!"
    })

@app.route('/search', methods=['GET'])
def search_songs():
    query = request.args.get('q', '') or request.args.get('query', '')
    songs = load_songs()
    
    if not query:
        return jsonify({"status": "success", "count": len(songs), "results": songs})

    query_lower = query.lower()
    filtered = [
        s for s in songs 
        if query_lower in s.get('title', '').lower() or 
           query_lower in s.get('artist', '').lower() or 
           query_lower in s.get('album', '').lower()
    ]

    return jsonify({"status": "success", "count": len(filtered), "results": filtered if filtered else songs})

@app.route('/artist/top-hits', methods=['GET'])
def artist_top_hits():
    artist_name = request.args.get('name', '') or request.args.get('q', '') or 'Arijit Singh'
    songs = load_songs()
    
    filtered = [s for s in songs if artist_name.lower() in s.get('artist', '').lower()]
    results = filtered if filtered else songs

    return jsonify({"status": "success", "artist": artist_name, "count": len(results), "results": results})

@app.route('/add-song', methods=['POST'])
def add_song():
    data = request.get_json()
    if not data or not data.get('title') or not data.get('stream_url'):
        return jsonify({"status": "error", "message": "Title and stream_url are required"}), 400

    songs = load_songs()
    new_song = {
        "id": str(len(songs) + 1),
        "title": data.get('title'),
        "artist": data.get('artist', 'Unknown Artist'),
        "album": data.get('album', 'Single'),
        "image": data.get('image', 'https://via.placeholder.com/500'),
        "stream_url": data.get('stream_url'),
        "duration": data.get('duration', 0)
    }
    
    songs.append(new_song)
    save_songs(songs)
    return jsonify({"status": "success", "message": "Song added successfully", "song": new_song})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
