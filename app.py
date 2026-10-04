from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import base64
import time

app = Flask(__name__)
CORS(app)

# 🔑 Spotify Official Developer Credentials
SPOTIFY_CLIENT_ID = "c6241430aa814093a2225d492bd1552e"
SPOTIFY_CLIENT_SECRET = "1bf7c71c0c134dd3adae3d57d5484997"

spotify_token = ""
token_expires_at = 0

def get_spotify_token():
    global spotify_token, token_expires_at
    if spotify_token and time.time() < token_expires_at:
        return spotify_token

    url = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}

    try:
        res = requests.post(url, headers=headers, data=data, timeout=8)
        if res.status_code == 200:
            token_data = res.json()
            spotify_token = token_data.get("access_token")
            token_expires_at = time.time() + token_data.get("expires_in", 3600) - 60
            return spotify_token
    except Exception as e:
        print("Spotify Token Exception:", e)
    return None

def get_audio_stream_from_piped(query):
    piped_instances = [
        "https://pipedapi.kavin.rocks",
        "https://api.piped.video",
        "https://pipedapi.drgns.space",
        "https://pipedapi.mha.fi",
        "https://pipedapi.astrobot.me",
        "https://pipedapi.privacy.com.de"
    ]

    for base_url in piped_instances:
        try:
            search_url = f"{base_url}/search"
            res = requests.get(search_url, params={"q": query, "filter": "music_songs"}, timeout=4)
            if res.status_code == 200:
                items = res.json().get('items', [])
                if items and isinstance(items, list):
                    video_id = items[0].get('url', '').replace('/watch?v=', '')
                    if video_id:
                        stream_res = requests.get(f"{base_url}/streams/{video_id}", timeout=4)
                        if stream_res.status_code == 200:
                            audio_streams = stream_res.json().get('audioStreams', [])
                            if audio_streams:
                                return audio_streams[-1].get('url')
        except Exception:
            continue
    return ""

def fetch_itunes_fallback(query):
    try:
        url = "https://itunes.apple.com/search"
        params = {"term": query, "entity": "song", "limit": 25, "country": "IN"}
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, params=params, headers=headers, timeout=8)
        if res.status_code == 200:
            results = res.json().get("results", [])
            songs = []
            for item in results:
                title = item.get("trackName", "Unknown Song")
                artist = item.get("artistName", "Unknown Artist")
                image = item.get("artworkUrl100", "").replace("100x100bb.jpg", "600x600bb.jpg")
                preview_audio = item.get("previewUrl", "")
                
                # Try full audio stream via Piped, fallback to official iTunes HD Audio stream
                stream = get_audio_stream_from_piped(f"{title} {artist} audio") or preview_audio
                
                if stream:
                    songs.append({
                        "id": str(item.get("trackId", "")),
                        "title": title,
                        "artist": artist,
                        "album": item.get("collectionName", ""),
                        "image": image,
                        "stream_url": stream,
                        "duration": 30
                    })
            return songs
    except Exception as e:
        print("iTunes Fallback Exception:", e)
    return []

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "app": "SonicFlow Backend v2 (Spotify + iTunes Engine)",
        "message": "Spotify + iTunes Dual Engine is running smoothly!"
    })

@app.route('/search', methods=['GET'])
def search_songs():
    query = request.args.get('q', '') or request.args.get('query', '')
    if not query:
        return jsonify({"status": "error", "message": "Search query missing"}), 400

    # 1. Primary Engine: Spotify Official Web API
    token = get_spotify_token()
    if token:
        try:
            url = "https://api.spotify.com/v1/search"
            headers = {
                "Authorization": f"Bearer {token}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
            params = {"q": query, "type": "track", "limit": 20, "market": "IN"}
            
            res = requests.get(url, headers=headers, params=params, timeout=8)
            if res.status_code == 200:
                data = res.json()
                tracks = data.get('tracks', {}).get('items', [])
                songs = []
                for track in tracks:
                    title = track.get('name')
                    artists = ", ".join([a.get('name') for a in track.get('artists', []) if a.get('name')])
                    images = track.get('album', {}).get('images', [])
                    image = images[0].get('url') if images else ''
                    
                    stream_url = get_audio_stream_from_piped(f"{title} {artists} audio") or track.get('preview_url', '')

                    if stream_url:
                        songs.append({
                            "id": track.get('id'),
                            "title": title,
                            "artist": artists,
                            "album": track.get('album', {}).get('name'),
                            "image": image,
                            "stream_url": stream_url,
                            "duration": track.get('duration_ms', 0) // 1000
                        })
                if songs:
                    return jsonify({"status": "success", "source": "spotify", "count": len(songs), "results": songs})
        except Exception as e:
            print("Spotify Search Exception:", e)

    # 2. Universal Backup Engine: iTunes Official Engine
    itunes_songs = fetch_itunes_fallback(query)
    if itunes_songs:
        return jsonify({"status": "success", "source": "itunes", "count": len(itunes_songs), "results": itunes_songs})

    return jsonify({"status": "error", "message": "Unable to fetch songs right now. Please try again."}), 500

@app.route('/artist/top-hits', methods=['GET'])
def artist_top_hits():
    artist_name = request.args.get('name', 'Arijit Singh')
    return search_songs()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
