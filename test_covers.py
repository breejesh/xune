#!/usr/bin/env python3
"""Test album cover extraction."""
import sys
from pathlib import Path
from app.core.storage import load_tracks_db
from app.ui.main_window import MainWindow


def test_covers():
    """Check what covers are available."""
    tracks = load_tracks_db()
    print(f"Total tracks: {len(tracks)}")
    
    # Group by album
    albums = {}
    for track in tracks:
        album = track.album or "Unknown"
        if album not in albums:
            albums[album] = []
        albums[album].append(track)
    
    print(f"Total albums: {len(albums)}")
    print("\nFirst 10 albums:")
    for i, (album, album_tracks) in enumerate(list(albums.items())[:10]):
        print(f"  {album}: {len(album_tracks)} tracks")
        if album_tracks:
            track = album_tracks[0]
            print(f"    - Sample track path: {track.path}")
            print(f"    - Parent dir: {track.path.parent if hasattr(track.path, 'parent') else 'N/A'}")


if __name__ == "__main__":
    test_covers()
