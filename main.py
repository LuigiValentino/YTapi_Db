import requests
import sqlite3
import re

API_KEY = ""           # Clave de API de YouTube
CHANNEL_ID = ""        # ID del canal de YouTube
VIDEO_LIMIT = 20000    # Número máximo de videos a extraer

# Configuración de la base de datos
db_path = 'videos.sqlite'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    game TEXT,
    embed_link TEXT,
    video_id TEXT UNIQUE
)
''')
conn.commit()

def video_exists(video_id):
    cursor.execute("SELECT 1 FROM tracks WHERE video_id = ?", (video_id,))
    return cursor.fetchone() is not None

def get_playlist_id(channel_id):
    url = f"https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={channel_id}&key={API_KEY}"
    response = requests.get(url).json()
    if "items" in response and response["items"]:
        return response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    else:
        print("Error: No se pudo obtener la lista de reproducción del canal.")
        return None

def get_videos_from_playlist(playlist_id):
    videos = []
    page_token = ""
    video_count = 0

    while video_count < VIDEO_LIMIT:
        url = f"https://www.googleapis.com/youtube/v3/playlistItems?key={API_KEY}&playlistId={playlist_id}&part=snippet&maxResults=50&pageToken={page_token}"
        response = requests.get(url).json()
        
        if "error" in response:
            error_message = response["error"]["message"]
            print("Error al obtener datos de la API:", error_message)
            
            if "quota" in error_message.lower():
                print("Cuota diaria alcanzada. Reintente mañana.")
                return videos 
            else:
                print("Error inesperado:", error_message)
                return videos  

        for item in response.get("items", []):
            title = item["snippet"]["title"]
            video_id = item["snippet"]["resourceId"]["videoId"]
            embed_link = f"https://www.youtube.com/embed/{video_id}"

            if video_exists(video_id):
                continue

            match = re.match(r'^(.*?)-\s*(.*)$', title)
            if match:
                video_title = match.group(1).strip()
                game = match.group(2).strip()
            else:
                video_title = title
                game = None

            videos.append((video_title, game, embed_link, video_id))
            video_count += 1

            if video_count >= VIDEO_LIMIT:
                break

        page_token = response.get("nextPageToken", "")
        if not page_token:
            print("No hay más videos en la lista de reproducción.")
            break

    return videos

playlist_id = get_playlist_id(CHANNEL_ID)
if playlist_id:
    videos = get_videos_from_playlist(playlist_id)
    cursor.executemany('''
        INSERT INTO tracks (title, game, embed_link, video_id)
        VALUES (?, ?, ?, ?)
    ''', videos)
    conn.commit()
    print(f"{len(videos)} nuevos videos insertados en la base de datos. Total procesado: {len(videos)} videos.")
else:
    print("No se pudo encontrar la lista de reproducción del canal.")

conn.close()
