"""
File Manager Backend - Teil 1: Basis-Strukturen und Konfiguration - FIXED VERSION
Erweitert um Ordner-Entfernung und verbesserte Konfigurationsverwaltung
"""

import os
import json
import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum


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
    """Zentrale Konfigurationsklasse - ERWEITERTE VERSION"""
    
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
        self.auto_extract_archives: bool = False  # FIX: Standard auf False gesetzt
        self.delete_archives_after_extract: bool = False  # FIX: Standard auf False gesetzt
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
                
                # FIX: Korrekte Standard-Werte für Archive-Settings
                self.auto_extract_archives = data.get('auto_extract_archives', False)
                self.delete_archives_after_extract = data.get('delete_archives_after_extract', False)
                self.auto_cleanup_extracted_archives = data.get('auto_cleanup_extracted_archives', False)
                self.cleanup_extracted_archives_on_startup = data.get('cleanup_extracted_archives_on_startup', True)
                
                self.log_level = data.get('log_level', 'INFO')
                
                logging.info(f"Konfiguration geladen: {len(self.watch_folders)} Watch-Ordner, {len(self.target_folders)} Target-Ordner")
                
        except Exception as e:
            logging.error(f"Fehler beim Laden der Konfiguration: {e}")
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
                
            logging.info(f"Konfiguration gespeichert: {len(self.watch_folders)} Watch-Ordner, {len(self.target_folders)} Target-Ordner")
                
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Konfiguration: {e}")
    
    def _create_default_config(self) -> None:
        """Erstellt Standard-Konfiguration"""
        logging.info("Erstelle Standard-Konfiguration...")
        
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
            logging.info(f"Standard Watch-Ordner hinzugefügt: {downloads_path}")
        
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
            logging.info(f"Standard Target-Ordner hinzugefügt: {videos_path}")
        
        self.save_config()
    
    def add_watch_folder(self, path: str, name: str, **kwargs) -> bool:
        """Fügt neuen Überwachungsordner hinzu"""
        if not os.path.exists(path):
            logging.warning(f"Watch-Ordner existiert nicht: {path}")
            return False
        
        # Prüfen ob bereits vorhanden
        for folder in self.watch_folders:
            if folder.path == path:
                logging.warning(f"Watch-Ordner bereits vorhanden: {path}")
                return False
        
        self.watch_folders.append(WatchFolder(path=path, name=name, **kwargs))
        self.save_config()
        logging.info(f"Watch-Ordner hinzugefügt: {name} ({path})")
        return True
    
    def add_target_folder(self, path: str, name: str, **kwargs) -> bool:
        """Fügt neuen Zielordner hinzu"""
        if not os.path.exists(path):
            logging.warning(f"Target-Ordner existiert nicht: {path}")
            return False
        
        # Prüfen ob bereits vorhanden
        for folder in self.target_folders:
            if folder.path == path:
                logging.warning(f"Target-Ordner bereits vorhanden: {path}")
                return False
        
        self.target_folders.append(TargetFolder(path=path, name=name, **kwargs))
        self.save_config()
        logging.info(f"Target-Ordner hinzugefügt: {name} ({path})")
        return True
    
    # FIX: Methoden zum Entfernen von Ordnern hinzugefügt
    def remove_watch_folder(self, path: str) -> bool:
        """Entfernt Überwachungsordner"""
        for i, folder in enumerate(self.watch_folders):
            if folder.path == path:
                removed_folder = self.watch_folders.pop(i)
                self.save_config()
                logging.info(f"Watch-Ordner entfernt: {removed_folder.name} ({path})")
                return True
        
        logging.warning(f"Watch-Ordner nicht gefunden: {path}")
        return False
    
    def remove_target_folder(self, path: str) -> bool:
        """Entfernt Zielordner"""
        for i, folder in enumerate(self.target_folders):
            if folder.path == path:
                removed_folder = self.target_folders.pop(i)
                self.save_config()
                logging.info(f"Target-Ordner entfernt: {removed_folder.name} ({path})")
                return True
        
        logging.warning(f"Target-Ordner nicht gefunden: {path}")
        return False
    
    def get_watch_folder_by_path(self, path: str) -> Optional[WatchFolder]:
        """Findet Watch-Ordner nach Pfad"""
        for folder in self.watch_folders:
            if folder.path == path:
                return folder
        return None
    
    def get_target_folder_by_path(self, path: str) -> Optional[TargetFolder]:
        """Findet Target-Ordner nach Pfad"""
        for folder in self.target_folders:
            if folder.path == path:
                return folder
        return None
    
    def update_watch_folder(self, path: str, **kwargs) -> bool:
        """Aktualisiert Watch-Ordner-Eigenschaften"""
        folder = self.get_watch_folder_by_path(path)
        if folder:
            for key, value in kwargs.items():
                if hasattr(folder, key):
                    setattr(folder, key, value)
            self.save_config()
            logging.info(f"Watch-Ordner aktualisiert: {folder.name} ({path})")
            return True
        return False
    
    def update_target_folder(self, path: str, **kwargs) -> bool:
        """Aktualisiert Target-Ordner-Eigenschaften"""
        folder = self.get_target_folder_by_path(path)
        if folder:
            for key, value in kwargs.items():
                if hasattr(folder, key):
                    setattr(folder, key, value)
            self.save_config()
            logging.info(f"Target-Ordner aktualisiert: {folder.name} ({path})")
            return True
        return False
    
    def get_enabled_watch_folders(self) -> List[WatchFolder]:
        """Gibt nur aktivierte Watch-Ordner zurück"""
        return [folder for folder in self.watch_folders if folder.enabled]
    
    def get_enabled_target_folders(self) -> List[TargetFolder]:
        """Gibt nur aktivierte Target-Ordner zurück"""
        return [folder for folder in self.target_folders if folder.enabled]
    
    def validate_folders(self) -> Dict[str, List[str]]:
        """Validiert alle konfigurierten Ordner"""
        issues = {
            'missing_watch_folders': [],
            'missing_target_folders': [],
            'duplicate_watch_paths': [],
            'duplicate_target_paths': []
        }
        
        # Watch-Ordner prüfen
        watch_paths = []
        for folder in self.watch_folders:
            if not os.path.exists(folder.path):
                issues['missing_watch_folders'].append(f"{folder.name} ({folder.path})")
            
            if folder.path in watch_paths:
                issues['duplicate_watch_paths'].append(folder.path)
            else:
                watch_paths.append(folder.path)
        
        # Target-Ordner prüfen
        target_paths = []
        for folder in self.target_folders:
            if not os.path.exists(folder.path):
                issues['missing_target_folders'].append(f"{folder.name} ({folder.path})")
            
            if folder.path in target_paths:
                issues['duplicate_target_paths'].append(folder.path)
            else:
                target_paths.append(folder.path)
        
        return issues
    
    def get_file_type(self, filepath: str) -> FileType:
        """Bestimmt Dateityp basierend auf Erweiterung"""
        ext = Path(filepath).suffix.lower()
        if ext in self.video_extensions:
            return FileType.VIDEO
        elif ext in self.archive_extensions:
            return FileType.ARCHIVE
        else:
            return FileType.OTHER
    
    def get_config_summary(self) -> Dict:
        """Gibt Konfigurations-Zusammenfassung zurück"""
        validation = self.validate_folders()
        
        return {
            'folder_counts': {
                'watch_folders': len(self.watch_folders),
                'target_folders': len(self.target_folders),
                'enabled_watch_folders': len(self.get_enabled_watch_folders()),
                'enabled_target_folders': len(self.get_enabled_target_folders())
            },
            'extensions': {
                'video_extensions': len(self.video_extensions),
                'archive_extensions': len(self.archive_extensions)
            },
            'settings': {
                'auto_extract_archives': self.auto_extract_archives,
                'delete_archives_after_extract': self.delete_archives_after_extract,
                'auto_cleanup_extracted_archives': self.auto_cleanup_extracted_archives,
                'cleanup_extracted_archives_on_startup': self.cleanup_extracted_archives_on_startup,
                'min_file_size_mb': self.min_file_size_mb,
                'download_stability_seconds': self.download_stability_seconds
            },
            'validation': validation,
            'has_issues': any(len(issues) > 0 for issues in validation.values())
        }


