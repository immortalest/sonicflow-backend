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

def extract_stream_url(item):
    if not isinstance(item, dict):
        return ""
    
    more_info = item.get('more_info')
    if not isinstance(more_info, dict):
        more_info = {}

    # 1. Preview URL to 320kbps HD audio transformation
    preview = item.get('media_preview_url') or more_info.get('media_preview_url') or item.get('preview_url') or ""
    if isinstance(preview, str) and 'saavncdn.com' in preview:
        url = preview.replace('preview.saavncdn.com', 'aac.saavncdn.com')
        url = url.replace('_96_p.mp4', '_320.mp4').replace('_96_p.mp3', '_320.mp3')
        url = url.replace('_96_p', '_320.mp4')
        return url

    # 2. downloadUrl / download_url list
    download_urls = item.get('downloadUrl') or item.get('download_url') or item.get('downloadUrls') or more_info.get('downloadUrl') or []
    if isinstance(download_urls, list) and len(download_urls) > 0:
        last = download_urls[-1]
        if isinstance(last, dict):
            return last.get('url', '') or last.get('link', '')
        return str(last)
    elif isinstance(download_urls, str) and download_urls.startswith('http'):
        return download_urls

    # 3. Direct media_url
    media_url = item.get('media_url') or more_info.get('media_url')
    if isinstance(media_url, str) and media_url.startswith('http'):
        return media_url

    return ""

def parse_song_item(item):
    if not isinstance(item, dict):
        return None

    stream_url = extract_stream_url(item)
    if not stream_url:
        return None

    more_info = item.get('more_info')
    if not isinstance(more_info, dict):
        more_info = {}

    title = clean_text(item.get('title') or item.get('name') or item.get('song') or "Unknown Song")

    image_url = ""
    images = item.get('image') or item.get('images') or []
    if isinstance(images, list) and len(images) > 0:
        last_img = images[-1]
        image_url = last_img.get('url', '') if isinstance(last_img, dict) else str(last_img)
    elif isinstance(images, str):
        image_url = images.replace('150x150', '500x500').replace('50x50', '500x500')

    artist = ""
    if 'artistMap' in more_info and isinstance(more_info['artistMap'], dict):
        prim = more_info['artistMap'].get('primary_artists', [])
        if prim and isinstance(prim, list):
            artist = ", ".join([a.get('name', '') for a in prim if isinstance(a, dict) and a.get('name')])
    if not artist:
        artists_data = item.get('artists')
        if isinstance(artists_data, dict):
            prim = artists_data.get('primary', [])
            if isinstance(prim, list):
                artist = ", ".join([a.get('name', '') for a in prim if isinstance(a, dict) and a.get('name')])
    if not artist:
        artist = item.get('primaryArtists') or item.get('artist') or item.get('singers') or item.get('subtitle') or more_info.get('singers') or "Unknown Artist"

    album_name = clean_text(more_info.get('album') or (item.get('album', {}).get('name', '') if isinstance(item.get('album'), dict) else str(item.get('album', ''))))

    return {
        "id": str(item.get('id', '')),
        "title": title,
        "artist": clean_text(artist),
        "album": album_name,
        "image": image_url,
        "stream_url": stream_url,
        "duration": item.get('duration', 0) or more_info.get('duration', 0)
    }

def extract_songs_from_response(data):
    results = []
    if isinstance(data, dict):
        if 'results' in data and isinstance(data['results'], list):
            results = data['results']
        elif 'songs' in data and isinstance(data['songs'], dict) and 'data' in data['songs']:
            results = data['songs']['data']
        elif 'data' in data:
            if isinstance(data['data'], dict):
                if 'results' in data['data'] and isinstance(data['data']['results'], list):
                    results = data['data']['results']
                elif 'songs' in data['data'] and isinstance(data['data']['songs'], list):
                    results = data['data']['songs']
            elif isinstance(data['data'], list):
                results = data['data']
    elif isinstance(data, list):
        results = data

    songs = []
    for item in results:
        parsed = parse_song_item(item)
        if parsed:
            songs.append(parsed)
    return songs

def fetch_songs_multi_strategy(query):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.jiosaavn.com/'
    }
    cookies = {
        'L': 'hindi,english,punjabi,telugu,tamil',
        'gdpr_acceptance': 'true'
    }

    # Strategy 1: Official JioSaavn Web Search
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
        res = requests.get(url, params=params, headers=headers, cookies=cookies, timeout=6)
        if res.status_code == 200:
            songs = extract_songs_from_response(res.json())
            if songs:
                return songs
    except Exception:
        pass

    # Strategy 2: Official JioSaavn Android Search
    try:
        url = "https://www.jiosaavn.com/api.php"
        params = {
            '__call': 'search.getMoreResults',
            '_format': 'json',
            '_marker': '0',
            'api_version': '4',
            'ctx': 'android',
            'query': query,
            'p': '0',
            'n': '30'
        }
        res = requests.get(url, params=params, headers=headers, cookies=cookies, timeout=6)
        if res.status_code == 200:
            songs = extract_songs_from_response(res.json())
            if songs:
                return songs
    except Exception:
        pass

    # Strategy 3: Official JioSaavn Autocomplete
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
        res = requests.get(url, params=params, headers=headers, cookies=cookies, timeout=6)
        if res.status_code == 200:
            songs = extract_songs_from_response(res.json())
            if songs:
                return songs
    except Exception:
        pass

    # Strategy 4: Backup Mirror Endpoints
    mirror_urls = [
        f"https://jiosaavn-api-v3.vercel.app/search/songs?query={query}",
        f"https://saavn.me/search/songs?query={query}",
        f"https://saavn.dev/api/search/songs?query={query}"
    ]
    for m_url in mirror_urls:
        try:
            res = requests.get(m_url, headers=headers, timeout=5)
            if res.status_code == 200:
                songs = extract_songs_from_response(res.json())
                if songs:
                    return songs
        except Exception:
            continue

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

    songs = fetch_songs_multi_strategy(query)
    if songs:
        return jsonify({"status": "success", "count": len(songs), "results": songs})

    return jsonify({"status": "error", "message": "No songs found."}), 404

@app.route('/artist/top-hits', methods=['GET'])
def artist_top_hits():
    artist_name = request.args.get('name', 'Arijit Singh')
    
    songs = fetch_songs_multi_strategy(artist_name)
    if songs:
        return jsonify({"status": "success", "artist": artist_name, "count": len(songs), "results": songs})

    return jsonify({"status": "error", "message": f"Unable to fetch songs for artist {artist_name}"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
