import pandas as pd
import pylast
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# --- CONFIGURATION ---
# 1. YOUR EXACT SESSION WINDOW (Manila Time)
START_TIME_STR = "2025-11-29 18:01:00" 
END_TIME_STR   = "2025-11-29 21:05:00"

# 2. YOUR TIMEZONE OFFSET (Manila = 8)
TIMEZONE_OFFSET = 8 

# Load Env
if os.path.exists("../.env"):
    load_dotenv("../.env")
else:
    load_dotenv()

LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_USERNAME = os.getenv("LASTFM_USERNAME")
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")

# Directory Setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "music_data.csv")
CACHE_PATH = os.path.join(BASE_DIR, ".cache")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def parse_lastfm_date(date_str):
    try:
        # Parse UTC time from Last.fm
        dt_utc = datetime.strptime(str(date_str), "%d %b %Y, %H:%M")
        # Add Offset to get Manila Time
        dt_local = dt_utc + timedelta(hours=TIMEZONE_OFFSET)
        return dt_local
    except ValueError:
        return None

def rescue_data():
    print(f"🚑 Starting SMART Rescue (UTC+{TIMEZONE_OFFSET})...")
    
    start_dt = datetime.strptime(START_TIME_STR, "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(END_TIME_STR, "%Y-%m-%d %H:%M:%S")
    
    print(f"   Target Window: {start_dt}  <-->  {end_dt}")
    
    try:
        network = pylast.LastFMNetwork(api_key=LASTFM_API_KEY)
        user = network.get_user(LASTFM_USERNAME)
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope="user-read-private",
            cache_path=CACHE_PATH
        ))
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return

    print("   Fetching last 100 tracks from Last.fm...")
    try:
        recent_tracks = user.get_recent_tracks(limit=100)
    except Exception as e:
        print(f"Error fetching from Last.fm: {e}")
        return
    
    rescued_data = []
    artist_cache = {}

    for item in reversed(recent_tracks):
        try:
            if not item.playback_date:
                continue 

            # Convert UTC string to Local Time
            track_dt = parse_lastfm_date(item.playback_date)
            
            if track_dt:
                # DEBUG PRINT: Show what the script sees
                # print(f"   Checking: {item.track.title} @ {track_dt} ... ", end="")

                if start_dt <= track_dt <= end_dt:
                    # print("✅ KEEP")
                    print(f"   ✅ KEEP: {item.track.title} ({track_dt})")
                    
                    # --- FETCH METADATA ---
                    artist_name = item.track.artist.name
                    title = item.track.title
                    # Save the LOCAL time to CSV so it matches Mac Tracker
                    timestamp = str(track_dt) 
                    
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

                    rescued_data.append({
                        'timestamp': timestamp,
                        'artist': artist_name,
                        'title': title,
                        'genres': genres,
                        'popularity': popularity
                    })
                else:
                    # print("❌ SKIP")
                    pass
            else:
                pass

        except Exception as e:
            print(f"   Error on track: {e}")

    if rescued_data:
        df = pd.DataFrame(rescued_data)
        header_needed = not os.path.exists(DATA_FILE)
        # Append mode to be safe, or 'w' to overwrite if you want a clean start
        df.to_csv(DATA_FILE, mode='w', index=False)
        print(f"🎉 RESCUE COMPLETE! Saved {len(rescued_data)} tracks to {DATA_FILE}")
    else:
        print("❌ No tracks found. (Did you listen to music?)")

if __name__ == "__main__":
    rescue_data()