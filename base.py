"""
File Manager Backend - Teil 1: Basis-Strukturen und Konfiguration
"""

import os
import sys
import json
import logging
import codecs
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

# Unicode-Encoding fix für Windows
if sys.platform == 'win32':
    try:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
    except Exception:
        pass  # Fallback if already configured


class FileStatus(Enum):
    """Status eines gefundenen Files"""
    PENDING = "pending"
    APPROVED = "approved" 
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    REJECTED = "rejected"


class FileType(Enum):
    """Unterstützte Dateitypen"""
    VIDEO = "video"
    ARCHIVE = "archive"
    OTHER = "other"


@dataclass
class VideoFile:
    """Repräsentiert eine gefundene Video-Datei"""
    filepath: str
    filename: str
    series_name: str
    episode_number: Optional[int]
    season_number: Optional[int]
    file_size: int
    status: FileStatus
    target_folder: Optional[str] = None
    detected_at: float = 0.0
    last_modified: float = 0.0
    confidence: float = 0.0  # Confidence der Pattern-Erkennung
    manual_override: bool = False  # Wurde manuell bearbeitet
    original_filename: str = ""  # Original-Dateiname für Fallback
    
    def __post_init__(self):
        if not self.original_filename:
            self.original_filename = self.filename
    
    def to_dict(self) -> Dict:
        """Konvertiert zu Dictionary für JSON"""
        return {
            **asdict(self),
            'status': self.status.value,
            'file_size_mb': round(self.file_size / (1024*1024), 2)
        }


@dataclass
class ArchiveFile:
    """Repräsentiert eine gefundene Archive-Datei"""
    filepath: str
    filename: str
    file_size: int
    status: FileStatus
    extract_path: Optional[str] = None
    detected_at: float = 0.0
    last_modified: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            'status': self.status.value,
            'file_size_mb': round(self.file_size / (1024*1024), 2)
        }


@dataclass
class WatchFolder:
    """Konfiguration für überwachte Ordner"""
    path: str
    name: str
    watch_videos: bool = True
    watch_archives: bool = True
    recursive: bool = True
    video_search_depth: int = 1  # 0 = nur Hauptordner, 1 = eine Ebene tief, etc.
    enabled: bool = True


@dataclass
class TargetFolder:
    """Ziel-Ordner für Video-Sortierung"""
    path: str
    name: str
    priority: int = 0  # Höhere Zahl = höhere Priorität bei Auswahl
    enabled: bool = True


