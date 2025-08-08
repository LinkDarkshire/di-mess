"""
File Manager Backend - Teil 3: File Monitor
Überwacht Ordner und erkennt neue Video/Archive-Dateien
"""

import os
import time
import threading
import logging
from typing import Dict, List, Callable, Optional, Set
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent
from base import Config, VideoFile, ArchiveFile, FileStatus, FileType
from video_pattern_analyzer import VideoPatternAnalyzer
from dataclasses import asdict

class DownloadMonitor:
    """
    Überwacht Dateien auf Vollständigkeit des Downloads
    Prüft ob Dateigröße stabil bleibt über einen Zeitraum
    """
    
    def __init__(self, stability_seconds: int = 30):
        self.stability_seconds = stability_seconds
        self.monitored_files: Dict[str, Dict] = {}
        self.logger = logging.getLogger(__name__)
        self.lock = threading.Lock()
        
        # Background-Thread für periodische Checks
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.running = False
        
    def start(self) -> None:
        """Startet die Download-Überwachung"""
        if not self.running:
            self.running = True
            self.monitor_thread.start()
            self.logger.info("Download Monitor gestartet")
    
    def stop(self) -> None:
        """Stoppt die Download-Überwachung"""
        self.running = False
        self.logger.info("Download Monitor gestoppt")
    
    def add_file(self, filepath: str, callback: Callable[[str], None]) -> None:
        """
        Fügt eine Datei zur Überwachung hinzu
        
        Args:
            filepath: Pfad zur Datei
            callback: Funktion die aufgerufen wird wenn Download komplett ist
        """
        if not os.path.exists(filepath):
            return
            
        with self.lock:
            file_info = {
                'path': filepath,
                'size': os.path.getsize(filepath),
                'last_modified': os.path.getmtime(filepath),
                'stable_since': time.time(),
                'callback': callback,
                'notified': False
            }
            
            self.monitored_files[filepath] = file_info
            self.logger.debug(f"Datei zur Download-Überwachung hinzugefügt: {filepath}")
    
    def remove_file(self, filepath: str) -> None:
        """Entfernt eine Datei aus der Überwachung"""
        with self.lock:
            if filepath in self.monitored_files:
                del self.monitored_files[filepath]
                self.logger.debug(f"Datei aus Download-Überwachung entfernt: {filepath}")
    
    def _monitor_loop(self) -> None:
        """Haupt-Loop für die Überwachung"""
        while self.running:
            try:
                with self.lock:
                    files_to_check = list(self.monitored_files.items())
                
                current_time = time.time()
                files_to_remove = []
                
                for filepath, file_info in files_to_check:
                    # Prüfen ob Datei noch existiert
                    if not os.path.exists(filepath):
                        files_to_remove.append(filepath)
                        continue
                    
                    # Aktuelle Dateigröße und Änderungszeit prüfen
                    try:
                        current_size = os.path.getsize(filepath)
                        current_modified = os.path.getmtime(filepath)
                        
                        # Hat sich die Datei geändert?
                        if (current_size != file_info['size'] or 
                            current_modified != file_info['last_modified']):
                            # Datei hat sich geändert - Timer zurücksetzen
                            file_info['size'] = current_size
                            file_info['last_modified'] = current_modified
                            file_info['stable_since'] = current_time
                            file_info['notified'] = False
                            self.logger.debug(f"Datei-Änderung erkannt: {filepath} (Größe: {current_size})")
                        
                        # Ist die Datei lange genug stabil?
                        stable_duration = current_time - file_info['stable_since']
                        if (stable_duration >= self.stability_seconds and 
                            not file_info['notified']):
                            # Download ist vollständig!
                            file_info['notified'] = True
                            self.logger.info(f"Download vollständig: {filepath} (stabil seit {stable_duration:.1f}s)")
                            
                            # Callback ausführen
                            try:
                                file_info['callback'](filepath)
                            except Exception as e:
                                self.logger.error(f"Fehler in Download-Callback für {filepath}: {e}")
                            
                            # Datei aus Überwachung entfernen
                            files_to_remove.append(filepath)
                    
                    except (OSError, IOError) as e:
                        self.logger.warning(f"Fehler beim Prüfen von {filepath}: {e}")
                        files_to_remove.append(filepath)
                
                # Fertige Dateien entfernen
                with self.lock:
                    for filepath in files_to_remove:
                        self.monitored_files.pop(filepath, None)
                
                time.sleep(5)  # Alle 5 Sekunden prüfen
                
            except Exception as e:
                self.logger.error(f"Fehler in Download-Monitor Loop: {e}")
                time.sleep(10)


