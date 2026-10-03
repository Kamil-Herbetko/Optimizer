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
        tracks = []
        while results:
            for item in results["items"]:
                track = item.get("track")
                if track and track.get("artists") and not track.get("is_local"):
                    tracks.append(f"{track['name']} {track['artists'][0]['name']}")
            results = sp.next(results) if results.get("next") else None
        return tracks

    return []
