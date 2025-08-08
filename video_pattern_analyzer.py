"""
File Manager Backend - Teil 2: Video Pattern Analyzer
Intelligente Erkennung von Serien-Namen und Episoden-Nummern
"""

import re
import os
import logging
from typing import Optional, Tuple, List, Dict
from pathlib import Path
from dataclasses import dataclass


@dataclass
class VideoMetadata:
    """Extrahierte Metadaten aus Video-Dateinamen"""
    series_name: str
    episode_number: Optional[int] = None
    season_number: Optional[int] = None
    resolution: Optional[str] = None
    language: Optional[str] = None
    source: Optional[str] = None
    confidence: float = 0.0  # 0-1, wie sicher die Erkennung ist


class VideoPatternAnalyzer:
    """
    Analysiert Video-Dateinamen und extrahiert Serien-Informationen
    Unterstützt verschiedene Naming-Conventions für Anime und Serien
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Regex-Patterns für verschiedene Naming-Conventions
        self.patterns = [
            # Anime-Style: "Yuusha-chan_no_Bouken_wa_Owatteshimatta_02_ENG_www.site.net.mp4"
            {
                'name': 'anime_underscore',
                'pattern': r'^(.+?)_(\d{2,3})(?:_([A-Z]{2,3}))?.*\.(\w+)$',
                'confidence': 0.9,
                'groups': {'series': 1, 'episode': 2, 'language': 3, 'extension': 4}
            },
            
            # Standard-Style: "Series Name S01E05.mp4" oder "Series Name 1x05.mp4" 
            {
                'name': 'standard_season_episode',
                'pattern': r'^(.+?)[\s\._-][Ss]?(\d{1,2})[xXeE](\d{1,3}).*\.(\w+)$',
                'confidence': 0.95,
                'groups': {'series': 1, 'season': 2, 'episode': 3, 'extension': 4}
            },
            
            # Einfach: "Series Name 05.mp4" oder "Series Name - 05.mp4"
            {
                'name': 'simple_episode',
                'pattern': r'^(.+?)[\s\._-]+(\d{1,3}).*\.(\w+)$',
                'confidence': 0.7,
                'groups': {'series': 1, 'episode': 2, 'extension': 3}
            },
            
            # Bracket-Style: "Series Name [05].mp4" oder "Series Name (Episode 05).mp4"
            {
                'name': 'bracket_episode', 
                'pattern': r'^(.+?)[\s\._-]*[\[\(].*?(\d{1,3}).*?[\]\)].*\.(\w+)$',
                'confidence': 0.8,
                'groups': {'series': 1, 'episode': 2, 'extension': 3}
            }
        ]
        
        # Patterns für Resolution-Erkennung
        self.resolution_patterns = [
            r'\b(480p|720p|1080p|1440p|2160p|4K|8K)\b',
            r'\b(\d{3,4}x\d{3,4})\b'
        ]
        
        # Language-Patterns
        self.language_patterns = {
            r'\b(ENG|ENGLISH)\b': 'English',
            r'\b(GER|GERMAN|DEU)\b': 'German', 
            r'\b(JPN|JAPANESE)\b': 'Japanese',
            r'\b(SUB|SUBBED)\b': 'Subtitled',
            r'\b(DUB|DUBBED)\b': 'Dubbed'
        }
        
        # Source-Patterns
        self.source_patterns = {
            r'\b(BluRay|BD|BDRip)\b': 'BluRay',
            r'\b(WEB-?DL|WebRip)\b': 'WEB',
            r'\b(DVDRip|DVD)\b': 'DVD',
            r'\b(HDTV|TV)\b': 'TV',
            r'\b(CAM|TS|TC)\b': 'CAM'
        }
        
        # Wörter die aus Serien-Namen entfernt werden sollten
        self.cleanup_words = [
            'www', 'com', 'net', 'org', 'tv', 'site', 'download',
            'torrent', 'rip', 'encode', 'release', 'group'
        ]
    
    def analyze_filename(self, filepath: str) -> Optional[VideoMetadata]:
        """
        Analysiert einen Dateinamen und extrahiert Video-Metadaten
        
        Args:
            filepath: Pfad zur Video-Datei
            
        Returns:
            VideoMetadata oder None wenn keine Erkennung möglich
        """
        filename = Path(filepath).name
        self.logger.debug(f"Analysiere Dateiname: {filename}")
        
        best_match = None
        best_confidence = 0.0
        
        # Alle Patterns durchprobieren
        for pattern_info in self.patterns:
            match = re.search(pattern_info['pattern'], filename, re.IGNORECASE)
            if match:
                metadata = self._extract_metadata(match, pattern_info, filename)
                if metadata and metadata.confidence > best_confidence:
                    best_match = metadata
                    best_confidence = metadata.confidence
                    self.logger.debug(f"Pattern '{pattern_info['name']}' matched mit Confidence {metadata.confidence}")
        
        if best_match:
            self.logger.info(f"Beste Erkennung für '{filename}': {best_match.series_name} E{best_match.episode_number}")
        else:
            self.logger.warning(f"Keine Erkennung möglich für: {filename}")
            
        return best_match
    
    def _extract_metadata(self, match: re.Match, pattern_info: Dict, filename: str) -> Optional[VideoMetadata]:
        """Extrahiert Metadaten aus einem Regex-Match"""
        try:
            groups = pattern_info['groups']
            
            # Serien-Name extrahieren und bereinigen
            series_raw = match.group(groups['series']) if 'series' in groups else ""
            series_name = self._clean_series_name(series_raw)
            
            if not series_name:
                return None
            
            # Episode extrahieren
            episode = None
            if 'episode' in groups and match.group(groups['episode']):
                episode = int(match.group(groups['episode']))
            
            # Season extrahieren  
            season = None
            if 'season' in groups and match.group(groups['season']):
                season = int(match.group(groups['season']))
            
            # Sprache extrahieren
            language = None
            if 'language' in groups and match.group(groups['language']):
                language = match.group(groups['language'])
            
            # Zusätzliche Metadaten aus vollem Dateinamen
            resolution = self._extract_resolution(filename)
            if not language:
                language = self._extract_language(filename)
            source = self._extract_source(filename)
            
            # Confidence berechnen
            base_confidence = pattern_info['confidence']
            confidence = self._calculate_confidence(series_name, episode, season, base_confidence)
            
            return VideoMetadata(
                series_name=series_name,
                episode_number=episode,
                season_number=season,
                resolution=resolution,
                language=language,
                source=source,
                confidence=confidence
            )
            
        except (ValueError, IndexError) as e:
            self.logger.debug(f"Fehler bei Metadaten-Extraktion: {e}")
            return None
    
    def _clean_series_name(self, raw_name: str) -> str:
        """Bereinigt und normalisiert Serien-Namen"""
        if not raw_name:
            return ""
        
        # Unterstriche durch Leerzeichen ersetzen (für Anime-Style)
        name = raw_name.replace('_', ' ')
        
        # Punkte durch Leerzeichen ersetzen (wenn nicht am Ende)
        name = re.sub(r'\.(?!\w+$)', ' ', name)
        
        # Mehrfache Leerzeichen entfernen
        name = re.sub(r'\s+', ' ', name)
        
        # Cleanup-Wörter entfernen
        words = name.split()
        cleaned_words = []
        
        for word in words:
            word_lower = word.lower()
            # Skip wenn Cleanup-Wort oder Website-Pattern
            if (word_lower in self.cleanup_words or 
                '.' in word_lower and len(word_lower) > 4):
                continue
            cleaned_words.append(word)
        
        # Titel-Case anwenden
        result = ' '.join(cleaned_words).strip()
        if result:
            # Sonderbehandlung für bekannte Wörter
            result = self._apply_title_case(result)
        
        return result
    
    def _apply_title_case(self, text: str) -> str:
        """Wendet intelligente Titel-Großschreibung an"""
        # Kleine Wörter die nicht großgeschrieben werden
        small_words = {'no', 'wa', 'wo', 'ga', 'ni', 'to', 'de', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'by', 'for', 'of'}
        
        words = text.split()
        result = []
        
        for i, word in enumerate(words):
            # Erstes und letztes Wort immer groß
            if i == 0 or i == len(words) - 1:
                result.append(word.capitalize())
            # Kleine Wörter klein lassen (außer am Anfang/Ende)
            elif word.lower() in small_words:
                result.append(word.lower())
            else:
                result.append(word.capitalize())
        
        return ' '.join(result)
    
    def _extract_resolution(self, filename: str) -> Optional[str]:
        """Extrahiert Auflösung aus Dateiname"""
        for pattern in self.resolution_patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_language(self, filename: str) -> Optional[str]:
        """Extrahiert Sprache aus Dateiname"""
        for pattern, lang in self.language_patterns.items():
            if re.search(pattern, filename, re.IGNORECASE):
                return lang
        return None
    
    def _extract_source(self, filename: str) -> Optional[str]:
        """Extrahiert Quelle aus Dateiname"""
        for pattern, source in self.source_patterns.items():
            if re.search(pattern, filename, re.IGNORECASE):
                return source
        return None
    
    def _calculate_confidence(self, series_name: str, episode: Optional[int], 
                            season: Optional[int], base_confidence: float) -> float:
        """Berechnet Confidence-Score basierend auf extrahierten Daten"""
        confidence = base_confidence
        
        # Bonus für gültigen Serien-Namen
        if series_name and len(series_name) > 2:
            confidence += 0.1
        
        # Bonus für erkannte Episode
        if episode is not None:
            confidence += 0.1
        
        # Bonus für erkannte Season
        if season is not None:
            confidence += 0.05
        
        # Malus für sehr kurze oder verdächtige Namen
        if len(series_name) < 3:
            confidence -= 0.3
        
        # Auf [0, 1] begrenzen
        return max(0.0, min(1.0, confidence))
    
    def find_existing_series_folder(self, series_name: str, target_folders: List[str]) -> Optional[str]:
        """
        Sucht nach existierenden Ordnern für eine Serie
        
        Args:
            series_name: Name der Serie
            target_folders: Liste der Ziel-Ordner zum Durchsuchen
            
        Returns:
            Pfad zum gefundenen Serien-Ordner oder None
        """
        for target_folder in target_folders:
            if not os.path.exists(target_folder):
                continue
                
            try:
                for item in os.listdir(target_folder):
                    item_path = os.path.join(target_folder, item)
                    if os.path.isdir(item_path):
                        # Exakte Übereinstimmung
                        if item.lower() == series_name.lower():
                            return item_path
                        
                        # Ähnlichkeits-Check (vereinfacht)
                        similarity = self._calculate_name_similarity(series_name, item)
                        if similarity > 0.8:  # 80% Ähnlichkeit
                            self.logger.info(f"Ähnlicher Ordner gefunden: '{item}' für Serie '{series_name}' (Ähnlichkeit: {similarity:.2f})")
                            return item_path
                            
            except PermissionError:
                self.logger.warning(f"Keine Berechtigung für Ordner: {target_folder}")
                continue
        
        return None
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Berechnet Ähnlichkeit zwischen zwei Namen (vereinfacht)"""
        name1_clean = re.sub(r'[^\w\s]', '', name1.lower())
        name2_clean = re.sub(r'[^\w\s]', '', name2.lower())
        
        words1 = set(name1_clean.split())
        words2 = set(name2_clean.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0


# Test-Funktionen
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    analyzer = VideoPatternAnalyzer()
    
    # Test-Dateinamen
    test_files = [
        "Yuusha-chan_no_Bouken_wa_Owatteshimatta_02_ENG_www.UnderHentai.net.mp4",
        "Attack on Titan S04E15 1080p.mkv",
        "One Piece - 1045.mp4",
        "Demon Slayer [12] BluRay.mp4",
        "My Hero Academia 3x05 DUBBED.mp4"
    ]
    
    print("=== Video Pattern Analyzer Tests ===\n")
    
    for filename in test_files:
        print(f"Datei: {filename}")
        metadata = analyzer.analyze_filename(filename)
        if metadata:
            print(f"  Serie: {metadata.series_name}")
            print(f"  Episode: {metadata.episode_number}")
            print(f"  Season: {metadata.season_number}")
            print(f"  Auflösung: {metadata.resolution}")
            print(f"  Sprache: {metadata.language}")
            print(f"  Quelle: {metadata.source}")
            print(f"  Confidence: {metadata.confidence:.2f}")
        else:
            print("  Keine Erkennung möglich")
        print()