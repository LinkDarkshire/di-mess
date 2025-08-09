"""
File Manager Backend - Teil 4: Archive Handler
Automatisches Entpacken von ZIP, RAR und anderen Archiven
"""

import os
import shutil
import zipfile
import logging
import threading
import time
from typing import Optional, List, Dict, Callable
from pathlib import Path
from dataclasses import asdict
from base import Config, FileType, FileStatus, ArchiveFile

try:
    import rarfile  # pip install rarfile
    RARFILE_AVAILABLE = True
except ImportError:
    RARFILE_AVAILABLE = False
    logging.warning("rarfile nicht verfügbar - RAR-Archive können nicht entpackt werden")

try:
    import py7zr  # pip install py7zr
    PY7ZR_AVAILABLE = True
except ImportError:
    PY7ZR_AVAILABLE = False
    logging.warning("py7zr nicht verfügbar - 7z-Archive können nicht entpackt werden")


class ArchiveExtractor:
    """
    Klasse zum Entpacken verschiedener Archive-Formate
    Unterstützt ZIP, RAR, 7Z und andere Formate
    """
    
    def get_startup_cleanup_candidates(self) -> List[Dict]:
        """Gibt Archive zurück die Benutzer-Bestätigung für Cleanup brauchen"""
        return self.cleanup_candidates
    
    def approve_cleanup_candidate(self, archive_path: str, action: str) -> Dict:
        """
        Genehmigt Cleanup-Aktion für ein Archive
        
        Args:
            archive_path: Pfad zum Archive
            action: 'delete' oder 'extract'
        """
        try:
            result = self.startup_cleanup.cleanup_archive_by_user_choice(archive_path, action)
            
            # Aus Cleanup-Kandidaten entfernen
            self.cleanup_candidates = [
                c for c in self.cleanup_candidates 
                if c['archive_path'] != archive_path
            ]
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def approve_all_cleanup_candidates(self, action: str) -> Dict:
        """
        Führt Aktion für alle Cleanup-Kandidaten aus
        
        Args:
            action: 'delete' (alle löschen) oder 'extract' (alle entpacken)
        """
        results = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'details': []
        }
        
        candidates_copy = self.cleanup_candidates.copy()
        
        for candidate in candidates_copy:
            archive_path = candidate['archive_path']
            result = self.approve_cleanup_candidate(archive_path, action)
            
            results['total_processed'] += 1
            if result['success']:
                results['successful'] += 1
            else:
                results['failed'] += 1
            
            results['details'].append({
                'archive_path': archive_path,
                'archive_name': candidate['archive_name'],
                'result': result
            })
        
        return results
    
    def add_archive(self, archive_file: ArchiveFile) -> None:
        """Erweiterte Archive-Hinzufügung mit Smart-Check"""
        
        # Prüfen ob bereits entpackt
        if self._is_already_extracted(archive_file):
            self.logger.info(f"Archive bereits entpackt, überspringe: {archive_file.filename}")
            
            # Direkt als completed markieren
            archive_file.status = FileStatus.COMPLETED
            with self.lock:
                self.completed_archives[archive_file.filepath] = {
                    **archive_file.to_dict(),
                    'processing_result': {
                        'success': True,
                        'already_extracted': True,
                        'message': 'Archive war bereits entpackt'
                    }
                }
            
            # Optional: Archive löschen wenn konfiguriert
            if self.config.delete_archives_after_extract:
                self._safe_delete_archive(archive_file.filepath)
            
            self._notify_status_change(archive_file)
            return
        
        # Normal zur Queue hinzufügen
        super().add_archive(archive_file)
    
    def _is_already_extracted(self, archive_file: ArchiveFile) -> bool:
        """Prüft ob Archive bereits entpackt wurde"""
        archive_path = archive_file.filepath
        
        # Cache prüfen
        if archive_path in self.archive_cache:
            cache_entry = self.archive_cache[archive_path]
            # Cache ist noch gültig wenn Archive nicht geändert wurde
            if cache_entry['modified_time'] == archive_file.last_modified:
                return cache_entry['is_extracted']
        
        # Erwarteter Entpack-Ordner
        extract_path = os.path.splitext(archive_path)[0]
        
        is_extracted = False
        
        # Prüfen ob Ordner existiert und Dateien enthält
        if os.path.exists(extract_path) and os.path.isdir(extract_path):
            try:
                # Prüfen ob Ordner nicht leer ist
                files_in_dir = list(os.listdir(extract_path))
                if files_in_dir:
                    # Erweiterte Prüfung: Mindestens eine Datei mit sinnvoller Größe
                    for filename in files_in_dir:
                        filepath = os.path.join(extract_path, filename)
                        if os.path.isfile(filepath) and os.path.getsize(filepath) > 0:
                            is_extracted = True
                            break
            except (OSError, PermissionError):
                pass
        
        # Alternative Ordner-Namen prüfen (häufige Varianten)
        if not is_extracted:
            base_name = Path(archive_path).stem
            parent_dir = Path(archive_path).parent
            
            # Varianten: "Archive Name", "Archive_Name", etc.
            name_variants = [
                base_name,
                base_name.replace('_', ' '),
                base_name.replace('-', ' '),
                base_name.replace('.', ' ')
            ]
            
            for variant in name_variants:
                variant_path = parent_dir / variant
                if variant_path.exists() and variant_path.is_dir():
                    try:
                        files_in_dir = list(variant_path.iterdir())
                        if any(f.is_file() and f.stat().st_size > 0 for f in files_in_dir):
                            is_extracted = True
                            extract_path = str(variant_path)
                            break
                    except (OSError, PermissionError):
                        continue
        
        # Cache aktualisieren
        self.archive_cache[archive_path] = {
            'modified_time': archive_file.last_modified,
            'is_extracted': is_extracted,
            'extract_path': extract_path if is_extracted else None
        }
        
        return is_extracted
    
    def _safe_delete_archive(self, archive_path: str) -> bool:
        """Sicher Archive löschen mit Backup-Option"""
        try:
            # Optional: Backup erstellen (konfigurierbar)
            if hasattr(self.config, 'create_archive_backup') and self.config.create_archive_backup:
                backup_dir = Path(archive_path).parent / '.archive_backup'
                backup_dir.mkdir(exist_ok=True)
                backup_path = backup_dir / Path(archive_path).name
                shutil.move(archive_path, backup_path)
                self.logger.info(f"Archive in Backup verschoben: {backup_path}")
            else:
                os.remove(archive_path)
                self.logger.info(f"Archive gelöscht: {Path(archive_path).name}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Fehler beim Löschen des Archives {archive_path}: {e}")
            return False
    
    def get_statistics(self) -> Dict:
        """Gibt detaillierte Statistiken zurück"""
        with self.lock:
            stats = {
                'pending': len(self.pending_archives),
                'processing': len(self.processing_archives),
                'completed': len(self.completed_archives),
                'cache_entries': len(self.archive_cache),
                'worker_running': self.worker_running
            }
            
            # Status-Verteilung der pending Archives
            status_count = {}
            for archive in self.pending_archives.values():
                status = archive.status.value
                status_count[status] = status_count.get(status, 0) + 1
            
            stats['pending_by_status'] = status_count
            
            # Erfolgs-Rate der completed Archives
            if self.completed_archives:
                successful = sum(1 for data in self.completed_archives.values() 
                               if data.get('processing_result', {}).get('success', False))
                stats['success_rate'] = successful / len(self.completed_archives)
            else:
                stats['success_rate'] = 0.0
        
        return stats __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Mapping von Dateierweiterungen zu Extraktions-Methoden
        self.extractors = {
            '.zip': self._extract_zip,
            '.rar': self._extract_rar,
            '.7z': self._extract_7z,
            '.tar': self._extract_tar,
            '.tar.gz': self._extract_tar,
            '.tar.bz2': self._extract_tar,
            '.tar.xz': self._extract_tar,
        }
    
    def can_extract(self, filepath: str) -> bool:
        """Prüft ob die Datei entpackt werden kann"""
        ext = self._get_extension(filepath)
        return ext in self.extractors
    
    def extract(self, archive_path: str, extract_to: Optional[str] = None) -> Dict:
        """
        Entpackt ein Archive
        
        Args:
            archive_path: Pfad zum Archive
            extract_to: Zielordner (optional, sonst neben Archive)
            
        Returns:
            Dict mit Status und Informationen
        """
        if not os.path.exists(archive_path):
            return {
                'success': False,
                'error': 'Archive-Datei nicht gefunden',
                'archive_path': archive_path
            }
        
        # Zielordner bestimmen
        if extract_to is None:
            extract_to = os.path.splitext(archive_path)[0]
        
        # Prüfen ob bereits entpackt
        if os.path.exists(extract_to) and os.listdir(extract_to):
            return {
                'success': True,
                'already_extracted': True,
                'archive_path': archive_path,
                'extract_path': extract_to,
                'message': 'Archive bereits entpackt'
            }
        
        # Zielordner erstellen
        os.makedirs(extract_to, exist_ok=True)
        
        # Entsprechende Extraktions-Methode aufrufen
        ext = self._get_extension(archive_path)
        if ext not in self.extractors:
            return {
                'success': False,
                'error': f'Nicht unterstütztes Format: {ext}',
                'archive_path': archive_path
            }
        
        try:
            self.logger.info(f"Entpacke Archive: {Path(archive_path).name} -> {extract_to}")
            
            extractor_func = self.extractors[ext]
            result = extractor_func(archive_path, extract_to)
            
            if result['success']:
                # Entpackte Dateien zählen
                file_count = self._count_files_recursive(extract_to)
                result.update({
                    'archive_path': archive_path,
                    'extract_path': extract_to,
                    'file_count': file_count,
                    'message': f'Archive erfolgreich entpackt ({file_count} Dateien)'
                })
                
                self.logger.info(f"Archive erfolgreich entpackt: {file_count} Dateien in {extract_to}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Fehler beim Entpacken von {archive_path}: {e}")
            
            # Aufräumen bei Fehler
            if os.path.exists(extract_to):
                try:
                    shutil.rmtree(extract_to)
                except:
                    pass
            
            return {
                'success': False,
                'error': str(e),
                'archive_path': archive_path
            }
    
    def _get_extension(self, filepath: str) -> str:
        """Bestimmt die Dateierweiterung (auch für .tar.gz etc.)"""
        path = Path(filepath)
        
        # Spezialbehandlung für .tar.* Archive
        if path.suffixes:
            # Prüfe .tar.gz, .tar.bz2, .tar.xz
            if len(path.suffixes) >= 2 and path.suffixes[-2] == '.tar':
                return ''.join(path.suffixes[-2:])
            # Normale Erweiterung
            return path.suffix.lower()
        
        return ''
    
    def _extract_zip(self, archive_path: str, extract_to: str) -> Dict:
        """Entpackt ZIP-Archive"""
        try:
            with zipfile.ZipFile(archive_path, 'r') as zip_file:
                # Prüfe auf schädliche Pfade
                for member in zip_file.namelist():
                    if os.path.isabs(member) or ".." in member:
                        raise Exception(f"Unsicherer Pfad in Archive: {member}")
                
                zip_file.extractall(extract_to)
                return {'success': True}
                
        except zipfile.BadZipFile:
            return {'success': False, 'error': 'Beschädigte ZIP-Datei'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _extract_rar(self, archive_path: str, extract_to: str) -> Dict:
        """Entpackt RAR-Archive"""
        if not RARFILE_AVAILABLE:
            return {'success': False, 'error': 'rarfile-Bibliothek nicht verfügbar'}
        
        try:
            with rarfile.RarFile(archive_path, 'r') as rar_file:
                # Prüfe auf schädliche Pfade
                for member in rar_file.namelist():
                    if os.path.isabs(member) or ".." in member:
                        raise Exception(f"Unsicherer Pfad in Archive: {member}")
                
                rar_file.extractall(extract_to)
                return {'success': True}
                
        except rarfile.BadRarFile:
            return {'success': False, 'error': 'Beschädigte RAR-Datei'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _extract_7z(self, archive_path: str, extract_to: str) -> Dict:
        """Entpackt 7Z-Archive"""
        if not PY7ZR_AVAILABLE:
            return {'success': False, 'error': 'py7zr-Bibliothek nicht verfügbar'}
        
        try:
            with py7zr.SevenZipFile(archive_path, 'r') as seven_file:
                # Prüfe auf schädliche Pfade
                for member in seven_file.getnames():
                    if os.path.isabs(member) or ".." in member:
                        raise Exception(f"Unsicherer Pfad in Archive: {member}")
                
                seven_file.extractall(extract_to)
                return {'success': True}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _extract_tar(self, archive_path: str, extract_to: str) -> Dict:
        """Entpackt TAR-Archive (inkl. .tar.gz, .tar.bz2, etc.)"""
        import tarfile
        
        try:
            with tarfile.open(archive_path, 'r:*') as tar_file:
                # Prüfe auf schädliche Pfade
                for member in tar_file.getmembers():
                    if os.path.isabs(member.name) or ".." in member.name:
                        raise Exception(f"Unsicherer Pfad in Archive: {member.name}")
                
                tar_file.extractall(extract_to)
                return {'success': True}
                
        except tarfile.TarError:
            return {'success': False, 'error': 'Beschädigte TAR-Datei'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _count_files_recursive(self, directory: str) -> int:
        """Zählt alle Dateien rekursiv in einem Ordner"""
        count = 0
        try:
            for root, dirs, files in os.walk(directory):
                count += len(files)
        except Exception:
            pass
        return count


class StartupArchiveCleanup:
    """
    Prüft beim Start alle Archive-Dateien und bereinigt bereits entpackte
    """
    
    def __init__(self, config: Config, extractor: ArchiveExtractor):
        self.config = config
        self.extractor = extractor
        self.logger = logging.getLogger(__name__)
        
        # Ergebnisse des Startup-Scans
        self.found_archives: List[Dict] = []
        self.cleanup_candidates: List[Dict] = []
    
    def scan_for_extracted_archives(self) -> Dict:
        """
        Scannt alle Überwachungsordner nach Archive-Dateien mit bereits 
        existierenden entpackten Ordnern
        """
        self.logger.info("Starte Startup Archive-Cleanup Scan...")
        
        total_archives = 0
        cleanup_candidates = 0
        auto_cleaned = 0
        
        for watch_folder in self.config.watch_folders:
            if not watch_folder.enabled or not watch_folder.watch_archives:
                continue
            
            if not os.path.exists(watch_folder.path):
                continue
            
            try:
                # Nur oberste Ebene für Archive scannen
                for filename in os.listdir(watch_folder.path):
                    filepath = os.path.join(watch_folder.path, filename)
                    
                    if os.path.isfile(filepath):
                        file_type = self.config.get_file_type(filepath)
                        
                        if file_type == FileType.ARCHIVE:
                            total_archives += 1
                            result = self._check_archive_status(filepath)
                            
                            self.found_archives.append(result)
                            
                            if result['has_extracted_folder']:
                                cleanup_candidates += 1
                                self.cleanup_candidates.append(result)
                                
                                # Auto-cleanup wenn konfiguriert
                                if self.config.auto_cleanup_extracted_archives:
                                    if self._auto_cleanup_archive(result):
                                        auto_cleaned += 1
            
            except Exception as e:
                self.logger.error(f"Fehler beim Scannen von {watch_folder.path}: {e}")
        
        result = {
            'total_archives_found': total_archives,
            'cleanup_candidates': cleanup_candidates,
            'auto_cleaned': auto_cleaned,
            'needs_user_confirmation': len(self.cleanup_candidates) - auto_cleaned,
            'candidates': self.cleanup_candidates if not self.config.auto_cleanup_extracted_archives else []
        }
        
        self.logger.info(f"Archive-Cleanup Scan abgeschlossen: {total_archives} Archive gefunden, "
                        f"{cleanup_candidates} Cleanup-Kandidaten, {auto_cleaned} automatisch bereinigt")
        
        return result
    
    def _check_archive_status(self, archive_path: str) -> Dict:
        """Prüft Status eines Archives (entpackt oder nicht)"""
        archive_info = {
            'archive_path': archive_path,
            'archive_name': Path(archive_path).name,
            'archive_size_mb': round(os.path.getsize(archive_path) / (1024*1024), 2),
            'has_extracted_folder': False,
            'extracted_folder_path': None,
            'extracted_folder_size_mb': 0.0,
            'file_count_in_extracted': 0,
            'recommended_action': 'extract'  # 'extract' oder 'delete'
        }
        
        # Erwartete Pfade für entpackten Ordner
        possible_extract_paths = self._get_possible_extract_paths(archive_path)
        
        for extract_path in possible_extract_paths:
            if os.path.exists(extract_path) and os.path.isdir(extract_path):
                # Prüfen ob Ordner Dateien enthält
                file_count = self._count_files_recursive(extract_path)
                if file_count > 0:
                    # Ordner existiert und enthält Dateien
                    archive_info.update({
                        'has_extracted_folder': True,
                        'extracted_folder_path': extract_path,
                        'extracted_folder_size_mb': self._get_folder_size_mb(extract_path),
                        'file_count_in_extracted': file_count,
                        'recommended_action': 'delete'
                    })
                    break
        
        return archive_info
    
    def _get_possible_extract_paths(self, archive_path: str) -> List[str]:
        """Gibt mögliche Pfade für entpackte Ordner zurück"""
        base_path = Path(archive_path)
        parent_dir = base_path.parent
        
        # Verschiedene mögliche Namen
        base_name = base_path.stem
        
        possible_names = [
            base_name,  # archive -> archive/
            base_name.replace('_', ' '),  # archive_name -> archive name/
            base_name.replace('-', ' '),  # archive-name -> archive name/
            base_name.replace('.', ' '),  # archive.name -> archive name/
        ]
        
        # Entfernen Sie häufige Archive-Suffixe
        for suffix in ['.part1', '.part01', '.vol1', '.vol01']:
            if base_name.endswith(suffix):
                clean_name = base_name[:-len(suffix)]
                possible_names.append(clean_name)
        
        # Zu absolute Pfade konvertieren
        return [str(parent_dir / name) for name in possible_names]
    
    def _count_files_recursive(self, directory: str) -> int:
        """Zählt alle Dateien rekursiv in einem Ordner"""
        count = 0
        try:
            for root, dirs, files in os.walk(directory):
                count += len(files)
        except Exception:
            pass
        return count
    
    def _get_folder_size_mb(self, directory: str) -> float:
        """Berechnet Ordnergröße in MB"""
        total_size = 0
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    filepath = os.path.join(root, file)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception:
            pass
        
        return round(total_size / (1024*1024), 2)
    
    def _auto_cleanup_archive(self, archive_info: Dict) -> bool:
        """Führt automatische Bereinigung durch"""
        try:
            archive_path = archive_info['archive_path']
            
            self.logger.info(f"Auto-Cleanup: Lösche bereits entpacktes Archive {archive_info['archive_name']}")
            os.remove(archive_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Fehler beim Auto-Cleanup von {archive_info['archive_path']}: {e}")
            return False
    
    def cleanup_archive_by_user_choice(self, archive_path: str, action: str) -> Dict:
        """
        Führt Benutzer-gewählte Aktion aus
        
        Args:
            archive_path: Pfad zum Archive
            action: 'delete' (löschen) oder 'extract' (entpacken)
        """
        try:
            if action == 'delete':
                os.remove(archive_path)
                return {
                    'success': True,
                    'action': 'deleted',
                    'message': f'Archive gelöscht: {Path(archive_path).name}'
                }
            
            elif action == 'extract':
                # Archive entpacken über ArchiveExtractor
                result = self.extractor.extract(archive_path)
                
                if result['success']:
                    # Nach erfolgreichem Entpacken löschen wenn konfiguriert
                    if self.config.delete_archives_after_extract:
                        os.remove(archive_path)
                        result['archive_deleted'] = True
                    
                    return {
                        'success': True,
                        'action': 'extracted',
                        'message': f'Archive entpackt: {result.get("file_count", 0)} Dateien',
                        'extract_result': result
                    }
                else:
                    return {
                        'success': False,
                        'action': 'extract_failed',
                        'error': result.get('error', 'Unbekannter Fehler')
                    }
            
            else:
                return {
                    'success': False,
                    'error': f'Unbekannte Aktion: {action}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class ArchiveHandler:
    """
    Hauptklasse für Archive-Verarbeitung
    Verwaltet die Warteschlange und führt Aktionen aus
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.extractor = ArchiveExtractor()
        self.logger = logging.getLogger(__name__)
        
        # Warteschlange für Archive-Verarbeitung
        self.pending_archives: Dict[str, ArchiveFile] = {}
        self.processing_archives: Dict[str, ArchiveFile] = {}
        self.completed_archives: Dict[str, Dict] = {}
        
        # Callback für Status-Updates
        self.status_callback: Optional[Callable] = None
        
        # Thread-Sicherheit
        self.lock = threading.Lock()
        
        # Worker-Thread für Verarbeitung
        self.worker_thread = None
        self.worker_running = False
    
    def set_status_callback(self, callback: Callable) -> None:
        """Setzt Callback für Status-Updates"""
        self.status_callback = callback
    
    def add_archive(self, archive_file: ArchiveFile) -> None:
        """Fügt Archive zur Verarbeitungsqueue hinzu"""
        with self.lock:
            self.pending_archives[archive_file.filepath] = archive_file
            archive_file.status = FileStatus.PENDING
        
        self.logger.info(f"Archive zur Queue hinzugefügt: {archive_file.filename}")
        self._notify_status_change(archive_file)
        
        # Worker-Thread starten falls nötig
        if not self.worker_running:
            self.start_worker()
    
    def approve_archive(self, filepath: str) -> bool:
        """Genehmigt ein Archive für die Verarbeitung"""
        with self.lock:
            if filepath in self.pending_archives:
                archive_file = self.pending_archives[filepath]
                archive_file.status = FileStatus.APPROVED
                self._notify_status_change(archive_file)
                self.logger.info(f"Archive genehmigt: {archive_file.filename}")
                return True
        return False
    
    def reject_archive(self, filepath: str) -> bool:
        """Lehnt ein Archive ab"""
        with self.lock:
            if filepath in self.pending_archives:
                archive_file = self.pending_archives.pop(filepath)
                archive_file.status = FileStatus.REJECTED
                self._notify_status_change(archive_file)
                self.logger.info(f"Archive abgelehnt: {archive_file.filename}")
                return True
        return False
    
    def get_pending_archives(self) -> List[Dict]:
        """Gibt alle wartenden Archive zurück"""
        with self.lock:
            return [archive.to_dict() for archive in self.pending_archives.values()]
    
    def get_processing_archives(self) -> List[Dict]:
        """Gibt alle gerade verarbeiteten Archive zurück"""
        with self.lock:
            return [archive.to_dict() for archive in self.processing_archives.values()]
    
    def get_completed_archives(self) -> List[Dict]:
        """Gibt alle abgeschlossenen Archive zurück"""
        with self.lock:
            return list(self.completed_archives.values())
    
    def start_worker(self) -> None:
        """Startet den Worker-Thread"""
        if self.worker_running:
            return
        
        self.worker_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        self.logger.info("Archive-Worker gestartet")
    
    def stop_worker(self) -> None:
        """Stoppt den Worker-Thread"""
        self.worker_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=10)
        self.logger.info("Archive-Worker gestoppt")
    
    def _worker_loop(self) -> None:
        """Haupt-Loop des Worker-Threads"""
        while self.worker_running:
            try:
                # Nächstes genehmigte Archive finden
                archive_to_process = None
                
                with self.lock:
                    for filepath, archive_file in self.pending_archives.items():
                        if archive_file.status == FileStatus.APPROVED:
                            archive_to_process = archive_file
                            # Aus pending in processing verschieben
                            self.processing_archives[filepath] = self.pending_archives.pop(filepath)
                            break
                
                if archive_to_process:
                    self._process_archive(archive_to_process)
                else:
                    # Kein Archive zu verarbeiten, kurz warten
                    threading.Event().wait(2)
                    
            except Exception as e:
                self.logger.error(f"Fehler im Archive-Worker: {e}")
                threading.Event().wait(5)
    
    def _process_archive(self, archive_file: ArchiveFile) -> None:
        """Verarbeitet ein einzelnes Archive"""
        filepath = archive_file.filepath
        
        try:
            # Status auf processing setzen
            archive_file.status = FileStatus.PROCESSING
            self._notify_status_change(archive_file)
            
            self.logger.info(f"Beginne Verarbeitung von: {archive_file.filename}")
            
            # Archive entpacken
            result = self.extractor.extract(filepath)
            
            if result['success']:
                archive_file.status = FileStatus.COMPLETED
                archive_file.extract_path = result.get('extract_path')
                
                # Archive löschen wenn konfiguriert
                if self.config.delete_archives_after_extract:
                    try:
                        os.remove(filepath)
                        self.logger.info(f"Archive-Datei gelöscht: {archive_file.filename}")
                        result['archive_deleted'] = True
                    except Exception as e:
                        self.logger.warning(f"Konnte Archive nicht löschen {filepath}: {e}")
                        result['archive_deleted'] = False
                
                self.logger.info(f"Archive erfolgreich verarbeitet: {archive_file.filename}")
                
            else:
                archive_file.status = FileStatus.ERROR
                self.logger.error(f"Archive-Verarbeitung fehlgeschlagen: {archive_file.filename} - {result.get('error')}")
            
            # Aus processing entfernen und zu completed hinzufügen
            with self.lock:
                if filepath in self.processing_archives:
                    del self.processing_archives[filepath]
                
                self.completed_archives[filepath] = {
                    **archive_file.to_dict(),
                    'processing_result': result
                }
            
            self._notify_status_change(archive_file)
            
        except Exception as e:
            # Fehlerbehandlung
            archive_file.status = FileStatus.ERROR
            self.logger.error(f"Unerwarteter Fehler bei Archive-Verarbeitung {filepath}: {e}")
            
            with self.lock:
                if filepath in self.processing_archives:
                    del self.processing_archives[filepath]
                
                self.completed_archives[filepath] = {
                    **archive_file.to_dict(),
                    'processing_result': {
                        'success': False,
                        'error': str(e)
                    }
                }
            
            self._notify_status_change(archive_file)
    
    def _notify_status_change(self, archive_file: ArchiveFile) -> None:
        """Benachrichtigt über Status-Änderungen"""
        if self.status_callback:
            try:
                self.status_callback(archive_file)
            except Exception as e:
                self.logger.error(f"Fehler in Status-Callback: {e}")
    
    def cleanup_old_completed(self, max_age_hours: int = 24) -> int:
        """Räumt alte completed Archive aus dem Speicher auf"""
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        removed_count = 0
        
        with self.lock:
            to_remove = []
            for filepath, completed_data in self.completed_archives.items():
                detected_at = completed_data.get('detected_at', current_time)
                if detected_at < cutoff_time:
                    to_remove.append(filepath)
            
            for filepath in to_remove:
                del self.completed_archives[filepath]
                removed_count += 1
        
        if removed_count > 0:
            self.logger.info(f"Aufgeräumt: {removed_count} alte Archive-Einträge entfernt")
        
        return removed_count
    
    def get_statistics(self) -> Dict:
        """Gibt detaillierte Statistiken zurück"""
        with self.lock:
            stats = {
                'pending': len(self.pending_archives),
                'processing': len(self.processing_archives),
                'completed': len(self.completed_archives),
                'worker_running': self.worker_running
            }
            
            # Status-Verteilung der pending Archives
            status_count = {}
            for archive in self.pending_archives.values():
                status = archive.status.value
                status_count[status] = status_count.get(status, 0) + 1
            
            stats['pending_by_status'] = status_count
            
            # Erfolgs-Rate der completed Archives
            if self.completed_archives:
                successful = sum(1 for data in self.completed_archives.values() 
                               if data.get('processing_result', {}).get('success', False))
                stats['success_rate'] = successful / len(self.completed_archives)
            else:
                stats['success_rate'] = 0.0
        
        return stats


class SmartArchiveHandler(ArchiveHandler):
    """
    Erweiterte Version des ArchiveHandlers mit intelligenten Features
    - Erkennt bereits entpackte Archive
    - Vermeidet doppelte Entpackung
    - Verwaltet Ordner-Struktur intelligent
    - Startup-Cleanup für bereits entpackte Archive
    """
    
    def __init__(self, config: Config):
        super().__init__(config)
        
        # Cache für bereits geprüfte Archive
        self.archive_cache: Dict[str, Dict] = {}
        
        # Startup-Cleanup Manager
        self.startup_cleanup = StartupArchiveCleanup(config, self.extractor)
        
        # Cleanup-Status
        self.startup_cleanup_completed = False
        self.cleanup_candidates: List[Dict] = []
    
    def perform_startup_cleanup(self) -> Dict:
        """
        Führt Startup-Cleanup durch - prüft bereits entpackte Archive
        """
        if not self.config.cleanup_extracted_archives_on_startup:
            return {
                'cleanup_enabled': False,
                'message': 'Startup-Cleanup ist deaktiviert'
            }
        
        self.logger.info("Starte Archive Startup-Cleanup...")
        
        try:
            cleanup_result = self.startup_cleanup.scan_for_extracted_archives()
            
            # Wenn nicht auto-cleanup, Kandidaten für Benutzer-Bestätigung sammeln  
            if not self.config.auto_cleanup_extracted_archives and cleanup_result['cleanup_candidates'] > 0:
                self.cleanup_candidates = self.startup_cleanup.cleanup_candidates.copy()
            
            self.startup_cleanup_completed = True
            
            return {
                'cleanup_enabled': True,
                'success': True,
                **cleanup_result
            }
            
        except Exception as e:
            self.logger.error(f"Fehler beim Startup-Cleanup: {e}")
            return {
                'cleanup_enabled': True,
                'success': False,
                'error': str(e)
            }
    
    def