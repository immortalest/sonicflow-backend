from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import html
import re

app = Flask(__name__)
CORS(app)

# Vercel Hosted Edge Endpoints (Never blocked by JioSaavn/Cloudflare)
SEARCH_ENDPOINTS = [
    "https://jiosaavn-api-v3.vercel.app/search/songs",
    "https://jiosaavn-api-ts.vercel.app/search/songs",
    "https://jiosaavn-api-one.vercel.app/search/songs",
    "https://jiosaavn-api-core.vercel.app/search/songs",
    "https://saavn.me/search/songs",
    "https://saavn.me/api/search/songs",
    "https://jiosaavn-api.mubashir.my.id/search/songs"
]

def clean_text(text):
    if not text:
        return ''
    return html.unescape(re.sub(r'<[^>]+>', '', str(text)))

def parse_song_item(item):
    if not isinstance(item, dict):
        return None

    # Stream URL Extraction (320kbps / 128kbps HD Audio)
    stream_url = ""
    download_urls = item.get('downloadUrl') or item.get('download_url') or item.get('downloadUrls') or []
    if isinstance(download_urls, list) and len(download_urls) > 0:
        last_dl = download_urls[-1]
        if isinstance(last_dl, dict):
            stream_url = last_dl.get('url', '') or last_dl.get('link', '')
        else:
            stream_url = str(last_dl)
    elif isinstance(download_urls, str):
        stream_url = download_urls
    elif isinstance(item.get('media_url'), str):
        stream_url = item.get('media_url')

    if not stream_url:
        preview = item.get('media_preview_url') or (item.get('more_info', {}).get('media_preview_url') if isinstance(item.get('more_info'), dict) else "")
        if preview and 'saavncdn.com' in preview:
            stream_url = preview.replace('preview.saavncdn.com', 'aac.saavncdn.com').replace('_96_p.mp4', '_320.mp4').replace('_96_p.mp3', '_320.mp3')

    # Image URL Extraction
    image_url = ""
    images = item.get('image') or item.get('images') or []
    if isinstance(images, list) and len(images) > 0:
        last_img = images[-1]
        image_url = last_img.get('url', '') if isinstance(last_img, dict) else str(last_img)
    elif isinstance(images, str):
        image_url = images.replace('150x150', '500x500').replace('50x50', '500x500')

    # Artist Name Extraction
    artists_data = item.get('artists', {})
    primary_artists = artists_data.get('primary', []) if isinstance(artists_data, dict) else []
    if primary_artists and isinstance(primary_artists, list):
        artist_names = ", ".join([a.get('name', '') for a in primary_artists if isinstance(a, dict) and a.get('name')])
    else:
        artist_names = item.get('primaryArtists') or item.get('artist') or item.get('singers') or "Unknown Artist"

    title = clean_text(item.get('name') or item.get('title') or item.get('song') or "Unknown Song")

    album_name = ""
    album_data = item.get('album')
    if isinstance(album_data, dict):
        album_name = clean_text(album_data.get('name', ''))
    elif isinstance(album_data, str):
        album_name = clean_text(album_data)

    return {
        "id": str(item.get('id', '')),
        "title": title,
        "artist": clean_text(artist_names),
        "album": album_name,
        "image": image_url,
        "stream_url": stream_url,
        "duration": item.get('duration', 0)
    }

def fetch_from_endpoints(query):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*'
    }
    params = {'query': query, 'q': query, 'limit': 30}
    last_err = "No response"

    for url in SEARCH_ENDPOINTS:
        try:
            res = requests.get(url, params=params, headers=headers, timeout=6)
            if res.status_code == 200:
                data = res.json()
                if data:
                    songs = parse_jiosaavn_data(data)
                    if songs:
                        return songs, None
            else:
                last_err = f"HTTP {res.status_code}"
        except Exception as e:
            last_err = str(e)

    return None, last_err

def parse_jiosaavn_data(data):
    songs = []
    results = []
    
    if isinstance(data, dict):
        if 'data' in data:
            if isinstance(data['data'], dict) and 'results' in data['data']:
                results = data['data']['results']
            elif isinstance(data['data'], list):
                results = data['data']
        elif 'results' in data and isinstance(data['results'], list):
            results = data['results']
    elif isinstance(data, list):
        results = data

    for item in results:
        parsed = parse_song_item(item)
        if parsed and parsed["stream_url"]:
            songs.append(parsed)

    return songs

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "app": "SonicFlow Backend Engine v2",
        "message": "Server is running smoothly!"
    })

@app.route('/search', methods=['GET'])
def search_songs():
    query = request.args.get('q', '') or request.args.get('query', '')
    if not query:
        return jsonify({"status": "error", "message": "Search query missing"}), 400

    songs, err = fetch_from_endpoints(query)
    if songs:
        return jsonify({"status": "success", "count": len(songs), "results": songs})

    return jsonify({"status": "error", "message": f"Unable to fetch songs: {err}"}), 500

@app.route('/artist/top-hits', methods=['GET'])
def artist_top_hits():
    artist_name = request.args.get('name', 'Arijit Singh')
    
    songs, err = fetch_from_endpoints(artist_name)
    if songs:
        return jsonify({"status": "success", "artist": artist_name, "count": len(songs), "results": songs})

    return jsonify({"status": "error", "message": f"Unable to fetch artist songs: {err}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
