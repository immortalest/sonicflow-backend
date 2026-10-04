from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# All tested & working JioSaavn API endpoints
SEARCH_ENDPOINTS = [
    "https://saavn.dev/api/search/songs",
    "https://saavn.me/api/search/songs",
    "https://saavn.me/search/songs",
    "https://jiosaavn-api-v3.vercel.app/search/songs",
    "https://jiosaavn-api-v3.vercel.app/api/search/songs"
]

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "app": "SonicFlow Backend Engine v2",
        "message": "Server is running smoothly!"
    })

def fetch_from_endpoints(params):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    for url in SEARCH_ENDPOINTS:
        try:
            # 10-second timeout for Render network latency
            res = requests.get(url, params=params, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data and (data.get('success') == True or data.get('status') == 'SUCCESS' or 'data' in data or 'results' in data):
                    return data
        except Exception:
            continue
    return None

def parse_song_item(item):
    if not isinstance(item, dict):
        return None

    # Stream URL Extraction (High Quality 320kbps / 128kbps)
    stream_url = ""
    download_urls = item.get('downloadUrl') or item.get('download_url') or []
    if isinstance(download_urls, list) and len(download_urls) > 0:
        last_dl = download_urls[-1]
        stream_url = last_dl.get('url') if isinstance(last_dl, dict) else str(last_dl)
    elif isinstance(download_urls, str):
        stream_url = download_urls

    # Image URL Extraction
    image_url = ""
    images = item.get('image') or []
    if isinstance(images, list) and len(images) > 0:
        last_img = images[-1]
        image_url = last_img.get('url') if isinstance(last_img, dict) else str(last_img)
    elif isinstance(images, str):
        image_url = images

    # Artist Name Extraction
    artists_data = item.get('artists', {})
    primary_artists = artists_data.get('primary', []) if isinstance(artists_data, dict) else []
    if primary_artists and isinstance(primary_artists, list):
        artist_names = ", ".join([a.get('name', '') for a in primary_artists if isinstance(a, dict) and a.get('name')])
    else:
        artist_names = item.get('primaryArtists') or item.get('artist') or "Unknown Artist"

    title = item.get('name') or item.get('title') or "Unknown Song"

    return {
        "id": str(item.get('id', '')),
        "title": title,
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

    data = fetch_from_endpoints({"query": query, "limit": 30})
    
    if not data:
        return jsonify({"status": "error", "message": "API endpoints currently unreachable. Please try again."}), 500

    songs = []
    results = []
    
    # Universal JSON response parser
    if isinstance(data, dict):
        if 'data' in data:
            if isinstance(data['data'], dict) and 'results' in data['data']:
                results = data['data']['results']
            elif isinstance(data['data'], list):
                results = data['data']
        elif 'results' in data:
            results = data['results']
    elif isinstance(data, list):
        results = data

    for item in results:
        parsed = parse_song_item(item)
        if parsed and parsed["stream_url"]:
            songs.append(parsed)

    return jsonify({"status": "success", "count": len(songs), "results": songs})

@app.route('/artist/top-hits', methods=['GET'])
def artist_top_hits():
    artist_name = request.args.get('name', 'Arijit Singh')
    
    data = fetch_from_endpoints({"query": artist_name, "limit": 30})
    
    if not data:
        return jsonify({"status": "error", "message": "API endpoints currently unreachable. Please try again."}), 500

    songs = []
    results = []
    
    if isinstance(data, dict):
        if 'data' in data:
            if isinstance(data['data'], dict) and 'results' in data['data']:
                results = data['data']['results']
            elif isinstance(data['data'], list):
                results = data['data']
        elif 'results' in data:
            results = data['results']
    elif isinstance(data, list):
        results = data

    for item in results:
        parsed = parse_song_item(item)
        if parsed and parsed["stream_url"]:
            songs.append(parsed)

    return jsonify({
        "status": "success",
        "artist": artist_name,
        "count": len(songs),
        "results": songs
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
