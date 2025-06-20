import streamlit as st
import spotipy
import tempfile
import uuid
import os
from spotipy.oauth2 import SpotifyOAuth

# 📌 Streamlit secrets içinden client bilgilerini alıyoruz
CLIENT_ID = st.secrets["client_id"]
CLIENT_SECRET = st.secrets["client_secret"]
REDIRECT_URI = "https://spotify-playlist-sync.streamlit.app"

SCOPE = (
    "playlist-modify-public "
    "playlist-modify-private "
    "playlist-read-private "
    "playlist-read-collaborative "
    "user-read-private"
)

st.set_page_config(page_title="Spotify Playlist Sync", page_icon="🎵")
st.title("🎵 Spotify Playlist Sync")

# 🧠 Oturuma özel cache path oluştur
if "cache_path" not in st.session_state:
    session_id = str(uuid.uuid4())
    temp_dir = tempfile.gettempdir()
    st.session_state.cache_path = os.path.join(temp_dir, f".spotify_cache_{session_id}")

# 🔐 Her oturum için yeni auth manager
auth_manager = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_path=st.session_state.cache_path
)

query_params = st.query_params
code = query_params.get("code", [None])[0] if isinstance(query_params.get("code"), list) else query_params.get("code")

if "token_info" not in st.session_state:
    if code:
        try:
            token_info = auth_manager.get_cached_token(code, as_dict=True)
            st.session_state.token_info = token_info  # 🎯 Session'da sakla
            st.query_params()  # 🔄 URL'deki `code` parametresini temizle
            st.rerun()
        except spotipy.oauth2.SpotifyOauthError:
            st.error("Token alınamadı. Yeniden giriş yapmayı deneyin.")
            st.stop()
    else:
        auth_url = auth_manager.get_authorize_url()
        st.markdown(f"[👉 Login with Spotify]({auth_url})", unsafe_allow_html=True)
        st.stop()

# 🟢 Kullanıcı başarıyla giriş yaptıysa:
sp = spotipy.Spotify(auth=st.session_state.token_info["cached_token"])

try:
    user = sp.current_user()
    st.success(f"Hoş geldin, **{user['display_name']}**!")
except Exception:
    st.error("Giriş başarısız. Lütfen tekrar giriş yap.")
    st.stop()

# 🎵 Kullanıcının playlistlerini çek
playlists = sp.current_user_playlists(limit=50)
playlist_dict = {p['name']: p['id'] for p in playlists['items']}

if len(playlist_dict) < 2:
    st.warning("En az iki playlist'e sahip olmalısınız.")
    st.stop()

source = st.selectbox("🎧 Kaynak Playlist", list(playlist_dict.keys()))
target = st.selectbox("🎯 Hedef Playlist", list(playlist_dict.keys()))
count = st.number_input("Kaç şarkıyı senkronize etmek istersiniz?", 1, 100, 50)

if st.button("🔁 Sync Playlists"):
    try:
        source_id = playlist_dict[source]
        target_id = playlist_dict[target]

        total_tracks = sp.playlist_tracks(source_id, fields="total")["total"]
        offset = max(0, total_tracks - count)
        source_tracks = sp.playlist_tracks(source_id, limit=count, offset=offset, fields="items(track(uri))")
        source_uris = [item["track"]["uri"] for item in source_tracks["items"] if item.get("track")]

        target_tracks = sp.playlist_tracks(target_id, fields="items(track(uri))")["items"]
        target_uris = [item["track"]["uri"] for item in target_tracks if item.get("track")]

        new_uris = [uri for uri in source_uris if uri not in target_uris]

        # Hedef playlist'te fazla varsa sil
        while len(target_uris) + len(new_uris) > count and target_tracks:
            to_remove = target_tracks[0]["track"]["uri"]
            sp.playlist_remove_all_occurrences_of_items(target_id, [to_remove])
            target_tracks.pop(0)
            target_uris.pop(0)

        if new_uris:
            sp.playlist_add_items(target_id, new_uris)
            st.success(f"✅ {len(new_uris)} yeni şarkı eklendi!")
        else:
            st.info("⚠️ Yeni şarkı yok. Zaten güncel.")
    except Exception as e:
        st.error(f"Hata oluştu: {str(e)}")