class FileSystemEventHandler(FileSystemEventHandler):
    """Handler für Dateisystem-Ereignisse"""
    
    def __init__(self, file_monitor: 'FileMonitor'):
        super().__init__()
        self.file_monitor = file_monitor
        self.logger = logging.getLogger(__name__)
    
    def on_created(self, event):
        """Neue Datei erstellt"""
        if not event.is_directory:
            self.logger.debug(f"Datei erstellt: {event.src_path}")
            self.file_monitor.handle_file_event(event.src_path, 'created')
    
    def on_modified(self, event):
        """Datei geändert"""
        if not event.is_directory:
            # Nur loggen bei signifikanten Änderungen
            self.file_monitor.handle_file_event(event.src_path, 'modified')


class FileMonitor:
    """
    Hauptklasse für die Überwachung von Ordnern
    Erkennt neue Video- und Archive-Dateien
    """
    
    def __init__(self, config: 'Config', video_analyzer: 'VideoPatternAnalyzer'):
        self.config = config
        self.video_analyzer = video_analyzer
        self.download_monitor = DownloadMonitor(config.download_stability_seconds)
        self.logger = logging.getLogger(__name__)
        
        # Watchdog Observer
        self.observer = Observer()
        self.event_handler = FileSystemEventHandler(self)
        
        # Callbacks für Events
        self.video_found_callback: Optional[Callable] = None
        self.archive_found_callback: Optional[Callable] = None
        
        # Sets für bereits verarbeitete Dateien
        self.processed_files: Set[str] = set()
        self.ignored_files: Set[str] = set()
        
        # Lock für Thread-Sicherheit
        self.lock = threading.Lock()
        
        self.running = False
    
    def set_callbacks(self, 
                     video_callback: Optional[Callable] = None,
                     archive_callback: Optional[Callable] = None) -> None:
        """Setzt Callback-Funktionen für gefundene Dateien"""
        self.video_found_callback = video_callback
        self.archive_found_callback = archive_callback
    
    def start(self) -> None:
        """Startet die Ordner-Überwachung"""
        if self.running:
            return
        
        self.running = True
        self.download_monitor.start()
        
        # Alle konfigurierten Ordner überwachen
        for watch_folder in self.config.watch_folders:
            if not watch_folder.enabled or not os.path.exists(watch_folder.path):
                continue
            
            self.observer.schedule(
                self.event_handler,
                watch_folder.path,
                recursive=watch_folder.recursive
            )
            self.logger.info(f"Überwache Ordner: {watch_folder.path} (rekursiv: {watch_folder.recursive})")
        
        self.observer.start()
        
        # Initial Scan aller Ordner
        self._initial_scan()
        
        self.logger.info("File Monitor gestartet")
    
    def stop(self) -> None:
        """Stoppt die Ordner-Überwachung"""
        if not self.running:
            return
        
        self.running = False
        self.observer.stop()
        self.observer.join()
        self.download_monitor.stop()
        
        self.logger.info("File Monitor gestoppt")
    
    def _initial_scan(self) -> None:
        """Scannt alle Überwachungsordner initial nach existierenden Dateien"""
        self.logger.info("Starte initialen Ordner-Scan...")
        
        for watch_folder in self.config.watch_folders:
            if not watch_folder.enabled or not os.path.exists(watch_folder.path):
                continue
            
            try:
                self._scan_folder_with_depth(watch_folder)
                        
            except Exception as e:
                self.logger.error(f"Fehler beim initialen Scan von {watch_folder.path}: {e}")
        
        self.logger.info("Initialer Ordner-Scan abgeschlossen")
    
    def _scan_folder_with_depth(self, watch_folder: 'WatchFolder') -> None:
        """Scannt Ordner unter Berücksichtigung der Video-Suchtiefe"""
        base_path = watch_folder.path
        max_depth = watch_folder.video_search_depth
        
        # Archiv-Dateien - immer nur oberste Ebene für Archive
        if watch_folder.watch_archives:
            for filename in os.listdir(base_path):
                filepath = os.path.join(base_path, filename)
                if os.path.isfile(filepath):
                    file_type = self.config.get_file_type(filepath)
                    if file_type == FileType.ARCHIVE:
                        self.handle_file_event(filepath, 'initial')
        
        # Video-Dateien - mit konfigurierbare Tiefe
        if watch_folder.watch_videos:
            self._scan_videos_recursive(base_path, max_depth, 0)
    
    def _scan_videos_recursive(self, current_path: str, max_depth: int, current_depth: int) -> None:
        """Rekursive Video-Suche mit Tiefenbegrenzung"""
        if current_depth > max_depth:
            return
        
        try:
            for item in os.listdir(current_path):
                item_path = os.path.join(current_path, item)
                
                if os.path.isfile(item_path):
                    # Video-Datei gefunden
                    file_type = self.config.get_file_type(item_path)
                    if file_type == FileType.VIDEO:
                        self.handle_file_event(item_path, 'initial')
                
                elif os.path.isdir(item_path) and current_depth < max_depth:
                    # Tiefer in Unterordner gehen
                    self._scan_videos_recursive(item_path, max_depth, current_depth + 1)
                    
        except (PermissionError, OSError) as e:
            self.logger.warning(f"Kann Ordner nicht lesen: {current_path} - {e}")
    
    def _get_file_depth(self, filepath: str, base_path: str) -> int:
        """Berechnet Tiefe einer Datei relativ zum Basis-Pfad"""
        try:
            rel_path = os.path.relpath(filepath, base_path)
            return len(Path(rel_path).parts) - 1  # -1 weil Datei selbst nicht zählt
        except ValueError:
            return 0
    
    def handle_file_event(self, filepath: str, event_type: str) -> None:
        """
        Verarbeitet ein Dateisystem-Event
        
        Args:
            filepath: Pfad zur Datei
            event_type: Art des Events ('created', 'modified', 'initial')
        """
        # Bereits verarbeitete oder ignorierte Dateien überspringen
        with self.lock:
            if filepath in self.processed_files or filepath in self.ignored_files:
                return
        
        # Prüfen ob Datei in erlaubter Tiefe liegt (nur bei Videos)
        file_type = self.config.get_file_type(filepath)
        
        if file_type == FileType.VIDEO:
            # Prüfe Video-Suchtiefe
            if not self._is_video_in_allowed_depth(filepath):
                with self.lock:
                    self.ignored_files.add(filepath)
                return
            
            self._handle_video_file(filepath, event_type)
        elif file_type == FileType.ARCHIVE:
            self._handle_archive_file(filepath, event_type)
        else:
            # Andere Dateitypen ignorieren
            with self.lock:
                self.ignored_files.add(filepath)
    
    def _is_video_in_allowed_depth(self, filepath: str) -> bool:
        """Prüft ob Video-Datei in erlaubter Suchtiefe liegt"""
        for watch_folder in self.config.watch_folders:
            if not watch_folder.enabled or not watch_folder.watch_videos:
                continue
                
            # Prüfen ob Datei in diesem Überwachungsordner liegt
            try:
                rel_path = os.path.relpath(filepath, watch_folder.path)
                if rel_path.startswith('..'):
                    continue  # Nicht in diesem Ordner
                
                depth = self._get_file_depth(filepath, watch_folder.path)
                if depth <= watch_folder.video_search_depth:
                    return True
                    
            except (ValueError, OSError):
                continue
        
        return False
    
    def _handle_video_file(self, filepath: str, event_type: str) -> None:
        """Verarbeitet eine gefundene Video-Datei"""
        try:
            # Datei-Informationen sammeln
            if not os.path.exists(filepath):
                return
            
            file_size = os.path.getsize(filepath)
            
            # Zu kleine Dateien ignorieren
            min_size_bytes = self.config.min_file_size_mb * 1024 * 1024
            if file_size < min_size_bytes:
                with self.lock:
                    self.ignored_files.add(filepath)
                return
            
            # Video-Metadaten analysieren - IMMER versuchen zu analysieren
            metadata = self.video_analyzer.analyze_filename(filepath)
            
            # VideoFile-Objekt erstellen - auch wenn keine/schwache Erkennung
            if metadata and metadata.confidence >= 0.3:  # Niedrigere Schwelle
                # Gute Erkennung
                video_file = VideoFile(
                    filepath=filepath,
                    filename=Path(filepath).name,
                    series_name=metadata.series_name,
                    episode_number=metadata.episode_number,
                    season_number=metadata.season_number,
                    file_size=file_size,
                    status=FileStatus.PENDING,
                    detected_at=time.time(),
                    last_modified=os.path.getmtime(filepath),
                    confidence=metadata.confidence,
                    manual_override=False,
                    original_filename=Path(filepath).name
                )
                
                self.logger.info(f"Video erkannt: {metadata.series_name} E{metadata.episode_number} (Confidence: {metadata.confidence:.2f})")
                
            else:
                # Schwache/keine Erkennung - trotzdem als Video behandeln
                filename_clean = Path(filepath).stem  # Ohne Erweiterung
                
                video_file = VideoFile(
                    filepath=filepath,
                    filename=Path(filepath).name,
                    series_name=filename_clean,  # Dateiname als Fallback
                    episode_number=None,
                    season_number=None,
                    file_size=file_size,
                    status=FileStatus.PENDING,
                    detected_at=time.time(),
                    last_modified=os.path.getmtime(filepath),
                    confidence=metadata.confidence if metadata else 0.0,
                    manual_override=False,
                    original_filename=Path(filepath).name
                )
                
                self.logger.info(f"Video gefunden (manuelle Bearbeitung nötig): {Path(filepath).name}")
            
            # Als verarbeitet markieren
            with self.lock:
                self.processed_files.add(filepath)
            
            # Je nach Event-Typ unterschiedlich behandeln
            if event_type == 'initial':
                # Bei initialem Scan sofort als vollständig behandeln
                self._notify_video_found(video_file)
            else:
                # Bei neuen Dateien auf Download-Vollständigkeit warten
                self.logger.info(f"Neue Video-Datei erkannt, warte auf Download-Vollständigkeit: {Path(filepath).name}")
                self.download_monitor.add_file(
                    filepath,
                    lambda fp: self._notify_video_found(video_file)
                )
        
        except Exception as e:
            self.logger.error(f"Fehler bei Video-Datei-Verarbeitung {filepath}: {e}")
    
    def _handle_archive_file(self, filepath: str, event_type: str) -> None:
        """Verarbeitet eine gefundene Archive-Datei"""
        try:
            if not os.path.exists(filepath):
                return
            
            file_size = os.path.getsize(filepath)
            
            # ArchiveFile-Objekt erstellen
            from filemanager_backend_p1 import ArchiveFile, FileStatus
            archive_file = ArchiveFile(
                filepath=filepath,
                filename=Path(filepath).name,
                file_size=file_size,
                status=FileStatus.PENDING,
                detected_at=time.time(),
                last_modified=os.path.getmtime(filepath)
            )
            
            # Als verarbeitet markieren
            with self.lock:
                self.processed_files.add(filepath)
            
            # Je nach Event-Typ unterschiedlich behandeln
            if event_type == 'initial':
                self._notify_archive_found(archive_file)
            else:
                self.logger.info(f"Neue Archive-Datei erkannt, warte auf Download-Vollständigkeit: {Path(filepath).name}")
                self.download_monitor.add_file(
                    filepath,
                    lambda fp: self._notify_archive_found(archive_file)
                )
        
        except Exception as e:
            self.logger.error(f"Fehler bei Archive-Datei-Verarbeitung {filepath}: {e}")
    
    def _notify_video_found(self, video_file: 'VideoFile') -> None:
        """Benachrichtigt über gefundene Video-Datei"""
        self.logger.info(f"Video-Datei bereit: {video_file.series_name} E{video_file.episode_number}")
        
        if self.video_found_callback:
            try:
                self.video_found_callback(video_file)
            except Exception as e:
                self.logger.error(f"Fehler in Video-Callback: {e}")
    
    def _notify_archive_found(self, archive_file: 'ArchiveFile') -> None:
        """Benachrichtigt über gefundene Archive-Datei"""
        self.logger.info(f"Archive-Datei bereit: {archive_file.filename}")
        
        if self.archive_found_callback:
            try:
                self.archive_found_callback(archive_file)
            except Exception as e:
                self.logger.error(f"Fehler in Archive-Callback: {e}")
    
    def get_stats(self) -> Dict:
        """Gibt Statistiken über überwachte Dateien zurück"""
        with self.lock:
            return {
                'processed_files': len(self.processed_files),
                'ignored_files': len(self.ignored_files),
                'monitoring_downloads': len(self.download_monitor.monitored_files),
                'watched_folders': len([f for f in self.config.watch_folders if f.enabled])
            }


