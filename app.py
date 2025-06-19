import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import uuid

CLIENT_ID = st.secrets["client_id"]
CLIENT_SECRET = st.secrets["client_secret"]
REDIRECT_URI = "https://spotify-playlist-sync.streamlit.app"
SCOPE = "playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative user-read-private"

st.set_page_config(page_title="Spotify Playlist Sync", page_icon=a"🎵")
st.title("🎵 Spotify Playlist Sync")

def get_auth_manager(user_id):
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=".cache-" + user_id,
        open_browser=False
    )

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

auth_manager = get_auth_manager(st.session_state.user_id)
token_info = st.session_state.get("token_info", None)

query_params = st.query_params

auth_manager = SpotifyOAuth(client_id=CLIENT_ID,
                            client_secret=CLIENT_SECRET,
                            redirect_uri=REDIRECT_URI,
                            scope=SCOPE)

if "code" in query_params:
    code = query_params["code"][0]
    token_info = auth_manager.get_access_token(code, as_dict=True)
    st.write("Access token alındı")
else:
    auth_url = auth_manager.get_authorize_url()
    st.markdown(f"[Login with Spotify]({auth_url})")

try:
    token = token_info['access_token']
    sp = spotipy.Spotify(auth=token)

    user = sp.current_user()
    st.success(f"Logged in as: {user['display_name']}")

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

except spotipy.exceptions.SpotifyException as e:
    st.error(f"Spotify API Error: {e}")
    # Token hatalı veya süresi dolmuş olabilir, sıfırla ve yeniden giriş iste
    if "token_info" in st.session_state:
        del st.session_state["token_info"]
    st.experimental_rerun()
