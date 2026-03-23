#!/usr/bin/env python3
"""Debug metadata extraction using LibraryService."""
from pathlib import Path
from mutagen import File as MutagenFile
from app.services.library_service import LibraryService
from app.repositories import TrackRepository

class DummyRepository(TrackRepository):
    """Dummy repository for testing."""
    def close(self): pass
    def delete(self, track_id): pass
    def exists(self, track_id): return False
    def get_all(self): return []
    def get_by_id(self, track_id): return None
    def save(self, track): pass

# Initialize service with dummy repo
service = LibraryService(DummyRepository())

# Find music files - test both MP3 and WMA
music_dirs = [Path.home() / 'Music', Path.home() / 'Desktop']
extensions = ['*.wma']
found = False

for music_dir in music_dirs:
    if music_dir.exists():
        for ext in extensions:
            for file_path in music_dir.rglob(ext):
                print(f'\n=== Testing: {file_path} ===')
                audio = MutagenFile(file_path)
                if audio:
                    print(f'File type: {type(audio).__name__}')
                    
                    # Show available keys in raw tags
                    if hasattr(audio, 'tags') and audio.tags:
                        print(f'Available tag keys: {list(audio.tags.keys())}')
                    
                    # Extract metadata using LibraryService methods
                    title = service._get_metadata_value(audio, ["TIT2", "TITLE", "Title", "\xa9nam"])
                    artist = service._get_metadata_value(audio, ["TPE1", "ARTIST", "Artist", "\xa9ART", "Author"])
                    album = service._get_metadata_value(audio, ["TALB", "ALBUM", "Album", "\xa9alb", "WM/AlbumTitle"])
                    genre = service._get_metadata_value(audio, ["TCON", "GENRE", "Genre", "\xa9gen", "WM/Genre"]) or ""
                    year = service._get_metadata_value(audio, ["TDRC", "DATE", "Year", "\xa9day", "WM/Year"])
                    track_num = service._get_metadata_value(audio, ["TRCK", "TRACKNUMBER", "TrackNumber", "WM/TrackNumber", "WM/TrackNumberAndCount"])
                    
                    print(f'\nExtracted metadata:')
                    print(f'  Title:      {title}')
                    print(f'  Artist:     {artist}')
                    print(f'  Album:      {album}')
                    print(f'  Genre:      {genre}')
                    print(f'  Year:       {year}')
                    print(f'  Track #:    {track_num}')
                    
                    if hasattr(audio, 'info'):
                        print(f'  Duration:   {audio.info.length:.2f}s')
                found = True
                break
            if found:
                break
    if found:
        break

if not found:
    print("No MP3 or WMA files found in Music or Desktop")
