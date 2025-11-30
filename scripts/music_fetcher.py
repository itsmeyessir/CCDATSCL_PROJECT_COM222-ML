import pandas as pd
import pylast
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import os
import subprocess 
from dotenv import load_dotenv
from datetime import datetime, timedelta

# --- CONFIGURATION ---
# Load .env from the parent directory if we are in scripts/
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
TARGET_PLAYLIST_URL = "https://open.spotify.com/playlist/0vvXsWCC9xrXsKd4FyS8kM?si=a85d3f5849b44ee1" 

# DIRECTORY SETUP
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "music_data.csv")
CACHE_PATH = os.path.join(BASE_DIR, ".cache") 

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

POLL_INTERVAL = 1200 
TIMEZONE_OFFSET = 8 # Manila Time Correction

# Store script start time (We will update this to Local Time logic)
SCRIPT_START_TIME = int(time.time())

def parse_lastfm_date_to_local(date_obj):
    """
    Converts Last.fm time (UTC) to Local Time (Manila/UTC+8)
    Returns: (datetime_object, unix_timestamp)
    """
    try:
        if not date_obj:
            # If "Now Playing", use current system time
            now = datetime.now()
            return now, int(now.timestamp())

        # If it's a string, parse it
        if isinstance(date_obj, str):
            dt_utc = datetime.strptime(date_obj, "%d %b %Y, %H:%M")
        else:
            # If it's a pylast object, get the string representation
            dt_utc = datetime.strptime(str(date_obj), "%d %b %Y, %H:%M")
            
        # Add Offset to get Manila Time
        dt_local = dt_utc + timedelta(hours=TIMEZONE_OFFSET)
        return dt_local, int(dt_local.timestamp())
        
    except Exception as e:
        # Fallback to current time if parsing fails
        print(f"   ⚠️ Date parse error: {e}")
        now = datetime.now()
        return now, int(now.timestamp())

def open_spotify_and_play(sp):
    print("🚀 Launching Spotify App...")
    try:
        subprocess.call(["open", "-a", "Spotify"])
        time.sleep(4) 
        
        print("   (Waking up local player...)")
        subprocess.call(["osascript", "-e", 'tell application "Spotify" to play'])
        time.sleep(2) 

        print(f"▶️ Switching to Target Playlist...")
        devices = sp.devices()
        if devices['devices']:
            device_id = devices['devices'][0]['id']
            sp.start_playback(device_id=device_id, context_uri=TARGET_PLAYLIST_URL)
            print("✅ Music started!")
        else:
            print("⚠️ App is open but API still can't see it. Please press Play manually!")
        
    except Exception as e:
        print(f"⚠️ Auto-play glitch: {e}")

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
        recent_tracks = user.get_recent_tracks(limit=50)
    except Exception as e:
        print(f"❌ Last.fm Error: {e}")
        return

    existing_timestamps = get_existing_timestamps()
    new_data = []
    artist_cache = {} 

    # We use a 20-minute buffer on the start time to be safe
    # But now we compare LOCAL time vs LOCAL start time
    effective_start_time = SCRIPT_START_TIME - 1200

    for item in reversed(recent_tracks):
        try:
            track = item.track
            
            # --- THE FIX: Convert to Local Time before comparing ---
            dt_local, ts_local = parse_lastfm_date_to_local(item.playback_date)
            
            # Filter: Is this track newer than when we started (minus buffer)?
            if ts_local < effective_start_time:
                continue 

            # Create the timestamp string we want to save (Local Time)
            timestamp_str = str(dt_local)
            
            if timestamp_str in existing_timestamps:
                continue 

            # --- METADATA FETCHING ---
            artist_name = track.artist.name
            title = track.title
            
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
                'timestamp': timestamp_str, # Saving the corrected Local Time
                'artist': artist_name,
                'title': title,
                'genres': genres,
                'popularity': popularity
            })
            print(f"   -> New Track: {title} [{genres[:15]}...] at {timestamp_str}")

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
    print(f"🎵 DJ & Tracker Started (UTC+{TIMEZONE_OFFSET} Mode)...")
    
    try:
        network = pylast.LastFMNetwork(api_key=LASTFM_API_KEY)
        user = network.get_user(LASTFM_USERNAME)
        
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