import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os

sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    )
)


def spotify_to_search(url: str) -> list[str]:
    if "track" in url:
        track = sp.track(url)
        return [f"{track['name']} {track['artists'][0]['name']}"]

    if "playlist" in url:
        results = sp.playlist_items(url)
        return [
            f"{item['track']['name']} {item['track']['artists'][0]['name']}"
            for item in results["items"]
        ]

    return []