class Config:
    """Zentrale Konfigurationsklasse"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.watch_folders: List[WatchFolder] = []
        self.target_folders: List[TargetFolder] = []
        self.video_extensions: Set[str] = {
            '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', 
            '.webm', '.m4v', '.mpg', '.mpeg', '.3gp', '.ts',
            '.ogv', '.divx', '.xvid', '.rm', '.rmvb'
        }
        self.archive_extensions: Set[str] = {
            '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'
        }
        self.min_file_size_mb: int = 10  # Mindestgröße für Videos
        self.download_stability_seconds: int = 30  # Warten bis Datei stabil ist
        self.enable_notifications: bool = True
        self.auto_extract_archives: bool = True
        self.delete_archives_after_extract: bool = True
        self.auto_cleanup_extracted_archives: bool = False  # Neu: Auto-cleanup ohne Nachfrage
        self.cleanup_extracted_archives_on_startup: bool = True  # Neu: Startup-cleanup aktiviert
        self.log_level: str = "INFO"
        
        self.load_config()
    
    def load_config(self) -> None:
        """Lädt Konfiguration aus JSON-Datei"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Watch Folders laden
                self.watch_folders = []
                for folder_data in data.get('watch_folders', []):
                    # Rückwärtskompatibilität: video_search_depth hinzufügen falls nicht vorhanden
                    if 'video_search_depth' not in folder_data:
                        folder_data['video_search_depth'] = 1
                    self.watch_folders.append(WatchFolder(**folder_data))
                
                # Target Folders laden
                self.target_folders = [
                    TargetFolder(**folder) for folder in data.get('target_folders', [])
                ]
                
                # Weitere Settings
                self.video_extensions.update(data.get('video_extensions', []))
                self.archive_extensions.update(data.get('archive_extensions', []))
                self.min_file_size_mb = data.get('min_file_size_mb', 10)
                self.download_stability_seconds = data.get('download_stability_seconds', 30)
                self.enable_notifications = data.get('enable_notifications', True)
                self.auto_extract_archives = data.get('auto_extract_archives', True)
                self.delete_archives_after_extract = data.get('delete_archives_after_extract', True)
                self.auto_cleanup_extracted_archives = data.get('auto_cleanup_extracted_archives', False)
                self.cleanup_extracted_archives_on_startup = data.get('cleanup_extracted_archives_on_startup', True)
                self.log_level = data.get('log_level', 'INFO')
                
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            self._create_default_config()
    
    def save_config(self) -> None:
        """Speichert aktuelle Konfiguration"""
        try:
            data = {
                'watch_folders': [asdict(folder) for folder in self.watch_folders],
                'target_folders': [asdict(folder) for folder in self.target_folders],
                'video_extensions': list(self.video_extensions),
                'archive_extensions': list(self.archive_extensions),
                'min_file_size_mb': self.min_file_size_mb,
                'download_stability_seconds': self.download_stability_seconds,
                'enable_notifications': self.enable_notifications,
                'auto_extract_archives': self.auto_extract_archives,
                'delete_archives_after_extract': self.delete_archives_after_extract,
                'auto_cleanup_extracted_archives': self.auto_cleanup_extracted_archives,
                'cleanup_extracted_archives_on_startup': self.cleanup_extracted_archives_on_startup,
                'log_level': self.log_level
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")
    
    def _create_default_config(self) -> None:
        """Erstellt Standard-Konfiguration"""
        # Standard Download-Ordner hinzufügen
        downloads_path = str(Path.home() / "Downloads")
        if os.path.exists(downloads_path):
            self.watch_folders.append(
                WatchFolder(
                    path=downloads_path,
                    name="Downloads",
                    watch_videos=True,
                    watch_archives=True,
                    recursive=True,
                    video_search_depth=1  # Standardtiefe: 1 Ebene
                )
            )
        
        # Standard Video-Ordner hinzufügen
        videos_path = str(Path.home() / "Videos")
        if os.path.exists(videos_path):
            self.target_folders.append(
                TargetFolder(
                    path=videos_path,
                    name="Videos",
                    priority=1
                )
            )
        
        self.save_config()
    
    def add_watch_folder(self, path: str, name: str, **kwargs) -> bool:
        """Fügt neuen Überwachungsordner hinzu"""
        if not os.path.exists(path):
            return False
        
        # Prüfen ob bereits vorhanden
        for folder in self.watch_folders:
            if folder.path == path:
                return False
        
        self.watch_folders.append(WatchFolder(path=path, name=name, **kwargs))
        self.save_config()
        return True
    
    def add_target_folder(self, path: str, name: str, **kwargs) -> bool:
        """Fügt neuen Zielordner hinzu"""
        if not os.path.exists(path):
            return False
        
        # Prüfen ob bereits vorhanden
        for folder in self.target_folders:
            if folder.path == path:
                return False
        
        self.target_folders.append(TargetFolder(path=path, name=name, **kwargs))
        self.save_config()
        return True
    
    def get_file_type(self, filepath: str) -> FileType:
        """Bestimmt Dateityp basierend auf Erweiterung"""
        ext = Path(filepath).suffix.lower()
        if ext in self.video_extensions:
            return FileType.VIDEO
        elif ext in self.archive_extensions:
            return FileType.ARCHIVE
        else:
            return FileType.OTHER


# Logging Setup - Jetzt außerhalb der Config-Klasse definiert
def setup_logging(config: Config) -> None:
    """Initialisiert Logging-System mit Unicode-Support"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    
    # Clear existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # File handler with UTF-8 encoding
    try:
        file_handler = logging.FileHandler('filemanager.log', encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_format))
    except Exception:
        # Fallback if UTF-8 encoding fails
        file_handler = logging.FileHandler('filemanager.log')
        file_handler.setFormatter(logging.Formatter(log_format))
    
    # Console handler with UTF-8 encoding
    try:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(log_format))
    except Exception:
        # Fallback
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format))
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=[file_handler, console_handler],
        force=True
    )


if __name__ == "__main__":
    # Test der Basis-Klassen
    config = Config()
    setup_logging(config)
    
    print("Configuration loaded:")
    print(f"Watch Folders: {len(config.watch_folders)}")
    print(f"Target Folders: {len(config.target_folders)}")
    
    # Test VideoFile
    test_video = VideoFile(
        filepath="/test/video.mp4",
        filename="video.mp4", 
        series_name="Test Series",
        episode_number=1,
        season_number=1,
        file_size=1024*1024*500,  # 500MB
        status=FileStatus.PENDING
    )
    
    print("\nTest VideoFile:")
    print(json.dumps(test_video.to_dict(), indent=2))