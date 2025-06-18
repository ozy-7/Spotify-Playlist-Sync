import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Spotify API credentials
CLIENT_ID = st.secrets["client_id"]
CLIENT_SECRET = st.secrets["client_secret"]
REDIRECT_URI = "https://spotify-playlist-sync.streamlit.app"
SCOPE = "playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative user-read-private"

st.set_page_config(page_title="Spotify Playlist Sync", page_icon="🎵")
st.title("🎵 Spotify Playlist Sync")

# Token varsa session state'e kaydet
if "token_info" not in st.session_state:
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        open_browser=False
    )

    if "code" in st.query_params:
        code = st.query_params["code"]
        token_info = auth_manager.get_access_token(code=code, as_dict=True)
        st.session_state.token_info = token_info
    else:
        auth_url = auth_manager.get_authorize_url()
        st.markdown(f"[🔐 Login with Spotify]({auth_url})", unsafe_allow_html=True)
        st.stop()

# Token varsa Spotipy nesnesini oluştur
token = st.session_state.token_info["access_token"]
sp = spotipy.Spotify(auth=token)

# Kullanıcı bilgisi
user = sp.current_user()
st.success(f"Logged in as: {user['display_name']}")

# Çalma listeleri
playlists = sp.current_user_playlists(limit=50)
playlist_options = {p["name"]: p["id"] for p in playlists["items"]}

source = st.selectbox("🎧 Select Source Playlist", list(playlist_options.keys()))
target = st.selectbox("🎯 Select Target Playlist", list(playlist_options.keys()))
count = st.number_input("🎵 Number of recent tracks to sync", min_value=1, max_value=100, value=50)

if st.button("🔁 Sync Playlists"):
    source_id = playlist_options[source]
    target_id = playlist_options[target]

    total_tracks = sp.playlist_tracks(source_id, fields="total")["total"]
    offset = max(0, total_tracks - count)
    source_tracks = sp.playlist_tracks(source_id, limit=count, offset=offset, fields="items(track(uri))")
    source_uris = [t["track"]["uri"] for t in source_tracks["items"]]

    target_tracks = sp.playlist_tracks(target_id, fields="items(track(uri))")["items"]
    target_uris = [t["track"]["uri"] for t in target_tracks]

    new_uris = [uri for uri in source_uris if uri not in target_uris]

    while len(target_uris) + len(new_uris) > count:
        to_remove = target_tracks[0]["track"]["uri"]
        sp.playlist_remove_all_occurrences_of_items(target_id, [to_remove])
        target_tracks.pop(0)
        target_uris.pop(0)

    if new_uris:
        sp.playlist_add_items(target_id, new_uris)
        st.success(f"✅ {len(new_uris)} new track(s) added to target playlist.")
    else:
        st.info("ℹ️ No new tracks to sync.")
