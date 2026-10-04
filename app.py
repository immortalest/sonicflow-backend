from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import html
import re

app = Flask(__name__)
CORS(app)

def clean_text(text):
    if not text:
        return ''
    return html.unescape(re.sub(r'<[^>]+>', '', str(text)))

def get_full_stream_url(item):
    if not isinstance(item, dict):
        return ""
    
    more_info = item.get('more_info', {}) if isinstance(item.get('more_info'), dict) else {}
    
    # 1. Direct Preview URL to Full-Length 320kbps HD Audio Link
    preview = item.get('media_preview_url') or more_info.get('media_preview_url') or ""
    if preview and 'saavncdn.com' in preview:
        url = preview.replace('preview.saavncdn.com', 'aac.saavncdn.com')
        url = url.replace('_96_p.mp4', '_320.mp4').replace('_96_p.mp3', '_320.mp3')
        url = url.replace('_96_p', '_320.mp4')
        return url

    # 2. Download URL Array (Full Songs)
    dl = item.get('downloadUrl') or item.get('download_url') or item.get('downloadUrls') or []
    if isinstance(dl, list) and len(dl) > 0:
        last = dl[-1]
        return last.get('url', '') if isinstance(last, dict) else str(last)
    elif isinstance(dl, str) and dl.startswith('http'):
        return dl

    # 3. Direct Media URL
    media_url = item.get('media_url') or more_info.get('media_url')
    if isinstance(media_url, str) and media_url.startswith('http'):
        return media_url

    return ""

def parse_song_item(item):
    if not isinstance(item, dict):
        return None

    stream_url = get_full_stream_url(item)
    if not stream_url:
        return None

    more_info = item.get('more_info', {}) if isinstance(item.get('more_info'), dict) else {}

    # Title Extraction
    title = clean_text(item.get('title') or item.get('name') or item.get('song') or "Unknown Song")

    # HD Image Extraction (500x500)
    image_url = ""
    images = item.get('image') or item.get('images') or []
    if isinstance(images, list) and len(images) > 0:
        last_img = images[-1]
        image_url = last_img.get('url', '') if isinstance(last_img, dict) else str(last_img)
    elif isinstance(images, str):
        image_url = images.replace('150x150', '500x500').replace('50x50', '500x500')

    # Artist Extraction
    artist = ""
    if 'artistMap' in more_info and isinstance(more_info['artistMap'], dict):
        prim = more_info['artistMap'].get('primary_artists', [])
        if prim and isinstance(prim, list):
            artist = ", ".join([a.get('name', '') for a in prim if isinstance(a, dict) and a.get('name')])
    if not artist:
        artists_data = item.get('artists', {})
        prim = artists_data.get('primary', []) if isinstance(artists_data, dict) else []
        if prim and isinstance(prim, list):
            artist = ", ".join([a.get('name', '') for a in prim if isinstance(a, dict) and a.get('name')])
    if not artist:
        artist = item.get('primaryArtists') or item.get('artist') or item.get('singers') or item.get('subtitle') or "Unknown Artist"

    album_name = clean_text(more_info.get('album') or (item.get('album', {}).get('name', '') if isinstance(item.get('album'), dict) else str(item.get('album', ''))))

    duration = item.get('duration', 0) or more_info.get('duration', 0)
    try:
        duration = int(duration)
    except Exception:
        duration = 0

    return {
        "id": str(item.get('id', '')),
        "title": title,
        "artist": clean_text(artist),
        "album": album_name,
        "image": image_url,
        "stream_url": stream_url,
        "duration": duration
    }

def fetch_full_songs_jiosaavn(query):
    # Android Mobile Headers (Never blocked by Cloudflare)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        'Accept': 'application/json, text/plain, */*'
    }
    cookies = {
        'L': 'hindi,english,punjabi,telugu,tamil',
        'gdpr_acceptance': 'true'
    }

    # Method 1: JioSaavn Android API (search.getResults)
    try:
        url = "https://www.jiosaavn.com/api.php"
        params = {
            '__call': 'search.getResults',
            '_format': 'json',
            '_marker': '0',
            'api_version': '4',
            'ctx': 'android',
            'q': query,
            'p': '1',
            'n': '40'
        }
        res = requests.get(url, params=params, headers=headers, cookies=cookies, timeout=8)
        if res.status_code == 200:
            data = res.json()
            results = data.get('results', [])
            songs = [parse_song_item(item) for item in results if parse_song_item(item)]
            if songs:
                return songs
    except Exception:
        pass

    # Method 2: JioSaavn Android API (autocomplete.get)
    try:
        url = "https://www.jiosaavn.com/api.php"
        params = {
            '__call': 'autocomplete.get',
            '_format': 'json',
            '_marker': '0',
            'api_version': '4',
            'ctx': 'android',
            'query': query
        }
        res = requests.get(url, params=params, headers=headers, cookies=cookies, timeout=8)
        if res.status_code == 200:
            data = res.json()
            songs_data = data.get('songs', {}).get('data', []) if isinstance(data.get('songs'), dict) else []
            songs = [parse_song_item(item) for item in songs_data if parse_song_item(item)]
            if songs:
                return songs
    except Exception:
        pass

    return []

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "app": "SonicFlow Backend Engine v2 (Full-Length HD Engine)",
        "message": "Full Length 320kbps HD Audio Engine is running!"
    })

@app.route('/search', methods=['GET'])
def search_songs():
    query = request.args.get('q', '') or request.args.get('query', '')
    if not query:
        return jsonify({"status": "error", "message": "Search query missing"}), 400

    songs = fetch_full_songs_jiosaavn(query)
    if songs:
        return jsonify({"status": "success", "count": len(songs), "results": songs})

    return jsonify({"status": "error", "message": "No full-length songs found for your query."}), 404

@app.route('/artist/top-hits', methods=['GET'])
def artist_top_hits():
    artist_name = request.args.get('name', 'Arijit Singh')
    songs = fetch_full_songs_jiosaavn(artist_name)
    if songs:
        return jsonify({"status": "success", "artist": artist_name, "count": len(songs), "results": songs})

    return jsonify({"status": "error", "message": f"Unable to fetch full-length songs for {artist_name}"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
