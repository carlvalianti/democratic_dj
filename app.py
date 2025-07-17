import streamlit as st
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import random
import time

# --- Spotify Auth Setup ---
sp = Spotify(auth_manager=SpotifyOAuth(
    scope="user-read-playback-state user-modify-playback-state playlist-read-private",
    redirect_uri="http://localhost:8501",
    client_id="e32ded3fccba40daa5d79d13330900b1",
    client_secret="7704c734ef9548b49fab5a132bd83713",
    open_browser=False,
))

# --- Session State Init ---
if "votes" not in st.session_state:
    st.session_state.votes = {}

# --- Get Current Track ---
def get_current_track():
    playback = sp.current_playback()
    if playback and playback["is_playing"]:
        item = playback["item"]
        return {
            "name": item["name"],
            "artist": item["artists"][0]["name"],
            "album_art": item["album"]["images"][0]["url"],
            "duration_ms": item["duration_ms"],
            "progress_ms": playback["progress_ms"]
        }
    return None

# --- Get Random Tracks from Playlist ---
def get_random_tracks(playlist_id, k=4):
    tracks = sp.playlist_items(playlist_id, additional_types=('track',))["items"]
    options = random.sample(tracks, k)
    return [{
        "name": t["track"]["name"],
        "artist": t["track"]["artists"][0]["name"],
        "uri": t["track"]["uri"]
    } for t in options]

# --- Display Voting Options ---
def display_votes(vote_options):
    st.subheader("Vote for the Next Song!")
    for track in vote_options:
        if st.button(f'🎶 {track["name"]} - {track["artist"]}'):
            uri = track["uri"]
            st.session_state.votes[uri] = st.session_state.votes.get(uri, 0) + 1

# --- Queue Winner ---
def queue_top_voted():
    if not st.session_state.votes:
        return None
    top_uri = max(st.session_state.votes, key=st.session_state.votes.get)
    st.write(f"🔥 Queued: {top_uri}")
    sp.add_to_queue(top_uri)
    st.session_state.votes = {}
    return None


# --- Main App ---
st.title("🎧 Democratic DJ")
current = get_current_track()

if current:
    st.markdown(f"**Now Playing:** {current['name']} by {current['artist']}")
    st.image(current["album_art"], width=200)

    playlist_id = "YOUR_PLAYLIST_ID"
    vote_options = get_random_tracks(playlist_id)
    display_votes(vote_options)

    # Timer to simulate voting window (replace with background logic if needed)
    if st.button("✅ End Vote + Queue Winner"):
        queue_top_voted()
else:
    st.write("No active playback found.")
