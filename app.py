import streamlit as st
import spotipy
import tempfile
import uuid
import os
from spotipy.oauth2 import SpotifyOAuth

# Streamlit secrets içinden client bilgilerini alıyoruz
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

# Oturuma özel cache path oluştur
if "cache_path" not in st.session_state:
    session_id = str(uuid.uuid4())
    temp_dir = tempfile.gettempdir()
    st.session_state.cache_path = os.path.join(temp_dir, f".spotify_cache_{session_id}")

# Yetkilendirme yöneticisini her zaman yeniden oluştur (session_state'e koyma!)
auth_manager = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_path=st.session_state.cache_path,
    show_dialog=True
)

# Kod parametresini al
code = st.query_params.get("code")
if isinstance(code, list):
    code = code[0]

# Eğer token yoksa ve kod varsa: token al ve sakla
if "token_info" not in st.session_state:
    if code:
        try:
            auth_manager.get_access_token(code=code)
            token_info = auth_manager.get_cached_token()
            st.session_state.token_info = token_info
            st.write("✅ Token alındı ve kaydedildi.")
            st.query_params.pop("code", None)
            st.rerun()
        except Exception as e:
            st.error(f"Token alınamadı. Hata: {str(e)}")
            st.stop()
    else:
        auth_url = auth_manager.get_authorize_url()
        st.markdown(f"[👉 Spotify ile Giriş Yap]({auth_url})", unsafe_allow_html=True)
        st.stop()

# Giriş başarılıysa spotipy istemcisi hazır
sp = spotipy.Spotify(auth_manager=auth_manager)

# Kullanıcıyı getir
try:
    user = sp.current_user()
    st.success(f"Hoş geldin, **{user['display_name']}**!")
except Exception as e:
    st.error(f"Giriş başarısız: {str(e)}")
    st.stop()

# Playlistleri getir
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

        # Fazla şarkı varsa hedef playlist'ten sil
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
