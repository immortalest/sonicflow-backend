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

def parse_song_item(item):
    if not isinstance(item, dict):
        return None

    # Stream URL Extraction (High Quality 320kbps Audio)
    stream_url = ""
    more_info = item.get('more_info', {}) if isinstance(item.get('more_info'), dict) else {}
    
    preview = item.get('media_preview_url') or more_info.get('media_preview_url') or ""
    if preview and 'saavncdn.com' in preview:
        stream_url = preview.replace('preview.saavncdn.com', 'aac.saavncdn.com').replace('_96_p.mp4', '_320.mp4').replace('_96_p.mp3', '_320.mp3')

    if not stream_url:
        dl = item.get('downloadUrl') or item.get('download_url') or item.get('downloadUrls') or []
        if isinstance(dl, list) and len(dl) > 0:
            last = dl[-1]
            stream_url = last.get('url', '') if isinstance(last, dict) else str(last)
        elif isinstance(dl, str):
            stream_url = dl

    if not stream_url and isinstance(item.get('media_url'), str):
        stream_url = item.get('media_url')

    if not stream_url:
        return None

    # Image Extraction
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

    title = clean_text(item.get('name') or item.get('title') or item.get('song') or "Unknown Song")
    album_name = clean_text(more_info.get('album') or (item.get('album', {}).get('name', '') if isinstance(item.get('album'), dict) else str(item.get('album', ''))))

    return {
        "id": str(item.get('id', '')),
        "title": title,
        "artist": clean_text(artist),
        "album": album_name,
        "image": image_url,
        "stream_url": stream_url,
        "duration": item.get('duration', 0)
    }

def fetch_jiosaavn_songs(query):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://www.jiosaavn.com/'
    }
    
    # Language Cookie Fix (JioSaavn requires language cookies to return tracks)
    cookies = {
        'L': 'hindi,english,punjabi,telugu,tamil',
        'gdpr_acceptance': 'true'
    }

    # 1. Primary Method: Official JioSaavn search.getResults
    try:
        url = "https://www.jiosaavn.com/api.php"
        params = {
            '__call': 'search.getResults',
            '_format': 'json',
            '_marker': '0',
            'api_version': '4',
            'ctx': 'web6dot0',
            'q': query,
            'p': '1',
            'n': '30'
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

    # 2. Secondary Method: Official JioSaavn autocomplete.get
    try:
        url = "https://www.jiosaavn.com/api.php"
        params = {
            '__call': 'autocomplete.get',
            '_format': 'json',
            '_marker': '0',
            'api_version': '4',
            'ctx': 'web6dot0',
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
        "app": "SonicFlow Backend Engine v2",
        "message": "Server is running smoothly!"
    })

@app.route('/search', methods=['GET'])
def search_songs():
    query = request.args.get('q', '') or request.args.get('query', '')
    if not query:
        return jsonify({"status": "error", "message": "Search query missing"}), 400

    songs = fetch_jiosaavn_songs(query)
    if songs:
        return jsonify({"status": "success", "count": len(songs), "results": songs})

    return jsonify({"status": "error", "message": "No songs found for your query. Please try another search term."}), 404

@app.route('/artist/top-hits', methods=['GET'])
def artist_top_hits():
    artist_name = request.args.get('name', 'Arijit Singh')
    
    songs = fetch_jiosaavn_songs(artist_name)
    if songs:
        return jsonify({"status": "success", "artist": artist_name, "count": len(songs), "results": songs})

    return jsonify({"status": "error", "message": f"Unable to fetch songs for artist {artist_name}"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
