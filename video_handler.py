"""
File Manager Backend - Teil 5: Video Handler
Intelligente Sortierung und Organisation von Video-Dateien
"""

import os
import shutil
import logging
import threading
from typing import Dict, List, Optional, Callable, Tuple
from pathlib import Path
from dataclasses import asdict
import re

from base import Config, VideoFile, FileStatus, FileType
from video_pattern_analyzer import VideoPatternAnalyzer


class VideoMover:
    """
    Klasse zum sicheren Verschieben von Video-Dateien
    Behandelt Duplikate und Ordner-Struktur intelligent
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def move_video(self, source_path: str, target_folder: str, 
                   series_name: str, episode_info: Optional[Dict] = None) -> Dict:
        """
        Verschiebt Video in Ziel-Ordner mit intelligenter Organisation
        
        Args:
            source_path: Quell-Pfad der Video-Datei
            target_folder: Basis-Zielordner
            series_name: Name der Serie
            episode_info: Dict mit Episode/Season-Infos
            
        Returns:
            Dict mit Bewegungs-Resultat
        """
        if not os.path.exists(source_path):
            return {
                'success': False,
                'error': 'Quell-Datei nicht gefunden',
                'source_path': source_path
            }
        
        try:
            # Ziel-Ordner für Serie bestimmen/erstellen
            series_folder = self._get_or_create_series_folder(target_folder, series_name)
            
            # Ziel-Dateinamen bestimmen
            target_filename = self._generate_target_filename(
                source_path, series_name, episode_info
            )
            
            target_path = os.path.join(series_folder, target_filename)
            
            # Prüfen ob Ziel bereits existiert
            if os.path.exists(target_path):
                duplicate_result = self._handle_duplicate(source_path, target_path, episode_info)
                if not duplicate_result['should_move']:
                    return duplicate_result
                
                # Neuen Namen für Duplikat generieren
                target_path = duplicate_result['new_target_path']
            
            # Dateibewegung durchführen
            self.logger.info(f"Verschiebe Video: {Path(source_path).name} -> {target_path}")
            
            # Sicherheitskopie falls gewünscht (konfigurierbar)
            shutil.move(source_path, target_path)
            
            # Berechtigungen setzen (falls nötig)
            self._set_file_permissions(target_path)
            
            return {
                'success': True,
                'source_path': source_path,
                'target_path': target_path,
                'series_folder': series_folder,
                'message': f'Video erfolgreich verschoben'
            }
            
        except Exception as e:
            self.logger.error(f"Fehler beim Verschieben von {source_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'source_path': source_path
            }
    
    def _get_or_create_series_folder(self, base_folder: str, series_name: str) -> str:
        """Bestimmt/erstellt Ordner für Serie"""
        # Ordner-Name bereinigen
        safe_series_name = self._sanitize_folder_name(series_name)
        series_folder = os.path.join(base_folder, safe_series_name)
        
        # Ordner erstellen falls nicht vorhanden
        os.makedirs(series_folder, exist_ok=True)
        
        return series_folder
    
    def _sanitize_folder_name(self, name: str) -> str:
        """Bereinigt Namen für Ordner-Verwendung"""
        # Ungültige Zeichen für Ordner-Namen entfernen/ersetzen
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, ' ')
        
        # Mehrfache Leerzeichen entfernen
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Windows-reservierte Namen vermeiden
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL'] + \
                        [f'COM{i}' for i in range(1, 10)] + \
                        [f'LPT{i}' for i in range(1, 10)]
        
        if name.upper() in reserved_names:
            name = f"{name}_series"
        
        # Maximale Länge begrenzen
        if len(name) > 200:
            name = name[:200].strip()
        
        return name
    
    def _generate_target_filename(self, source_path: str, series_name: str, 
                                episode_info: Optional[Dict]) -> str:
        """Generiert bereinigten Ziel-Dateinamen"""
        source_file = Path(source_path)
        extension = source_file.suffix
        
        # Basis-Name aus Serie und Episode-Info
        if episode_info and episode_info.get('episode_number'):
            episode_num = episode_info['episode_number']
            season_num = episode_info.get('season_number', 1)
            
            # Format: "Serie Name - S01E05.mp4"
            filename = f"{series_name} - S{season_num:02d}E{episode_num:02d}{extension}"
        else:
            # Fallback: Original-Name beibehalten aber bereinigen
            filename = self._sanitize_filename(source_file.name)
        
        return filename
    
    def _sanitize_filename(self, filename: str) -> str:
        """Bereinigt Dateinamen"""
        # Ungültige Zeichen entfernen
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Mehrfache Unterstriche/Punkte bereinigen
        filename = re.sub(r'[_.]{2,}', '_', filename)
        filename = filename.strip('_. ')
        
        return filename
    
    def _handle_duplicate(self, source_path: str, target_path: str, 
                         episode_info: Optional[Dict]) -> Dict:
        """Behandelt Duplikat-Dateien intelligent"""
        
        # Dateigröße vergleichen
        source_size = os.path.getsize(source_path)
        target_size = os.path.getsize(target_path)
        
        self.logger.info(f"Duplikat gefunden: {Path(target_path).name}")
        self.logger.info(f"  Quelle: {source_size:,} Bytes")
        self.logger.info(f"  Ziel:   {target_size:,} Bytes")
        
        # Wenn Dateien gleich groß sind, wahrscheinlich identisch
        if abs(source_size - target_size) < 1024:  # 1KB Toleranz
            return {
                'success': True,
                'should_move': False,
                'action': 'skipped_identical',
                'message': 'Identische Datei bereits vorhanden, Quelle wird übersprungen'
            }
        
        # Größere Datei bevorzugen (bessere Qualität)
        if source_size > target_size:
            # Neue Datei ist größer -> alte ersetzen
            try:
                os.remove(target_path)
                return {
                    'success': True,
                    'should_move': True,
                    'new_target_path': target_path,
                    'action': 'replaced_smaller',
                    'message': 'Kleinere Datei durch größere ersetzt'
                }
            except Exception as e:
                self.logger.error(f"Fehler beim Löschen der alten Datei: {e}")
        
        # Kleinere/gleiche Datei -> mit Suffix verschieben
        counter = 1
        base_path = Path(target_path)
        while True:
            new_name = f"{base_path.stem}_{counter:02d}{base_path.suffix}"
            new_target = base_path.parent / new_name
            
            if not new_target.exists():
                return {
                    'success': True,
                    'should_move': True,
                    'new_target_path': str(new_target),
                    'action': 'renamed_duplicate',
                    'message': f'Als Duplikat mit Suffix _{counter:02d} gespeichert'
                }
            
            counter += 1
            if counter > 99:  # Sicherheits-Begrenzung
                return {
                    'success': False,
                    'should_move': False,
                    'error': 'Zu viele Duplikate vorhanden'
                }
    
    def _set_file_permissions(self, filepath: str) -> None:
        """Setzt angemessene Dateiberechtigungen"""
        try:
            # Nur unter Unix/Linux relevant
            if os.name == 'posix':
                os.chmod(filepath, 0o644)  # rw-r--r--
        except Exception as e:
            self.logger.debug(f"Konnte Berechtigungen nicht setzen für {filepath}: {e}")


class VideoHandler:
    """
    Hauptklasse für Video-Verarbeitung
    Verwaltet Warteschlange und organisiert Videos intelligent
    """
    
    def __init__(self, config: 'Config', video_analyzer: 'VideoPatternAnalyzer'):
        self.config = config
        self.video_analyzer = video_analyzer
        self.video_mover = VideoMover()
        self.logger = logging.getLogger(__name__)
        
        # Warteschlangen
        self.pending_videos: Dict[str, 'VideoFile'] = {}
        self.processing_videos: Dict[str, 'VideoFile'] = {}
        self.completed_videos: Dict[str, Dict] = {}
        
        # Callbacks
        self.status_callback: Optional[Callable] = None
        self.folder_selection_callback: Optional[Callable] = None
        
        # Thread-Sicherheit
        self.lock = threading.Lock()
        
        # Worker-Thread
        self.worker_thread = None
        self.worker_running = False
    
    def set_callbacks(self, 
                     status_callback: Optional[Callable] = None,
                     folder_selection_callback: Optional[Callable] = None) -> None:
        """Setzt Callback-Funktionen"""
        self.status_callback = status_callback
        self.folder_selection_callback = folder_selection_callback
    
    def add_video(self, video_file: 'VideoFile') -> None:
        """Fügt Video zur Verarbeitungsqueue hinzu"""
        
        # Prüfen ob bereits ein ähnliches Video existiert
        existing_check = self._check_for_existing_episode(video_file)
        if existing_check['exists']:
            self.logger.info(f"Episode bereits vorhanden: {video_file.series_name} E{video_file.episode_number}")
            video_file.status = FileStatus.REJECTED
            
            with self.lock:
                self.completed_videos[video_file.filepath] = {
                    **video_file.to_dict(),
                    'processing_result': existing_check
                }
            
            self._notify_status_change(video_file)
            return
        
        # Mögliche Ziel-Ordner finden
        target_suggestions = self._find_target_folders(video_file)
        video_file.target_folder = target_suggestions[0]['path'] if target_suggestions else None
        
        with self.lock:
            self.pending_videos[video_file.filepath] = video_file
            video_file.status = FileStatus.PENDING
        
        self.logger.info(f"Video zur Queue hinzugefügt: {video_file.series_name} E{video_file.episode_number}")
        self._notify_status_change(video_file)
        
        # Worker starten falls nötig
        if not self.worker_running:
            self.start_worker()
    
    def approve_video(self, filepath: str, target_folder: Optional[str] = None) -> bool:
        """Genehmigt Video für Verarbeitung"""
        with self.lock:
            if filepath in self.pending_videos:
                video_file = self.pending_videos[filepath]
                video_file.status = FileStatus.APPROVED
                
                if target_folder:
                    video_file.target_folder = target_folder
                
                self._notify_status_change(video_file)
                self.logger.info(f"Video genehmigt: {video_file.series_name} E{video_file.episode_number}")
                return True
        return False
    
    def approve_all_videos(self) -> int:
        """Genehmigt alle wartenden Videos"""
        approved_count = 0
        
        with self.lock:
            for video_file in self.pending_videos.values():
                if video_file.status == FileStatus.PENDING:
                    video_file.status = FileStatus.APPROVED
                    self._notify_status_change(video_file)
                    approved_count += 1
        
        if approved_count > 0:
            self.logger.info(f"Alle {approved_count} Videos genehmigt")
        
        return approved_count
    
    def update_video_metadata(self, filepath: str, series_name: str, 
                             episode_number: Optional[int] = None, 
                             season_number: Optional[int] = None) -> bool:
        """Aktualisiert Video-Metadaten manuell"""
        with self.lock:
            if filepath in self.pending_videos:
                video_file = self.pending_videos[filepath]
                
                # Metadaten aktualisieren
                video_file.series_name = series_name.strip()
                video_file.episode_number = episode_number
                video_file.season_number = season_number
                video_file.manual_override = True
                video_file.confidence = 1.0  # Manuelle Eingabe = 100% Confidence
                
                self.logger.info(f"Video-Metadaten manuell aktualisiert: {series_name} E{episode_number}")
                self._notify_status_change(video_file)
                return True
                
        return False
    
    def reject_video(self, filepath: str) -> bool:
        """Lehnt Video ab"""
        with self.lock:
            if filepath in self.pending_videos:
                video_file = self.pending_videos.pop(filepath)
                video_file.status = FileStatus.REJECTED
                
                self.completed_videos[filepath] = {
                    **video_file.to_dict(),
                    'processing_result': {
                        'success': True,
                        'action': 'rejected_by_user',
                        'message': 'Von Benutzer abgelehnt'
                    }
                }
                
                self._notify_status_change(video_file)
                self.logger.info(f"Video abgelehnt: {video_file.series_name}")
                return True
        return False
    
    def move_video_to_folder(self, filepath: str, target_folder: str, 
                           custom_filename: Optional[str] = None) -> bool:
        """Verschiebt Video in benutzerdefinierten Ordner"""
        with self.lock:
            if filepath in self.pending_videos:
                video_file = self.pending_videos[filepath]
                
                # Custom target setzen
                video_file.target_folder = target_folder
                
                # Custom Dateiname wenn gewünscht
                if custom_filename:
                    # Erweiterung beibehalten
                    original_ext = Path(video_file.filename).suffix
                    if not custom_filename.endswith(original_ext):
                        custom_filename += original_ext
                    
                    video_file.filename = custom_filename
                
                # Als custom move markieren
                video_file.manual_override = True
                
                self.logger.info(f"Video für Custom-Move vorbereitet: {video_file.filename} -> {target_folder}")
                self._notify_status_change(video_file)
                return True
                
        return False
    
    def _check_for_existing_episode(self, video_file: 'VideoFile') -> Dict:
        """Prüft ob Episode bereits in Ziel-Ordnern existiert"""
        
        for target_folder_config in self.config.target_folders:
            if not target_folder_config.enabled or not os.path.exists(target_folder_config.path):
                continue
            
            # Nach Serien-Ordner suchen
            series_folder = self.video_analyzer.find_existing_series_folder(
                video_file.series_name, [target_folder_config.path]
            )
            
            if series_folder and os.path.exists(series_folder):
                # Dateien im Serien-Ordner prüfen
                existing_episodes = self._scan_existing_episodes(series_folder)
                
                # Prüfen ob diese Episode bereits existiert
                if video_file.episode_number in existing_episodes:
                    existing_file = existing_episodes[video_file.episode_number]
                    
                    return {
                        'exists': True,
                        'existing_file': existing_file,
                        'series_folder': series_folder,
                        'action': 'skipped_existing',
                        'message': f'Episode {video_file.episode_number} bereits vorhanden'
                    }
        
        return {'exists': False}
    
    def _scan_existing_episodes(self, series_folder: str) -> Dict[int, str]:
        """Scannt Serien-Ordner nach vorhandenen Episoden"""
        episodes = {}
        
        try:
            for filename in os.listdir(series_folder):
                filepath = os.path.join(series_folder, filename)
                
                if os.path.isfile(filepath):
                    # Video-Datei analysieren
                    file_type = self.config.get_file_type(filepath)
                    if file_type == FileType.VIDEO:
                        metadata = self.video_analyzer.analyze_filename(filepath)
                        if metadata and metadata.episode_number:
                            episodes[metadata.episode_number] = filepath
        
        except Exception as e:
            self.logger.warning(f"Fehler beim Scannen von {series_folder}: {e}")
        
        return episodes
    
    def _find_target_folders(self, video_file: 'VideoFile') -> List[Dict]:
        """Findet passende Ziel-Ordner für Video"""
        suggestions = []
        
        for folder_config in self.config.target_folders:
            if not folder_config.enabled or not os.path.exists(folder_config.path):
                continue
            
            # Prüfen ob bereits Serien-Ordner existiert
            existing_series = self.video_analyzer.find_existing_series_folder(
                video_file.series_name, [folder_config.path]
            )
            
            suggestion = {
                'path': folder_config.path,
                'name': folder_config.name,
                'priority': folder_config.priority,
                'has_existing_series': bool(existing_series),
                'existing_series_path': existing_series,
                'free_space_gb': self._get_free_space_gb(folder_config.path)
            }
            
            # Höhere Priorität wenn Serie bereits existiert
            if existing_series:
                suggestion['priority'] += 10
            
            suggestions.append(suggestion)
        
        # Nach Priorität sortieren (höchste zuerst)
        suggestions.sort(key=lambda x: x['priority'], reverse=True)
        
        return suggestions
    
    def _get_free_space_gb(self, path: str) -> float:
        """Gibt freien Speicherplatz in GB zurück"""
        try:
            statvfs = os.statvfs(path)
            free_bytes = statvfs.f_frsize * statvfs.f_available
            return free_bytes / (1024**3)  # GB
        except:
            return 0.0
    
    def get_pending_videos(self) -> List[Dict]:
        """Gibt alle wartenden Videos mit Ziel-Vorschlägen zurück"""
        with self.lock:
            result = []
            for video_file in self.pending_videos.values():
                video_data = video_file.to_dict()
                
                # Ziel-Ordner-Vorschläge hinzufügen
                target_suggestions = self._find_target_folders(video_file)
                video_data['target_suggestions'] = target_suggestions
                
                result.append(video_data)
            
            return result
    
    def get_processing_videos(self) -> List[Dict]:
        """Gibt aktuell verarbeitete Videos zurück"""
        with self.lock:
            return [video.to_dict() for video in self.processing_videos.values()]
    
    def get_completed_videos(self) -> List[Dict]:
        """Gibt abgeschlossene Videos zurück"""
        with self.lock:
            return list(self.completed_videos.values())
    
    def start_worker(self) -> None:
        """Startet Worker-Thread"""
        if self.worker_running:
            return
        
        self.worker_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        self.logger.info("Video-Worker gestartet")
    
    def stop_worker(self) -> None:
        """Stoppt Worker-Thread"""
        self.worker_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=10)
        self.logger.info("Video-Worker gestoppt")
    
    def _worker_loop(self) -> None:
        """Haupt-Loop des Worker-Threads"""
        while self.worker_running:
            try:
                # Nächstes genehmigtes Video finden
                video_to_process = None
                
                with self.lock:
                    for filepath, video_file in self.pending_videos.items():
                        if video_file.status == FileStatus.APPROVED:
                            video_to_process = video_file
                            # Aus pending in processing verschieben
                            self.processing_videos[filepath] = self.pending_videos.pop(filepath)
                            break
                
                if video_to_process:
                    self._process_video(video_to_process)
                else:
                    # Keine Videos zu verarbeiten
                    threading.Event().wait(2)
                    
            except Exception as e:
                self.logger.error(f"Fehler im Video-Worker: {e}")
                threading.Event().wait(5)
    
    def _process_video(self, video_file: 'VideoFile') -> None:
        """Verarbeitet ein einzelnes Video"""
        filepath = video_file.filepath
        
        try:
            # Status auf processing setzen
            video_file.status = FileStatus.PROCESSING
            self._notify_status_change(video_file)
            
            self.logger.info(f"Beginne Video-Verarbeitung: {video_file.series_name} E{video_file.episode_number}")
            
            # Ziel-Ordner validieren
            if not video_file.target_folder or not os.path.exists(video_file.target_folder):
                # Fallback: Ersten verfügbaren Ziel-Ordner verwenden
                suggestions = self._find_target_folders(video_file)
                if not suggestions:
                    raise Exception("Kein gültiger Ziel-Ordner verfügbar")
                video_file.target_folder = suggestions[0]['path']
            
            # Episode-Informationen für Mover vorbereiten
            episode_info = {
                'episode_number': video_file.episode_number,
                'season_number': video_file.season_number
            }
            
            # Video verschieben
            move_result = self.video_mover.move_video(
                filepath,
                video_file.target_folder,
                video_file.series_name,
                episode_info
            )
            
            if move_result['success']:
                video_file.status = FileStatus.COMPLETED
                self.logger.info(f"Video erfolgreich verarbeitet: {video_file.series_name} E{video_file.episode_number}")
            else:
                video_file.status = FileStatus.ERROR
                self.logger.error(f"Video-Verarbeitung fehlgeschlagen: {move_result.get('error')}")
            
            # Aus processing entfernen und zu completed hinzufügen
            with self.lock:
                if filepath in self.processing_videos:
                    del self.processing_videos[filepath]
                
                self.completed_videos[filepath] = {
                    **video_file.to_dict(),
                    'processing_result': move_result
                }
            
            self._notify_status_change(video_file)
            
        except Exception as e:
            # Fehlerbehandlung
            video_file.status = FileStatus.ERROR
            self.logger.error(f"Unerwarteter Fehler bei Video-Verarbeitung {filepath}: {e}")
            
            with self.lock:
                if filepath in self.processing_videos:
                    del self.processing_videos[filepath]
                
                self.completed_videos[filepath] = {
                    **video_file.to_dict(),
                    'processing_result': {
                        'success': False,
                        'error': str(e)
                    }
                }
            
            self._notify_status_change(video_file)
    
    def _notify_status_change(self, video_file: 'VideoFile') -> None:
        """Benachrichtigt über Status-Änderungen"""
        if self.status_callback:
            try:
                self.status_callback(video_file)
            except Exception as e:
                self.logger.error(f"Fehler in Status-Callback: {e}")
    
    def get_statistics(self) -> Dict:
        """Gibt detaillierte Statistiken zurück"""
        with self.lock:
            stats = {
                'pending': len(self.pending_videos),
                'processing': len(self.processing_videos),
                'completed': len(self.completed_videos),
                'worker_running': self.worker_running
            }
            
            # Status-Verteilung der pending Videos
            status_count = {}
            for video in self.pending_videos.values():
                status = video.status.value
                status_count[status] = status_count.get(status, 0) + 1
            
            stats['pending_by_status'] = status_count
            
            # Erfolgs-Rate der completed Videos
            if self.completed_videos:
                successful = sum(1 for data in self.completed_videos.values() 
                               if data.get('processing_result', {}).get('success', False))
                stats['success_rate'] = successful / len(self.completed_videos)
            else:
                stats['success_rate'] = 0.0
            
            # Serie-Verteilung
            series_count = {}
            for video in self.pending_videos.values():
                series = video.series_name
                series_count[series] = series_count.get(series, 0) + 1
            
            stats['series_distribution'] = series_count
        
        return stats
    
    def cleanup_old_completed(self, max_age_hours: int = 24) -> int:
        """Räumt alte completed Videos aus dem Speicher auf"""
        import time
        
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        removed_count = 0
        
        with self.lock:
            to_remove = []
            for filepath, completed_data in self.completed_videos.items():
                detected_at = completed_data.get('detected_at', current_time)
                if detected_at < cutoff_time:
                    to_remove.append(filepath)
            
            for filepath in to_remove:
                del self.completed_videos[filepath]
                removed_count += 1
        
        if removed_count > 0:
            self.logger.info(f"Aufgeräumt: {removed_count} alte Video-Einträge entfernt")
        
        return removed_count


# Erweiterte Video Handler Klasse mit zusätzlichen Features
class SmartVideoHandler(VideoHandler):
    """
    Erweiterte Version mit intelligenten Features:
    - Batch-Verarbeitung
    - Serie-Gruppierung
    - Quality-Management
    """
    
    def __init__(self, config: 'Config', video_analyzer: 'VideoPatternAnalyzer'):
        super().__init__(config, video_analyzer)
        
        # Erweiterte Konfiguration
        self.batch_processing = True
        self.max_batch_size = 5
        self.quality_preferences = {
            '2160p': 100,  # 4K
            '1440p': 90,   # 2K
            '1080p': 80,   # Full HD
            '720p': 60,    # HD
            '480p': 30     # SD
        }
    
    def process_series_batch(self, series_name: str, target_folder: str) -> Dict:
        """Verarbeitet alle Videos einer Serie als Batch"""
        
        with self.lock:
            series_videos = [
                video for video in self.pending_videos.values()
                if video.series_name.lower() == series_name.lower()
                and video.status == FileStatus.PENDING
            ]
        
        if not series_videos:
            return {
                'success': False,
                'message': 'Keine wartenden Videos für diese Serie gefunden'
            }
        
        # Alle Videos der Serie genehmigen
        approved_count = 0
        for video in series_videos:
            video.target_folder = target_folder
            video.status = FileStatus.APPROVED
            self._notify_status_change(video)
            approved_count += 1
        
        self.logger.info(f"Batch-Verarbeitung gestartet für '{series_name}': {approved_count} Videos")
        
        return {
            'success': True,
            'series_name': series_name,
            'video_count': approved_count,
            'target_folder': target_folder,
            'message': f'{approved_count} Videos zur Batch-Verarbeitung genehmigt'
        }
    
    def get_series_overview(self) -> List[Dict]:
        """Gibt Übersicht aller Serien mit wartenden Videos zurück"""
        series_map = {}
        
        with self.lock:
            for video in self.pending_videos.values():
                series_name = video.series_name
                
                if series_name not in series_map:
                    series_map[series_name] = {
                        'series_name': series_name,
                        'video_count': 0,
                        'episodes': [],
                        'total_size_mb': 0,
                        'quality_distribution': {},
                        'target_suggestions': self._find_target_folders(video)
                    }
                
                series_info = series_map[series_name]
                series_info['video_count'] += 1
                series_info['total_size_mb'] += round(video.file_size / (1024*1024), 2)
                
                if video.episode_number:
                    series_info['episodes'].append(video.episode_number)
                
                # Quality-Info wenn verfügbar
                metadata = self.video_analyzer.analyze_filename(video.filepath)
                if metadata and metadata.resolution:
                    quality = metadata.resolution
                    series_info['quality_distribution'][quality] = \
                        series_info['quality_distribution'].get(quality, 0) + 1
        
        # Nach Video-Anzahl sortieren
        result = list(series_map.values())
        result.sort(key=lambda x: x['video_count'], reverse=True)
        
        # Episoden sortieren
        for series in result:
            series['episodes'].sort()
        
        return result
    
    def suggest_best_quality(self, series_videos: List['VideoFile']) -> List['VideoFile']:
        """Schlägt Videos mit bester Qualität vor (entfernt Duplikate niedrigerer Qualität)"""
        
        # Nach Episode gruppieren
        episodes = {}
        for video in series_videos:
            episode = video.episode_number
            if episode not in episodes:
                episodes[episode] = []
            episodes[episode].append(video)
        
        # Beste Qualität pro Episode wählen
        best_videos = []
        for episode, video_list in episodes.items():
            if len(video_list) == 1:
                best_videos.append(video_list[0])
                continue
            
            # Videos nach Qualität bewerten
            scored_videos = []
            for video in video_list:
                metadata = self.video_analyzer.analyze_filename(video.filepath)
                quality_score = 0
                
                if metadata and metadata.resolution:
                    quality_score = self.quality_preferences.get(metadata.resolution, 0)
                
                # Dateigröße als zusätzlicher Indikator
                size_score = video.file_size / (1024*1024*1024)  # GB
                
                total_score = quality_score + (size_score * 5)  # Gewichtung
                scored_videos.append((total_score, video))
            
            # Bestes Video wählen
            scored_videos.sort(key=lambda x: x[0], reverse=True)
            best_videos.append(scored_videos[0][1])
            
            # Andere als rejected markieren
            for score, video in scored_videos[1:]:
                video.status = FileStatus.REJECTED
                self.logger.info(f"Video wegen niedrigerer Qualität abgelehnt: {video.filename}")
        
        return best_videos


# Test und Demo
if __name__ == "__main__":
    import json
    import time
    from filemanager_backend_p1 import Config, setup_logging, VideoFile, FileStatus
    from filemanager_backend_p2 import VideoPatternAnalyzer
    
    # Setup
    config = Config()
    setup_logging(config)
    logger = logging.getLogger(__name__)
    
    # Analyzer und Handler
    analyzer = VideoPatternAnalyzer()
    handler = SmartVideoHandler(config, analyzer)
    
    # Test-Callbacks
    def video_status_callback(video_file):
        print(f"\n🎬 Video Status Update:")
        print(f"   Serie: {video_file.series_name}")
        print(f"   Episode: {video_file.episode_number}")
        print(f"   Status: {video_file.status.value}")
        if video_file.target_folder:
            print(f"   Ziel: {video_file.target_folder}")
    
    handler.set_callbacks(status_callback=video_status_callback)
    
    print("=== Video Handler Test ===")
    
    # Test-Videos erstellen (simuliert)
    test_videos = [
        {
            'filepath': '/downloads/Attack_on_Titan_S04E01_1080p.mkv',
            'series': 'Attack on Titan',
            'episode': 1,
            'season': 4,
            'size': 1024*1024*800  # 800MB
        },
        {
            'filepath': '/downloads/Attack_on_Titan_S04E02_720p.mkv', 
            'series': 'Attack on Titan',
            'episode': 2,
            'season': 4,
            'size': 1024*1024*600  # 600MB
        },
        {
            'filepath': '/downloads/One_Piece_1045.mp4',
            'series': 'One Piece',
            'episode': 1045,
            'season': 1,
            'size': 1024*1024*400  # 400MB
        }
    ]
    
    # Videos zur Queue hinzufügen
    for test_video in test_videos:
        video_file = VideoFile(
            filepath=test_video['filepath'],
            filename=Path(test_video['filepath']).name,
            series_name=test_video['series'],
            episode_number=test_video['episode'],
            season_number=test_video['season'],
            file_size=test_video['size'],
            status=FileStatus.PENDING,
            detected_at=time.time(),
            last_modified=time.time()
        )
        
        print(f"\nFüge Video hinzu: {video_file.series_name} E{video_file.episode_number}")
        handler.add_video(video_file)
    
    print("\n=== Serien-Übersicht ===")
    series_overview = handler.get_series_overview()
    for series in series_overview:
        print(f"\nSerie: {series['series_name']}")
        print(f"  Videos: {series['video_count']}")
        print(f"  Episoden: {series['episodes']}")
        print(f"  Größe: {series['total_size_mb']} MB")
        print(f"  Qualität: {series['quality_distribution']}")
    
    print(f"\n=== Statistiken ===")
    stats = handler.get_statistics()
    print(json.dumps(stats, indent=2))
    
    print(f"\n=== Wartende Videos ===")
    pending = handler.get_pending_videos()
    for video in pending:
        print(f"  {video['series_name']} E{video['episode_number']} - {video['filename']}")
        print(f"    Ziel-Vorschläge: {len(video['target_suggestions'])}")
    
    # Cleanup
    handler.stop_worker()