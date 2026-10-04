from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# Backup API URLs (Agar ek domain down ho toh doosra apne aap try hoga)
API_BASE_URLS = [
    "https://saavn.me/api",
    "https://saavn.dev/api",
    "https://jiosaavn-api-v3.vercel.app"
]

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "app": "SonicFlow Backend Engine v2",
        "message": "Server is running smoothly!"
    })

def fetch_jiosaavn(endpoint_path, params):
    headers = {'User-Agent': 'Mozilla/5.0'}
    for base_url in API_BASE_URLS:
        try:
            url = f"{base_url}{endpoint_path}"
            res = requests.get(url, params=params, headers=headers, timeout=6)
            if res.status_code == 200:
                data = res.json()
                if data:
                    return data
        except Exception:
            continue
    return None

def parse_song_item(item):
    # Stream URL Extraction
    stream_url = ""
    download_urls = item.get('downloadUrl') or item.get('download_url') or []
    if isinstance(download_urls, list) and len(download_urls) > 0:
        stream_url = download_urls[-1].get('url') if isinstance(download_urls[-1], dict) else download_urls[-1]

    # Image URL Extraction
    image_url = ""
    images = item.get('image') or []
    if isinstance(images, list) and len(images) > 0:
        image_url = images[-1].get('url') if isinstance(images[-1], dict) else images[-1]

    # Artist Name Extraction
    artists_data = item.get('artists', {})
    primary_artists = artists_data.get('primary', []) if isinstance(artists_data, dict) else []
    if primary_artists and isinstance(primary_artists, list):
        artist_names = ", ".join([a.get('name', '') for a in primary_artists if isinstance(a, dict)])
    else:
        artist_names = item.get('primaryArtists') or item.get('artist') or "Unknown Artist"

    return {
        "id": item.get('id', ''),
        "title": item.get('name') or item.get('title') or "Unknown Song",
        "artist": artist_names,
        "album": item.get('album', {}).get('name', '') if isinstance(item.get('album'), dict) else str(item.get('album', '')),
        "image": image_url,
        "stream_url": stream_url,
        "duration": item.get('duration', 0)
    }

@app.route('/search', methods=['GET'])
def search_songs():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"status": "error", "message": "Search query missing"}), 400

    data = fetch_jiosaavn("/search/songs", {"query": query, "limit": 30})
    
    if not data:
        return jsonify({"status": "error", "message": "All API endpoints are currently unreachable."}), 500

    songs = []
    results = []
    
    if isinstance(data, dict):
        data_content = data.get('data', {})
        if isinstance(data_content, dict):
            results = data_content.get('results', [])
        elif isinstance(data_content, list):
            results = data_content

    for item in results:
        parsed = parse_song_item(item)
        if parsed["stream_url"]:
            songs.append(parsed)

    return jsonify({"status": "success", "count": len(songs), "results": songs})

@app.route('/artist/top-hits', methods=['GET'])
def artist_top_hits():
    artist_name = request.args.get('name', 'Arijit Singh')
    
    data = fetch_jiosaavn("/search/songs", {"query": artist_name, "limit": 30})
    
    if not data:
        return jsonify({"status": "error", "message": "All API endpoints are currently unreachable."}), 500

    songs = []
    results = []
    
    if isinstance(data, dict):
        data_content = data.get('data', {})
        if isinstance(data_content, dict):
            results = data_content.get('results', [])
        elif isinstance(data_content, list):
            results = data_content

    for item in results:
        parsed = parse_song_item(item)
        if parsed["stream_url"]:
            songs.append(parsed)

    return jsonify({
        "status": "success",
        "artist": artist_name,
        "count": len(songs),
        "results": songs
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
