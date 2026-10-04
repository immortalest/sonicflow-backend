from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # Mobile App Connection Fix

JIOSAAVN_API_BASE = "https://saavn.dev/api"

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "app": "SonicFlow Backend Engine v2",
        "message": "Server is running smoothly!"
    })

@app.route('/search', methods=['GET'])
def search_songs():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"status": "error", "message": "Search query missing"}), 400

    try:
        url = f"{JIOSAAVN_API_BASE}/search/songs?query={query}&limit=25"
        res = requests.get(url, timeout=10)
        data = res.json()

        songs = []
        if data.get('success') and 'data' in data and 'results' in data['data']:
            for item in data['data']['results']:
                # Extract highest audio quality URL (320kbps / 128kbps)
                download_urls = item.get('downloadUrl', [])
                stream_url = download_urls[-1].get('url', '') if download_urls else ''

                # Extract cover image
                images = item.get('image', [])
                image_url = images[-1].get('url', '') if images else ''

                # Extract artists
                artists = item.get('artists', {}).get('primary', [])
                artist_names = ", ".join([a.get('name', '') for a in artists]) if artists else item.get('artist', '')

                songs.append({
                    "id": item.get('id'),
                    "title": item.get('name'),
                    "artist": artist_names,
                    "album": item.get('album', {}).get('name', ''),
                    "image": image_url,
                    "stream_url": stream_url,
                    "duration": item.get('duration', 0)
                })

        return jsonify({"status": "success", "count": len(songs), "results": songs})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/artist/top-hits', methods=['GET'])
def artist_top_hits():
    artist_name = request.args.get('name', 'Arijit Singh')
    try:
        url = f"{JIOSAAVN_API_BASE}/search/songs?query={artist_name}&limit=30"
        res = requests.get(url, timeout=10)
        data = res.json()

        songs = []
        if data.get('success') and 'data' in data and 'results' in data['data']:
            for item in data['data']['results']:
                download_urls = item.get('downloadUrl', [])
                stream_url = download_urls[-1].get('url', '') if download_urls else ''

                images = item.get('image', [])
                image_url = images[-1].get('url', '') if images else ''

                artists = item.get('artists', {}).get('primary', [])
                artist_names = ", ".join([a.get('name', '') for a in artists]) if artists else item.get('artist', '')

                songs.append({
                    "id": item.get('id'),
                    "title": item.get('name'),
                    "artist": artist_names,
                    "album": item.get('album', {}).get('name', ''),
                    "image": image_url,
                    "stream_url": stream_url,
                    "duration": item.get('duration', 0)
                })

        return jsonify({
            "status": "success",
            "artist": artist_name,
            "count": len(songs),
            "results": songs
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
