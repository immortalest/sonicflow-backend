from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import html
import re
import base64
from Crypto.Cipher import DES

app = Flask(__name__)
CORS(app)

def clean_text(text):
    if not text:
        return ''
    return html.unescape(re.sub(r'<[^>]+>', '', str(text)))

def decrypt_url(cipher_text):
    try:
        if not cipher_text:
            return ""
        key = b'38588582'
        cipher = DES.new(key, DES.MODE_ECB)
        decrypted = cipher.decrypt(base64.b64decode(cipher_text)).decode('utf-8')
        
        p = decrypted.rfind('http')
        if p != -1:
            decrypted = decrypted[p:]
            
        for ext in ['.mp4', '.mp3', '.m4a']:
            pos = decrypted.find(ext)
            if pos != -1:
                decrypted = decrypted[:pos + len(ext)]
                break
                
        decrypted = decrypted.replace('_96.', '_320.').replace('_128.', '_320.')
        if not decrypted.startswith('http'):
            decrypted = 'https://' + decrypted.lstrip('/')
        return decrypted
    except Exception:
        return ""

def get_stream_url(item):
    more_info = item.get('more_info', {}) if isinstance(item.get('more_info'), dict) else {}
    
    # 1. Try decrypting encrypted_media_url
    enc_url = more_info.get('encrypted_media_url') or item.get('encrypted_media_url')
    if enc_url:
        dec = decrypt_url(enc_url)
        if dec and 'saavncdn' in dec:
            return dec
            
    # 2. Try media_preview_url to direct HD audio transformation
    preview = item.get('media_preview_url') or more_info.get('media_preview_url')
    if preview:
        return preview.replace('preview.saavncdn.com', 'aac.saavncdn.com').replace('_96_p.mp4', '_320.mp4').replace('_96_p.mp3', '_320.mp3')
        
    # 3. Try downloadUrl
    download_urls = item.get('downloadUrl') or item.get('download_url')
    if isinstance(download_urls, list) and len(download_urls) > 0:
        last = download_urls[-1]
        return last.get('url') if isinstance(last, dict) else str(last)
        
    return ""

def parse_jiosaavn_data(data):
    songs = []
    results = []
    
    if isinstance(data, dict):
        if 'results' in data:
            results = data['results']
        elif 'data' in data:
            if isinstance(data['data'], dict) and 'results' in data['data']:
                results = data['data']['results']
            elif isinstance(data['data'], list):
                results = data['data']
    elif isinstance(data, list):
        results = data

    for item in results:
        if not isinstance(item, dict):
            continue
            
        more_info = item.get('more_info', {}) if isinstance(item.get('more_info'), dict) else {}
        
        title = clean_text(item.get('title') or item.get('song') or item.get('name') or 'Unknown Song')
        
        # Extract artist names
        artist = ""
        if 'artistMap' in more_info and isinstance(more_info['artistMap'], dict):
            primary = more_info['artistMap'].get('primary_artists', [])
            if primary and isinstance(primary, list):
                artist = ", ".join([a.get('name', '') for a in primary if isinstance(a, dict)])
        if not artist:
            artist = clean_text(item.get('primary_artists') or item.get('singers') or item.get('subtitle') or item.get('artist') or 'Unknown Artist')
            
        # Extract HD cover image
        image_url = item.get('image', '')
        if isinstance(image_url, list) and len(image_url) > 0:
            image_url = image_url[-1].get('url') if isinstance(image_url[-1], dict) else str(image_url[-1])
        elif isinstance(image_url, str):
            image_url = image_url.replace('150x150', '500x500').replace('50x50', '500x500').replace('http://', 'https://')
            
        stream_url = get_stream_url(item)
        
        if stream_url:
            songs.append({
                "id": str(item.get('id', '')),
                "title": title,
                "artist": artist,
                "album": clean_text(more_info.get('album') or (item.get('album', {}).get('name', '') if isinstance(item.get('album'), dict) else str(item.get('album', '')))),
                "image": image_url,
                "stream_url": stream_url,
                "duration": item.get('duration', 0) or more_info.get('duration', 0)
            })
            
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
    query = request.args.get('q', '')
    if not query:
        return jsonify({"status": "error", "message": "Search query missing"}), 400

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # Direct JioSaavn Official Engine
    try:
        jio_url = "https://www.jiosaavn.com/api.php"
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
        res = requests.get(jio_url, params=params, headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            songs = parse_jiosaavn_data(data)
            if songs:
                return jsonify({"status": "success", "count": len(songs), "results": songs})
    except Exception:
        pass

    return jsonify({"status": "error", "message": "Unable to fetch songs right now. Please try again."}), 500

@app.route('/artist/top-hits', methods=['GET'])
def artist_top_hits():
    artist_name = request.args.get('name', 'Arijit Singh')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        jio_url = "https://www.jiosaavn.com/api.php"
        params = {
            '__call': 'search.getResults',
            '_format': 'json',
            '_marker': '0',
            'api_version': '4',
            'ctx': 'web6dot0',
            'q': artist_name,
            'p': '1',
            'n': '30'
        }
        res = requests.get(jio_url, params=params, headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            songs = parse_jiosaavn_data(data)
            if songs:
                return jsonify({"status": "success", "artist": artist_name, "count": len(songs), "results": songs})
    except Exception:
        pass

    return jsonify({"status": "error", "message": "Unable to fetch artist songs."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