# Test-Code
if __name__ == "__main__":
    import sys
    import json
    from filemanager_backend_p1 import Config, setup_logging
    from filemanager_backend_p2 import VideoPatternAnalyzer
    
    # Logging setup
    config = Config()
    setup_logging(config)
    logger = logging.getLogger(__name__)
    
    # Video Analyzer
    analyzer = VideoPatternAnalyzer()
    
    # Test Callbacks
    def on_video_found(video_file):
        print(f"\n🎬 VIDEO GEFUNDEN:")
        print(json.dumps(video_file.to_dict(), indent=2))
    
    def on_archive_found(archive_file):
        print(f"\n📦 ARCHIVE GEFUNDEN:")
        print(json.dumps(archive_file.to_dict(), indent=2))
    
    # File Monitor erstellen
    monitor = FileMonitor(config, analyzer)
    monitor.set_callbacks(on_video_found, on_archive_found)
    
    print("=== File Monitor Test ===")
    print("Drücke Ctrl+C zum Beenden\n")
    
    try:
        monitor.start()
        
        # Status alle 30 Sekunden ausgeben
        while True:
            time.sleep(30)
            stats = monitor.get_stats()
            print(f"\n📊 Status: {stats}")
            
    except KeyboardInterrupt:
        print("\nStoppe File Monitor...")
        monitor.stop()
        print("Beendet.")