import spotipy
import streamlit as st
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import random
from streamlit_autorefresh import st_autorefresh  # pip install streamlit-autorefresh
from spotipy.cache_handler import CacheHandler

# global
LOCK_TIME = 20

# top/bottom padding
st.markdown(
    """
    <style>
        /* Reduce top padding */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Spotify OAuth scope for your app
SCOPE = "user-read-playback-state user-modify-playback-state playlist-read-private"

class CustomTokenHandler(CacheHandler):
    def get_cached_token(self):
        return {
            "refresh_token": st.secrets["DJ_REFRESH_TOKEN"],
            "scope": "user-read-playback-state user-modify-playback-state playlist-read-private",
            "token_type": "Bearer",
            "expires_in": 3600
        }

    def save_token_to_cache(self, token_info):
        pass  # Optional: we’re not persisting anything

def authenticate_host():
    """
    Authenticate the single host user with Spotify.
    Uses a fixed cache file for token caching.
    """
    auth_manager = SpotifyOAuth(
        client_id=st.secrets["DJ_CLIENT_ID"],
        client_secret=st.secrets["DJ_CLIENT_SECRET"],
        redirect_uri=st.secrets["DJ_REDIRECT_URI"],
        scope="user-read-playback-state user-modify-playback-state playlist-read-private",
        cache_path=".cache-host",
        open_browser=False,
        show_dialog=True,  # force login once, then token cached
        cache_handler=CustomTokenHandler()
    )

    token_info = auth_manager.refresh_access_token(st.secrets["DJ_REFRESH_TOKEN"])
    return Spotify(auth=token_info["access_token"])

    # token_info = auth_manager.get_cached_token()
    #
    # if not token_info:
    #     code = st.query_params.get("code")
    #     if not code:
    #         auth_manager.get_access_token(code)
    #         st.query_params.clear()  # clear URL params
    #         st.rerun()
    #     else:
    #         auth_url = auth_manager.get_authorize_url()
    #         st.markdown(f"[Host Login]({auth_url})")
    #         st.stop()
    #
    # return spotipy.Spotify(auth_manager=auth_manager)

# --- Helpers ---
def get_current_track():
    playback = sp.current_playback()
    if playback and playback.get("item"):
        item = playback["item"]
        context = playback.get("context")
        playlist_uri = context["uri"] if context and context["type"] == "playlist" else None
        playlist_id = playlist_uri.split(":")[-1] if playlist_uri else None
        return {
            "id": item["id"],
            "name": item["name"],
            "artist": item["artists"][0]["name"],
            "album_art": item["album"]["images"][0]["url"],
            "duration_ms": item["duration_ms"],
            "progress_ms": playback["progress_ms"],
            "playlist_id": playlist_id
        }
    return None

def get_random_tracks(playlist_id, k=4):
    results = sp.playlist_items(playlist_id, additional_types=('track',))
    all_items = results["items"]

    # Filter out unplayable and local tracks
    clean_tracks = []
    for item in all_items:
        track = item.get("track")
        if not track:
            continue
        if not track.get("is_playable", True):
            continue
        if track["uri"].startswith("spotify:local:"):
            continue
        if track["duration_ms"] < 30_000:
            continue  # Optional: skip short tracks
        clean_tracks.append(track)

    sampled = random.sample(clean_tracks, min(len(clean_tracks), k))

    return [{
        "name": t["name"],
        "artist": t["artists"][0]["name"],
        "uri": t["uri"]
    } for t in sampled]

def display_votes(options):
    st.subheader("🎵 Vote for the Next Song")
    for track in options:
        name = truncate(track["name"], 30)
        artist = truncate(track["artist"], 20)
        label = f'{name} – {artist}'

        uri = track["uri"]
        if st.session_state.get("vote_winner") == uri:
            st.success(f"🏆 {label}")  # Winner
        elif st.session_state.vote_winner:
            st.button(label, disabled=True)  # Voting locked
        else:
            if st.button(label):
                st.session_state.votes[uri] = st.session_state.votes.get(uri, 0) + 1

def truncate(text, max_len):
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def queue_top_voted():
    if not st.session_state.votes:
        st.info("No votes were cast.")
        return None

    max_votes = max(st.session_state.votes.values())
    # Find all URIs tied for max votes
    tied_uris = [uri for uri, votes in st.session_state.votes.items() if votes == max_votes]

    # Randomly pick one if tie
    top_uri = random.choice(tied_uris)

    try:
        sp.add_to_queue(top_uri)
        st.success(f"🎉 Queued winner!")
    except Exception as e:
        st.error(f"Failed to queue: {e}")

    st.session_state.votes = {}
    st.session_state.vote_winner = top_uri  # Save winner
    return top_uri

# --- Streamlit UI ---
st.markdown("<h2 style='text-align: center;'>🎧 Democratic DJ 🎧</h2>", unsafe_allow_html=True)
#st.title("🎧 Democratic DJ 🎧")

sp = authenticate_host()


# Init session state (only once)
for key in ["votes", "vote_options", "last_track_id", "queued_this_song", "vote_winner"]:
    if key not in st.session_state:
        if key == "votes":
            st.session_state[key] = {}
        elif key == "queued_this_song":
            st.session_state[key] = False
        else:
            st.session_state[key] = None

# --- Auto-refresh the app every second to update countdown & playback info ---
count = st_autorefresh(interval=1000, limit=None, key="refresh_timer")

# Get current playback info
current = get_current_track()

if current:
    # st.image(current["album_art"], width=250)
    # st.markdown(f"**Now Playing:** {current['name']} by {current['artist']}")

    song_name = truncate(current['name'], 30)
    artist_name = truncate(current['artist'], 20)

    # Countdown timer
    remaining_ms = current["duration_ms"] - current["progress_ms"]
    remaining_sec = max(0, remaining_ms // 1000)
    time_left_to_vote = remaining_sec - LOCK_TIME
    if time_left_to_vote < 0:
        time_left_to_vote = 0  # don't show negative time
    minutes, seconds = divmod(time_left_to_vote, 60)

    # Center album art
    st.markdown(
        f"""
        <div style='text-align: center;'>
            <img src="{current['album_art']}" width="125" />
            <h4>Now Playing: {song_name} by {artist_name}</h4>
            <p>⏱️ Time left to vote: <strong>{minutes}:{str(seconds).zfill(2)}</strong></p>
        </div>
        """,
        unsafe_allow_html=True
    )


    # st.markdown(f"⏱️ Time left to vote: **{minutes}:{str(seconds).zfill(2)}**")

    # --- Auto-queue winner when song ends ---
    if remaining_sec <= LOCK_TIME and not st.session_state.get("queued_this_song"):
        queue_top_voted()
        st.session_state.queued_this_song = True

    # --- Smart Vote Refresh Logic ---
    progress_marker = current["progress_ms"] // 10_000  # 10-second buckets
    track_key = f"{current['id']}:{progress_marker}"

    if st.session_state.get("current_vote_key") != track_key:
        # Only update vote options on new track
        if st.session_state.get("last_track_id") != current["id"]:
            st.session_state.vote_options = get_random_tracks(current["playlist_id"]) if current["playlist_id"] else []
            st.session_state.votes = {}
            st.session_state.last_track_id = current["id"]
            st.session_state.queued_this_song = False  # reset for next track
            st.session_state.vote_winner = None  # NEW: clear winner

        st.session_state.current_vote_key = track_key

    # Display vote buttons
    if st.session_state.vote_options:
        display_votes(st.session_state.vote_options)

        if st.button("✅ End Vote + Queue Winner"):
            queue_top_voted()
            st.session_state.queued_this_song = True  # optional: prevent requeue if user ends early
    else:
        st.warning("No playlist found. Start playing a playlist on your Spotify device.")
else:
    st.warning("No active Spotify playback found. Play a song from a playlist to begin.")
