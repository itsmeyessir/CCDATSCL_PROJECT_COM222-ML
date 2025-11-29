import pandas as pd
import pylast
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import os
import subprocess 
from dotenv import load_dotenv
from datetime import datetime

# --- CONFIGURATION ---
if os.path.exists("../.env"):
    load_dotenv("../.env")
else:
    load_dotenv()

LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_USERNAME = os.getenv("LASTFM_USERNAME")
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")

# 🎵 PASTE YOUR PLAYLIST LINK HERE:
TARGET_PLAYLIST_URL = "https://open.spotify.com/playlist/0vvXsWCC9xrXsKd4FyS8kM?si=75767aa8d15e477a" 

# DIRECTORY SETUP
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "music_data.csv")
CACHE_PATH = os.path.join(BASE_DIR, ".cache") 

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

POLL_INTERVAL = 1200 
# Create a 20-minute buffer to catch current songs or late scrobbles
SCRIPT_START_TIME = int(time.time()) - 1200

def open_spotify_and_play(sp):
    print("🚀 Launching Spotify App...")
    try:
        # 1. Open the App
        subprocess.call(["open", "-a", "Spotify"])
        time.sleep(4) # Wait for UI to load
        
        # 2. THE FIX: Force 'Wake Up' via Mac System Command
        # This presses "Play" locally on your Mac, which forces the device to become "Active"
        print("   (Waking up local player...)")
        subprocess.call(["osascript", "-e", 'tell application "Spotify" to play'])
        time.sleep(2) # Wait for Spotify Server to realize we are active

        # 3. Now send the Playlist Command via API
        print(f"▶️ Switching to Target Playlist...")
        # Get active device now that we woke it up
        devices = sp.devices()
        if devices['devices']:
            device_id = devices['devices'][0]['id']
            sp.start_playback(device_id=device_id, context_uri=TARGET_PLAYLIST_URL)
            print("✅ Music started!")
        else:
            print("⚠️ App is open but API still can't see it. Please press Play manually!")
        
    except Exception as e:
        print(f"⚠️ Auto-play glitch: {e}")
        print("   (Just press Play on Spotify manually, the tracker will still work!)")

def get_existing_timestamps():
    if not os.path.exists(DATA_FILE):
        return set()
    try:
        df = pd.read_csv(DATA_FILE)
        return set(df['timestamp'].astype(str))
    except:
        return set()

def fetch_music_data(sp, network, user):
    print(f"⏰ Awake! Fetching data at {datetime.now().strftime('%H:%M:%S')}...")

    try:
        recent_tracks = user.get_recent_tracks(limit=50) # Limit 50 is enough for debugging
    except Exception as e:
        print(f"❌ Last.fm Error: {e}")
        return

    existing_timestamps = get_existing_timestamps()
    new_data = []
    artist_cache = {} 

    print(f"   (Filtering tracks played after Unix Time: {SCRIPT_START_TIME})")

    for item in reversed(recent_tracks):
        try:
            track = item.track
            
            # SAFE TIMESTAMP HANDLING
            if item.playback_date:
                try:
                    # Handle string or datetime object
                    if isinstance(item.playback_date, str):
                        dt_obj = datetime.strptime(item.playback_date, "%d %b %Y, %H:%M")
                        track_unix_time = int(dt_obj.timestamp())
                    else:
                        track_unix_time = int(item.playback_date.timestamp())
                except Exception as e:
                    track_unix_time = int(time.time()) 
            else:
                # "Now Playing" gets current time
                track_unix_time = int(time.time())

            # --- DEBUGGING PRINT ---
            # This will show you exactly what it finds and if it skips it
            # print(f"   Found: {track.title} at {track_unix_time}...", end=" ")

            # START FRESH FILTER
            if track_unix_time < SCRIPT_START_TIME:
                # print("Skipped (Too Old)")
                continue 
            
            if str(item.playback_date) in existing_timestamps:
                # print("Skipped (Duplicate)")
                continue

            # print("KEEPING! ✅")

            # --- METADATA FETCHING ---
            artist_name = track.artist.name
            title = track.title
            timestamp = str(item.playback_date) 
            
            genres = "Unknown"
            popularity = 0
            
            if artist_name in artist_cache:
                genres = artist_cache[artist_name]['genres']
                popularity = artist_cache[artist_name]['popularity']
            else:
                q = f"track:{title} artist:{artist_name}"
                results = sp.search(q=q, limit=1, type='track')
                
                if results['tracks']['items']:
                    track_item = results['tracks']['items'][0]
                    main_artist_id = track_item['artists'][0]['id']
                    artist_details = sp.artist(main_artist_id)
                    if artist_details['genres']:
                        genres = ", ".join(artist_details['genres'])
                    popularity = artist_details['popularity']
                
                if genres == "Unknown":
                    try:
                        lfm_artist = network.get_artist(artist_name)
                        top_tags = lfm_artist.get_top_tags(limit=5)
                        if top_tags:
                            tag_list = [tag.item.name.lower() for tag in top_tags]
                            genres = ", ".join(tag_list)
                    except:
                        pass

                artist_cache[artist_name] = {'genres': genres, 'popularity': popularity}

            new_data.append({
                'timestamp': timestamp,
                'artist': artist_name,
                'title': title,
                'genres': genres,
                'popularity': popularity
            })
            print(f"   -> New Track: {title} [{genres[:15]}...]")

        except Exception as e:
            print(f"   Error on track: {e}")

    if new_data:
        df = pd.DataFrame(new_data)
        header_needed = not os.path.exists(DATA_FILE)
        df.to_csv(DATA_FILE, mode='a', index=False, header=header_needed)
        print(f"✅ Saved {len(new_data)} new tracks to {DATA_FILE}.")
    else:
        print("zzz No new tracks found (since script started).")
        
if __name__ == "__main__":
    print("🎵 DJ & Tracker Started...")
    
    try:
        network = pylast.LastFMNetwork(api_key=LASTFM_API_KEY)
        user = network.get_user(LASTFM_USERNAME)
        
        # --- THE FIX IS HERE ---
        # Added 'user-read-playback-state'
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope="user-read-private user-read-playback-state user-modify-playback-state",
            cache_path=CACHE_PATH, 
            show_dialog=True 
        ))
        
        open_spotify_and_play(sp)
        
        while True:
            fetch_music_data(sp, network, user)
            time.sleep(POLL_INTERVAL)
            
    except Exception as e:
        print(f"❌ Critical Error: {e}")