import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Streamlit ayarları
st.set_page_config(page_title="Spotify Playlist Sync", page_icon="🎵")

# Spotify API bilgileri (Streamlit Secrets kısmında tutulur)
CLIENT_ID = st.secrets["client_id"]
CLIENT_SECRET = st.secrets["client_secret"]
REDIRECT_URI = "https://spotify-playlist-sync.streamlit.app"
SCOPE = "playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative user-read-private"

# Spotipy Auth Manager
auth_manager = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    show_dialog=True
    cache_path=None
)

query_params = st.query_params
if "code" in query_params:
    code = query_params["code"]
    if isinstance(code, list):
        code = code[0]

    try:
        token_info = auth_manager.get_access_token(code, as_dict=True)
        if token_info and "access_token" in token_info:
            sp = spotipy.Spotify(auth=token_info["access_token"])
            user = sp.current_user()
            st.success(f"Hoş geldin, {user['display_name']}!")
        else:
            st.error("Access token alınamadı. Lütfen tekrar deneyin.")
    except spotipy.SpotifyOauthError as e:
        st.error("Spotify ile bağlantı kurulamadı. Token süresi dolmuş olabilir. Yeniden giriş yap.")
        st.stop()
else:
    auth_url = auth_manager.get_authorize_url()
    st.markdown(f"[Login with Spotify]({auth_url})", unsafe_allow_html=True)
    st.stop()

# Spotify client'ı oluştur
sp = spotipy.Spotify(auth=token_info["access_token"])
user = sp.current_user()
st.success(f"Hoş geldin, {user['display_name']}! 👋")

# Playlist'leri getir
playlists = sp.current_user_playlists(limit=50)["items"]
playlist_options = {p['name']: p['id'] for p in playlists}

# Playlist seçimi
source = st.selectbox("🎧 Source Playlist", list(playlist_options.keys()))
target = st.selectbox("📥 Target Playlist", list(playlist_options.keys()))
count = st.number_input("🎶 Kaç şarkı eşitlensin?", min_value=1, max_value=100, value=50)

# Eşitle butonu
if st.button("🔁 Sync Playlists"):
    try:
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
            st.success(f"{len(new_uris)} yeni şarkı eklendi 🎉")
        else:
            st.info("Eklenmesi gereken yeni şarkı bulunamadı.")
    except Exception as e:
        st.error(f"Hata: {str(e)}")
