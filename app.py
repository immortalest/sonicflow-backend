from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import requests
import json
import re

app = Flask(__name__)
CORS(app)

# Initialize YouTube Music Engine
try:
    from ytmusicapi import YTMusic
    ytmusic = YTMusic()
except Exception:
    ytmusic = None

PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://api.piped.video",
    "https://pipedapi.drgns.space",
    "https://pipedapi.mha.fi",
    "https://pipedapi.astrobot.me",
    "https://pipedapi.privacy.com.de"
]

def get_direct_https_stream(video_id):
    # Fetch fresh direct HTTPS audio stream link on-demand
    for base_url in PIPED_INSTANCES:
        try:
            url = f"{base_url}/streams/{video_id}"
            res = requests.get(url, timeout=4)
            if res.status_code == 200:
                audio_streams = res.json().get('audioStreams', [])
                if audio_streams and isinstance(audio_streams, list):
                    stream_url = audio_streams[-1].get('url', '')
                    if stream_url and stream_url.startswith('http:'):
                        stream_url = stream_url.replace('http:', 'https:', 1)
                    if stream_url:
                        return stream_url
        except Exception:
            continue
            
    # Fallback HTTPS node
    return f"https://invidious.nerdvpn.de/latest_version?id={video_id}&itag=140"

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "app": "SonicFlow Backend Engine v2 (HTTPS On-Demand Stream)",
        "message": "Full-Length HTTPS Audio Engine is running smoothly!"
    })

@app.route('/stream')
def stream_audio():
    video_id = request.args.get('id', '') or request.args.get('video_id', '')
    if not video_id:
        return jsonify({"status": "error", "message": "Video ID missing"}), 400
        
    stream_url = get_direct_https_stream(video_id)
    return redirect(stream_url, code=302)

def search_ytmusic(query):
    songs = []
    if ytmusic:
        try:
            results = ytmusic.search(query, filter="songs", limit=25)
            host_url = request.host_url.rstrip('/')
            
            for item in results:
                vid = item.get("videoId")
                if not vid:
                    continue
                title = item.get("title", "Unknown Song")
                artists = item.get("artists", [])
                artist_name = ", ".join([a.get("name", "") for a in artists if isinstance(a, dict) and a.get("name")]) if isinstance(artists, list) else "Unknown Artist"
                
                album = item.get("album", {})
                album_name = album.get("name", "") if isinstance(album, dict) else str(album or "")
                
                thumbnails = item.get("thumbnails", [])
                image_url = ""
                if isinstance(thumbnails, list) and len(thumbnails) > 0:
                    image_url = thumbnails[-1].get("url", "")
                    image_url = re.sub(r'=w\d+-h\d+', '=w500-h500', image_url)
                if image_url.startswith('http:'):
                    image_url = image_url.replace('http:', 'https:', 1)

                duration = item.get("duration_seconds") or 0
                
                # Stream Link generated dynamically on-demand
                stream_link = f"{host_url}/stream?id={vid}"
                
                songs.append({
                    "id": vid,
                    "title": title,
                    "artist": artist_name,
                    "album": album_name,
                    "image": image_url,
                    "stream_url": stream_link,
                    "duration": duration
                })
        except Exception as e:
            print("ytmusic search error:", e)
    return songs

@app.route('/search', methods=['GET'])
def search_songs():
    query = request.args.get('q', '') or request.args.get('query', '')
    if not query:
        return jsonify({"status": "error", "message": "Search query missing"}), 400

    songs = search_ytmusic(query)
    if songs:
        return jsonify({"status": "success", "count": len(songs), "results": songs})

    return jsonify({"status": "error", "message": "No songs found for your query."}), 404

@app.route('/artist/top-hits', methods=['GET'])
def artist_top_hits():
    artist_name = request.args.get('name', '') or request.args.get('q', '') or request.args.get('query', '') or 'Arijit Singh'
    return search_songs()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
