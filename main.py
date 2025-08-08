#!/usr/bin/env python3
"""
File Manager Backend - Main Application
Korrigierte Version mit richtigen Imports
"""

import os
import sys
import time
import logging
import threading
from typing import Dict, List, Optional, Callable
from pathlib import Path

# Flask für REST API
from flask import Flask, request, jsonify
from flask_cors import CORS
import werkzeug.exceptions

# Lokale Imports - korrigierte Reihenfolge
from base import Config, setup_logging, FileStatus, FileType, VideoFile, ArchiveFile
from video_pattern_analyzer import VideoPatternAnalyzer
from file_monitor import FileMonitor
from archive_handler import SmartArchiveHandler
from video_handler import SmartVideoHandler


class FileManagerAPI:
    """
    REST API für die Kommunikation mit dem Frontend
    Stellt alle Funktionen über HTTP-Endpunkte zur Verfügung
    """
    
    def __init__(self, file_manager: 'FileManager'):
        self.file_manager = file_manager
        self.app = Flask(__name__)
        CORS(self.app)  # Für Frontend-Zugriff
        
        self.logger = logging.getLogger(__name__)
        
        # Fehlerbehandlung
        self.app.register_error_handler(404, self._handle_404)
        self.app.register_error_handler(500, self._handle_500)
        
        # Routes registrieren
        self._register_routes()
    
    def _register_routes(self) -> None:
        """Registriert alle API-Endpunkte"""
        
        # Status und Info
        self.app.route('/api/status', methods=['GET'])(self.get_status)
        self.app.route('/api/statistics', methods=['GET'])(self.get_statistics)
        
        # Konfiguration
        self.app.route('/api/config', methods=['GET'])(self.get_config)
        self.app.route('/api/config', methods=['POST'])(self.update_config)
        self.app.route('/api/config/folders/watch', methods=['POST'])(self.add_watch_folder)
        self.app.route('/api/config/folders/target', methods=['POST'])(self.add_target_folder)
        
        # Video-Management
        self.app.route('/api/videos/pending', methods=['GET'])(self.get_pending_videos)
        self.app.route('/api/videos/processing', methods=['GET'])(self.get_processing_videos)
        self.app.route('/api/videos/completed', methods=['GET'])(self.get_completed_videos)
        self.app.route('/api/videos/series', methods=['GET'])(self.get_series_overview)
        
        self.app.route('/api/videos/<path:filepath>/approve', methods=['POST'])(self.approve_video)
        self.app.route('/api/videos/<path:filepath>/reject', methods=['POST'])(self.reject_video)
        self.app.route('/api/videos/<path:filepath>/update', methods=['POST'])(self.update_video_metadata)
        self.app.route('/api/videos/<path:filepath>/move-custom', methods=['POST'])(self.move_video_custom)
        self.app.route('/api/videos/approve-all', methods=['POST'])(self.approve_all_videos)
        self.app.route('/api/videos/series/<series_name>/batch', methods=['POST'])(self.process_series_batch)
        
        # Archive-Management  
        self.app.route('/api/archives/pending', methods=['GET'])(self.get_pending_archives)
        self.app.route('/api/archives/processing', methods=['GET'])(self.get_processing_archives)
        self.app.route('/api/archives/completed', methods=['GET'])(self.get_completed_archives)
        
        self.app.route('/api/archives/<path:filepath>/approve', methods=['POST'])(self.approve_archive)
        self.app.route('/api/archives/<path:filepath>/reject', methods=['POST'])(self.reject_archive)
        
        # Startup Cleanup Endpunkte
        self.app.route('/api/archives/startup-cleanup/status', methods=['GET'])(self.get_startup_cleanup_status)
        self.app.route('/api/archives/startup-cleanup/candidates', methods=['GET'])(self.get_startup_cleanup_candidates)
        self.app.route('/api/archives/startup-cleanup/<path:filepath>/approve', methods=['POST'])(self.approve_cleanup_candidate)
        self.app.route('/api/archives/startup-cleanup/approve-all', methods=['POST'])(self.approve_all_cleanup_candidates)
        
        # System-Kontrolle
        self.app.route('/api/system/start', methods=['POST'])(self.start_monitoring)
        self.app.route('/api/system/stop', methods=['POST'])(self.stop_monitoring)
        self.app.route('/api/system/cleanup', methods=['POST'])(self.cleanup_old_entries)
    
    # Status und Info Endpunkte
    def get_status(self):
        """Gibt aktuellen System-Status zurück"""
        try:
            status = self.file_manager.get_system_status()
            return jsonify({
                'success': True,
                'data': status
            })
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def get_statistics(self):
        """Gibt detaillierte Statistiken zurück"""
        try:
            stats = self.file_manager.get_detailed_statistics()
            return jsonify({
                'success': True,
                'data': stats
            })
        except Exception as e:
            return self._error_response(str(e), 500)
    
    # Konfigurations-Endpunkte
    def get_config(self):
        """Gibt aktuelle Konfiguration zurück"""
        try:
            config_data = {
                'watch_folders': [vars(f) for f in self.file_manager.config.watch_folders],
                'target_folders': [vars(f) for f in self.file_manager.config.target_folders],
                'video_extensions': list(self.file_manager.config.video_extensions),
                'archive_extensions': list(self.file_manager.config.archive_extensions),
                'settings': {
                    'min_file_size_mb': self.file_manager.config.min_file_size_mb,
                    'download_stability_seconds': self.file_manager.config.download_stability_seconds,
                    'enable_notifications': self.file_manager.config.enable_notifications,
                    'auto_extract_archives': self.file_manager.config.auto_extract_archives,
                    'delete_archives_after_extract': self.file_manager.config.delete_archives_after_extract,
                    'auto_cleanup_extracted_archives': self.file_manager.config.auto_cleanup_extracted_archives,
                    'cleanup_extracted_archives_on_startup': self.file_manager.config.cleanup_extracted_archives_on_startup
                }
            }
            
            return jsonify({
                'success': True,
                'data': config_data
            })
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def update_config(self):
        """Aktualisiert Konfiguration"""
        try:
            data = request.get_json()
            
            # Settings aktualisieren
            if 'settings' in data:
                settings = data['settings']
                for key, value in settings.items():
                    if hasattr(self.file_manager.config, key):
                        setattr(self.file_manager.config, key, value)
            
            # Direkte settings (für Kompatibilität)
            for key, value in data.items():
                if key != 'settings' and hasattr(self.file_manager.config, key):
                    setattr(self.file_manager.config, key, value)
            
            # Konfiguration speichern
            self.file_manager.config.save_config()
            
            return jsonify({
                'success': True,
                'message': 'Konfiguration aktualisiert'
            })
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def add_watch_folder(self):
        """Fügt neuen Überwachungsordner hinzu"""
        try:
            data = request.get_json()
            path = data.get('path')
            name = data.get('name', Path(path).name)
            
            success = self.file_manager.config.add_watch_folder(path, name, **data)
            
            if success:
                # Monitoring neu starten um neuen Ordner zu überwachen
                self.file_manager.restart_monitoring()
                
                return jsonify({
                    'success': True,
                    'message': f'Überwachungsordner hinzugefügt: {name}'
                })
            else:
                return self._error_response('Ordner konnte nicht hinzugefügt werden', 400)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def add_target_folder(self):
        """Fügt neuen Zielordner hinzu"""
        try:
            data = request.get_json()
            path = data.get('path')
            name = data.get('name', Path(path).name)
            
            success = self.file_manager.config.add_target_folder(path, name, **data)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f'Zielordner hinzugefügt: {name}'
                })
            else:
                return self._error_response('Ordner konnte nicht hinzugefügt werden', 400)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    # Video-Management Endpunkte
    def get_pending_videos(self):
        """Gibt wartende Videos zurück"""
        try:
            videos = self.file_manager.video_handler.get_pending_videos()
            return jsonify({
                'success': True,
                'data': videos,
                'count': len(videos)
            })
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def get_processing_videos(self):
        """Gibt verarbeitete Videos zurück"""
        try:
            videos = self.file_manager.video_handler.get_processing_videos()
            return jsonify({
                'success': True,
                'data': videos,
                'count': len(videos)
            })
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def get_completed_videos(self):
        """Gibt abgeschlossene Videos zurück"""
        try:
            videos = self.file_manager.video_handler.get_completed_videos()
            return jsonify({
                'success': True,
                'data': videos,
                'count': len(videos)
            })
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def get_series_overview(self):
        """Gibt Serien-Übersicht zurück"""
        try:
            series = self.file_manager.video_handler.get_series_overview()
            return jsonify({
                'success': True,
                'data': series,
                'count': len(series)
            })
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def approve_video(self, filepath: str):
        """Genehmigt Video"""
        try:
            data = request.get_json() or {}
            target_folder = data.get('target_folder')
            
            success = self.file_manager.video_handler.approve_video(filepath, target_folder)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Video genehmigt'
                })
            else:
                return self._error_response('Video nicht gefunden oder bereits verarbeitet', 404)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def reject_video(self, filepath: str):
        """Lehnt Video ab"""
        try:
            success = self.file_manager.video_handler.reject_video(filepath)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Video abgelehnt'
                })
            else:
                return self._error_response('Video nicht gefunden', 404)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def update_video_metadata(self, filepath: str):
        """Aktualisiert Video-Metadaten manuell"""
        try:
            data = request.get_json()
            series_name = data.get('series_name')
            episode_number = data.get('episode_number')
            season_number = data.get('season_number')
            
            if not series_name:
                return self._error_response('series_name ist erforderlich', 400)
            
            success = self.file_manager.video_handler.update_video_metadata(
                filepath, series_name, episode_number, season_number
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Video-Metadaten aktualisiert'
                })
            else:
                return self._error_response('Video nicht gefunden', 404)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def move_video_custom(self, filepath: str):
        """Verschiebt Video in benutzerdefinierten Ordner"""
        try:
            data = request.get_json()
            target_folder = data.get('target_folder')
            custom_filename = data.get('custom_filename')
            
            if not target_folder:
                return self._error_response('target_folder ist erforderlich', 400)
            
            success = self.file_manager.video_handler.move_video_to_folder(
                filepath, target_folder, custom_filename
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Video für benutzerdefinierten Move vorbereitet'
                })
            else:
                return self._error_response('Video nicht gefunden', 404)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def approve_all_videos(self):
        """Genehmigt alle wartenden Videos"""
        try:
            count = self.file_manager.video_handler.approve_all_videos()
            return jsonify({
                'success': True,
                'message': f'{count} Videos genehmigt',
                'approved_count': count
            })
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def process_series_batch(self, series_name: str):
        """Verarbeitet alle Videos einer Serie"""
        try:
            data = request.get_json()
            target_folder = data.get('target_folder')
            
            if not target_folder:
                return self._error_response('target_folder ist erforderlich', 400)
            
            result = self.file_manager.video_handler.process_series_batch(series_name, target_folder)
            
            return jsonify({
                'success': result['success'],
                'data': result
            })
        except Exception as e:
            return self._error_response(str(e), 500)
    
    # Archive-Management Endpunkte
    def get_pending_archives(self):
        """Gibt wartende Archive zurück"""
        try:
            archives = self.file_manager.archive_handler.get_pending_archives()
            return jsonify({
                'success': True,
                'data': archives,
                'count': len(archives)
            })
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def get_processing_archives(self):
        """Gibt verarbeitete Archive zurück"""
        try:
            archives = self.file_manager.archive_handler.get_processing_archives()
            return jsonify({
                'success': True,
                'data': archives,
                'count': len(archives)
            })
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def get_completed_archives(self):
        """Gibt abgeschlossene Archive zurück"""
        try:
            archives = self.file_manager.archive_handler.get_completed_archives()
            return jsonify({
                'success': True,
                'data': archives,
                'count': len(archives)
            })
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def approve_archive(self, filepath: str):
        """Genehmigt Archive"""
        try:
            success = self.file_manager.archive_handler.approve_archive(filepath)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Archive genehmigt'
                })
            else:
                return self._error_response('Archive nicht gefunden', 404)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def reject_archive(self, filepath: str):
        """Lehnt Archive ab"""
        try:
            success = self.file_manager.archive_handler.reject_archive(filepath)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Archive abgelehnt'
                })
            else:
                return self._error_response('Archive nicht gefunden', 404)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    # Startup Cleanup Endpunkte
    def get_startup_cleanup_status(self):
        """Gibt Status des Startup-Cleanup zurück"""
        try:
            candidates = self.file_manager.archive_handler.get_startup_cleanup_candidates()
            
            return jsonify({
                'success': True,
                'data': {
                    'cleanup_completed': self.file_manager.archive_handler.startup_cleanup_completed,
                    'has_candidates': len(candidates) > 0,
                    'candidate_count': len(candidates),
                    'auto_cleanup_enabled': self.file_manager.config.auto_cleanup_extracted_archives
                }
            })
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def get_startup_cleanup_candidates(self):
        """Gibt Cleanup-Kandidaten zurück"""
        try:
            candidates = self.file_manager.archive_handler.get_startup_cleanup_candidates()
            
            return jsonify({
                'success': True,
                'data': candidates,
                'count': len(candidates)
            })
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def approve_cleanup_candidate(self, filepath: str):
        """Genehmigt Cleanup für ein Archive"""
        try:
            data = request.get_json()
            action = data.get('action', 'delete')  # 'delete' oder 'extract'
            
            if action not in ['delete', 'extract']:
                return self._error_response('action muss "delete" oder "extract" sein', 400)
            
            result = self.file_manager.archive_handler.approve_cleanup_candidate(filepath, action)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'data': result,
                    'message': result.get('message', 'Cleanup-Aktion ausgeführt')
                })
            else:
                return self._error_response(result.get('error', 'Cleanup fehlgeschlagen'), 400)
                
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def approve_all_cleanup_candidates(self):
        """Führt Cleanup für alle Kandidaten aus"""
        try:
            data = request.get_json()
            action = data.get('action', 'delete')  # 'delete' oder 'extract'
            
            if action not in ['delete', 'extract']:
                return self._error_response('action muss "delete" oder "extract" sein', 400)
            
            result = self.file_manager.archive_handler.approve_all_cleanup_candidates(action)
            
            return jsonify({
                'success': True,
                'data': result,
                'message': f'{result["successful"]} von {result["total_processed"]} Archive erfolgreich verarbeitet'
            })
            
        except Exception as e:
            return self._error_response(str(e), 500)
    
    # System-Kontrolle Endpunkte
    def start_monitoring(self):
        """Startet Überwachung"""
        try:
            self.file_manager.start()
            return jsonify({
                'success': True,
                'message': 'Überwachung gestartet'
            })
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def stop_monitoring(self):
        """Stoppt Überwachung"""
        try:
            self.file_manager.stop()
            return jsonify({
                'success': True,
                'message': 'Überwachung gestoppt'
            })
        except Exception as e:
            return self._error_response(str(e), 500)
    
    def cleanup_old_entries(self):
        """Räumt alte Einträge auf"""
        try:
            data = request.get_json() or {}
            max_age_hours = data.get('max_age_hours', 24)
            
            video_count = self.file_manager.video_handler.cleanup_old_completed(max_age_hours)
            archive_count = self.file_manager.archive_handler.cleanup_old_completed(max_age_hours)
            
            return jsonify({
                'success': True,
                'message': f'{video_count + archive_count} alte Einträge entfernt',
                'video_count': video_count,
                'archive_count': archive_count
            })
        except Exception as e:
            return self._error_response(str(e), 500)
    
    # Hilfsmethoden
    def _error_response(self, message: str, status_code: int = 500):
        """Erstellt Fehler-Antwort"""
        return jsonify({
            'success': False,
            'error': message
        }), status_code
    
    def _handle_404(self, e):
        """404 Fehlerbehandlung"""
        return jsonify({
            'success': False,
            'error': 'Endpunkt nicht gefunden'
        }), 404
    
    def _handle_500(self, e):
        """500 Fehlerbehandlung"""
        return jsonify({
            'success': False,
            'error': 'Interner Server-Fehler'
        }), 500
    
    def run(self, host: str = '127.0.0.1', port: int = 8080, debug: bool = False):
        """Startet API-Server"""
        self.logger.info(f"Starte API-Server auf {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)


class NotificationManager:
    """
    Verwaltet Benachrichtigungen für das System Tray
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.pending_notifications = []
        self.notification_callbacks: List[Callable] = []
    
    def add_callback(self, callback: Callable) -> None:
        """Fügt Benachrichtigungs-Callback hinzu"""
        self.notification_callbacks.append(callback)
    
    def notify_video_found(self, video_count: int, series_names: List[str]) -> None:
        """Benachrichtigung über neue Videos"""
        if video_count == 0:
            return
        
        if video_count == 1:
            title = "Neues Video gefunden"
            message = f"Serie: {series_names[0]}"
        else:
            title = f"{video_count} neue Videos gefunden"
            if len(set(series_names)) == 1:
                message = f"Serie: {series_names[0]} ({video_count} Episoden)"
            else:
                message = f"{len(set(series_names))} verschiedene Serien"
        
        self._send_notification(title, message, 'video')
    
    def notify_archive_found(self, archive_count: int) -> None:
        """Benachrichtigung über neue Archive"""
        if archive_count == 0:
            return
        
        if archive_count == 1:
            title = "Neues Archive gefunden"
            message = "Bereit zum Entpacken"
        else:
            title = f"{archive_count} neue Archive gefunden"
            message = "Bereit zum Entpacken"
        
        self._send_notification(title, message, 'archive')
    
    def notify_cleanup_candidates(self, candidate_count: int) -> None:
        """Benachrichtigung über Archive-Cleanup-Kandidaten"""
        if candidate_count == 0:
            return
        
        title = "Archive-Cleanup erforderlich"
        if candidate_count == 1:
            message = "1 bereits entpacktes Archive gefunden"
        else:
            message = f"{candidate_count} bereits entpackte Archive gefunden"
        
        self._send_notification(title, message, 'cleanup')
    
    def notify_processing_complete(self, success_count: int, error_count: int) -> None:
        """Benachrichtigung über abgeschlossene Verarbeitung"""
        if success_count + error_count == 0:
            return
        
        if error_count == 0:
            title = "Verarbeitung abgeschlossen"
            message = f"{success_count} Dateien erfolgreich verarbeitet"
        else:
            title = "Verarbeitung abgeschlossen"
            message = f"{success_count} erfolgreich, {error_count} Fehler"
        
        self._send_notification(title, message, 'complete')
    
    def _send_notification(self, title: str, message: str, category: str) -> None:
        """Sendet Benachrichtigung an alle registrierten Callbacks"""
        notification = {
            'title': title,
            'message': message,
            'category': category,
            'timestamp': time.time()
        }
        
        self.pending_notifications.append(notification)
        
        # Callbacks informieren
        for callback in self.notification_callbacks:
            try:
                callback(notification)
            except Exception as e:
                self.logger.error(f"Fehler in Notification-Callback: {e}")
    
    def get_pending_notifications(self) -> List[Dict]:
        """Gibt wartende Benachrichtigungen zurück und löscht sie"""
        notifications = self.pending_notifications.copy()
        self.pending_notifications.clear()
        return notifications


class FileManager:
    """
    Hauptklasse die alle Komponenten koordiniert
    """
    
    def __init__(self, config_path: str = "config.json"):
        # Konfiguration laden
        self.config = Config(config_path)
        setup_logging(self.config)
        self.logger = logging.getLogger(__name__)
        
        # Komponenten initialisieren
        self.video_analyzer = VideoPatternAnalyzer()
        self.file_monitor = FileMonitor(self.config, self.video_analyzer)
        self.archive_handler = SmartArchiveHandler(self.config)
        self.video_handler = SmartVideoHandler(self.config, self.video_analyzer)
        self.notification_manager = NotificationManager()
        
        # API erstellen
        self.api = FileManagerAPI(self)
        
        # Callbacks einrichten
        self._setup_callbacks()
        
        # Status tracking
        self.running = False
        self.start_time = None
        
        self.logger.info("File Manager initialisiert")
    
    def _setup_callbacks(self) -> None:
        """Richtet Callbacks zwischen Komponenten ein"""
        
        # File Monitor -> Handler
        self.file_monitor.set_callbacks(
            video_callback=self._on_video_found,
            archive_callback=self._on_archive_found
        )
        
        # Handler -> Notifications
        self.video_handler.set_callbacks(
            status_callback=self._on_video_status_change
        )
        
        self.archive_handler.set_status_callback(self._on_archive_status_change)
    
    def _on_video_found(self, video_file) -> None:
        """Callback für gefundene Videos"""
        self.video_handler.add_video(video_file)
        
        # Benachrichtigung senden
        pending_videos = self.video_handler.get_pending_videos()
        pending_count = len([v for v in pending_videos if v['status'] == 'pending'])
        
        if pending_count > 0:
            series_names = [v['series_name'] for v in pending_videos if v['status'] == 'pending']
            self.notification_manager.notify_video_found(pending_count, series_names)
    
    def _on_archive_found(self, archive_file) -> None:
        """Callback für gefundene Archive"""
        if self.config.auto_extract_archives:
            self.archive_handler.add_archive(archive_file)
            
            # Auto-Genehmigung wenn konfiguriert
            self.archive_handler.approve_archive(archive_file.filepath)
        else:
            self.archive_handler.add_archive(archive_file)
            
            # Benachrichtigung
            pending_count = len(self.archive_handler.get_pending_archives())
            self.notification_manager.notify_archive_found(pending_count)
    
    def _on_video_status_change(self, video_file) -> None:
        """Callback für Video-Status-Änderungen"""
        self.logger.debug(f"Video-Status geändert: {video_file.filename} -> {video_file.status.value}")
    
    def _on_archive_status_change(self, archive_file) -> None:
        """Callback für Archive-Status-Änderungen"""
        self.logger.debug(f"Archive-Status geändert: {archive_file.filename} -> {archive_file.status.value}")
    
    def start(self) -> None:
        """Startet alle Komponenten"""
        if self.running:
            self.logger.warning("File Manager läuft bereits")
            return
        
        try:
            self.running = True
            self.start_time = time.time()
            
            # Komponenten starten
            self.file_monitor.start()
            self.archive_handler.start_worker()
            self.video_handler.start_worker()
            
            # Startup Archive-Cleanup ausführen
            if self.config.cleanup_extracted_archives_on_startup:
                self.logger.info("Führe Startup Archive-Cleanup durch...")
                cleanup_result = self.archive_handler.perform_startup_cleanup()
                
                if cleanup_result.get('success'):
                    if cleanup_result.get('needs_user_confirmation', 0) > 0:
                        self.logger.info(f"Startup-Cleanup: {cleanup_result['needs_user_confirmation']} Archive benötigen Benutzer-Bestätigung")
                        
                        # Benachrichtigung für Frontend
                        self.notification_manager.notify_cleanup_candidates(
                            cleanup_result['needs_user_confirmation']
                        )
                    
                    if cleanup_result.get('auto_cleaned', 0) > 0:
                        self.logger.info(f"Startup-Cleanup: {cleanup_result['auto_cleaned']} Archive automatisch bereinigt")
                else:
                    self.logger.error(f"Startup-Cleanup fehlgeschlagen: {cleanup_result.get('error')}")
            
            self.logger.info("File Manager gestartet")
            
        except Exception as e:
            self.logger.error(f"Fehler beim Starten: {e}")
            self.running = False
            raise
    
    def stop(self) -> None:
        """Stoppt alle Komponenten"""
        if not self.running:
            return
        
        try:
            self.running = False
            
            # Komponenten stoppen
            self.file_monitor.stop()
            self.archive_handler.stop_worker()
            self.video_handler.stop_worker()
            
            self.logger.info("File Manager gestoppt")
            
        except Exception as e:
            self.logger.error(f"Fehler beim Stoppen: {e}")
    
    def restart_monitoring(self) -> None:
        """Startet Überwachung neu (nach Konfigurationsänderung)"""
        if self.running:
            self.file_monitor.stop()
            time.sleep(1)
            self.file_monitor.start()
            self.logger.info("Überwachung neu gestartet")
    
    def get_system_status(self) -> Dict:
        """Gibt aktuellen System-Status zurück"""
        uptime = time.time() - self.start_time if self.start_time else 0
        
        return {
            'running': self.running,
            'uptime_seconds': uptime,
            'components': {
                'file_monitor': hasattr(self.file_monitor, 'running') and self.file_monitor.running,
                'archive_worker': self.archive_handler.worker_running,
                'video_worker': self.video_handler.worker_running
            },
            'monitor_stats': self.file_monitor.get_stats(),
            'pending_notifications': len(self.notification_manager.pending_notifications)
        }
    
    def get_detailed_statistics(self) -> Dict:
        """Gibt detaillierte Statistiken zurück"""
        return {
            'system': self.get_system_status(),
            'videos': self.video_handler.get_statistics(),
            'archives': self.archive_handler.get_statistics(),
            'config': {
                'watch_folders': len(self.config.watch_folders),
                'target_folders': len(self.config.target_folders),
                'video_extensions': len(self.config.video_extensions),
                'archive_extensions': len(self.config.archive_extensions)
            }
        }
    
    def run_api_server(self, host: str = '127.0.0.1', port: int = 8080, debug: bool = False):
        """Startet API-Server"""
        self.api.run(host, port, debug)


# Hauptanwendung
def main():
    """Hauptfunktion zum Starten der Anwendung"""
    import argparse
    
    parser = argparse.ArgumentParser(description='File Manager Backend')
    parser.add_argument('--config', default='config.json', help='Pfad zur Konfigurationsdatei')
    parser.add_argument('--host', default='127.0.0.1', help='API Server Host')
    parser.add_argument('--port', type=int, default=8080, help='API Server Port')
    parser.add_argument('--debug', action='store_true', help='Debug-Modus')
    parser.add_argument('--no-monitor', action='store_true', help='Überwachung nicht automatisch starten')
    
    args = parser.parse_args()
    
    try:
        # File Manager erstellen
        file_manager = FileManager(args.config)
        
        print(f"""
╔══════════════════════════════════════════════╗
║          File Manager Backend v1.0           ║
╠══════════════════════════════════════════════╣
║  API Server: http://{args.host}:{args.port}        ║
║  Config: {args.config:33} ║
║  Debug: {str(args.debug):36} ║
╚══════════════════════════════════════════════╝
        """)
        
        # Monitoring starten (außer wenn deaktiviert)
        if not args.no_monitor:
            file_manager.start()
            print("✅ Datei-Überwachung gestartet")
        
        print("✅ API-Server wird gestartet...")
        print("   Drücke Ctrl+C zum Beenden\n")
        
        # API-Server starten (blockiert)
        file_manager.run_api_server(
            host=args.host,
            port=args.port,
            debug=args.debug
        )
        
    except KeyboardInterrupt:
        print("\n\n🛑 Beende File Manager...")
        if 'file_manager' in locals():
            file_manager.stop()
        print("✅ Beendet.")
        
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
        if 'file_manager' in locals():
            file_manager.stop()
        exit(1)


if __name__ == "__main__":
    main()