# Logging Setup - ERWEITERT
def setup_logging(config: Config) -> None:
    """Initialisiert Logging-System"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    
    # Bestehende Handler entfernen um Duplikate zu vermeiden
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # File Handler mit Rotation
    try:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            'filemanager.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(log_format))
        file_handler.setLevel(log_level)
    except Exception as e:
        # Fallback zu normalem FileHandler
        file_handler = logging.FileHandler('filemanager.log')
        file_handler.setFormatter(logging.Formatter(log_format))
        file_handler.setLevel(log_level)
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    console_handler.setLevel(log_level)
    
    # Root Logger konfigurieren
    logging.basicConfig(
        level=log_level,
        handlers=[file_handler, console_handler]
    )
    
    # Externe Bibliotheken weniger verbose machen
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


if __name__ == "__main__":
    # Test der Basis-Klassen
    config = Config()
    setup_logging(config)
    
    print("=== Konfiguration Test ===")
    summary = config.get_config_summary()
    print(f"Watch Folders: {summary['folder_counts']['watch_folders']}")
    print(f"Target Folders: {summary['folder_counts']['target_folders']}")
    print(f"Video Extensions: {summary['extensions']['video_extensions']}")
    print(f"Archive Extensions: {summary['extensions']['archive_extensions']}")
    
    if summary['has_issues']:
        print("\n⚠️ Konfigurationsprobleme gefunden:")
        for issue_type, issues in summary['validation'].items():
            if issues:
                print(f"  {issue_type}: {issues}")
    else:
        print("\n✅ Konfiguration ist gültig")
    
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
    
    print("\n=== Test VideoFile ===")
    print(json.dumps(test_video.to_dict(), indent=2))
    
    # Test Ordner-Management
    print("\n=== Test Ordner-Management ===")
    
    # Temporären Test-Ordner erstellen
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = str(temp_dir)
        
        # Watch-Ordner hinzufügen
        success = config.add_watch_folder(temp_path, "Test Watch")
        print(f"Watch-Ordner hinzugefügt: {success}")
        
        # Target-Ordner hinzufügen
        success = config.add_target_folder(temp_path, "Test Target")
        print(f"Target-Ordner hinzugefügt: {success}")
        
        # Ordner-Info anzeigen
        watch_folders = config.get_enabled_watch_folders()
        target_folders = config.get_enabled_target_folders()
        print(f"Enabled Watch Folders: {len(watch_folders)}")
        print(f"Enabled Target Folders: {len(target_folders)}")
        
        # Ordner entfernen
        success = config.remove_watch_folder(temp_path)
        print(f"Watch-Ordner entfernt: {success}")
        
        success = config.remove_target_folder(temp_path)
        print(f"Target-Ordner entfernt: {success}")
    
    print("\n=== Test abgeschlossen ===")