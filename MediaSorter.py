import eel
import sys
import os
import time
import re
import shutil
import json
import threading
import queue
import subprocess
from datetime import datetime
from urllib.parse import quote
from collections import OrderedDict
import tkinter as tk 
from tkinter import filedialog 
import traceback

# ===== EXE RESOURCE HANDLING =====
# This ensures the 'web' folder is found whether running as .py or .exe
def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# ===== WINDOWS PATH UTILITY =====
def normalize_windows_path(path):
    """Normalize Windows paths for cross-platform compatibility"""
    if not path or not isinstance(path, str):
        return ""
    
    # Convert to absolute path
    try:
        path = os.path.abspath(path)
    except:
        return path
    
    # Replace forward slashes with backslashes for Windows
    if sys.platform == "win32":
        path = path.replace('/', '\\')
    
    return path

# ===== CONFIGURATION =====
CONFIG_FILE = "sorter_config.json"
STATS = {'tv': 0, 'movies': 0, 'music': 0, 'other': 0}

def load_config():
    defaults = {
        "monitor": "", "tv": "", "movie": "", "music": "", "other": "", 
        "api_key": "", "acoustid_key": "", "use_ai_correction": True
    }
    
    config_path = os.path.abspath(CONFIG_FILE)
    print(f"Loading config from: {config_path}")
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding='utf-8') as f:
                loaded = json.load(f)
                # Normalize Windows paths
                for key in ["monitor", "tv", "movie", "music", "other"]:
                    if key in loaded and loaded[key]:
                        loaded[key] = normalize_windows_path(loaded[key])
                defaults.update(loaded)
        except Exception as e:
            print(f"Error loading config: {e}")
            traceback.print_exc()
            # Create a fresh config file
            try:
                with open(config_path, "w", encoding='utf-8') as f:
                    json.dump(defaults, f, indent=4)
            except:
                pass
    else:
        # Create config file if it doesn't exist
        try:
            with open(config_path, "w", encoding='utf-8') as f:
                json.dump(defaults, f, indent=4)
        except:
            pass
    
    return defaults

def save_config_file(config_data):
    # Normalize paths before saving
    config_copy = config_data.copy()
    for key in ["monitor", "tv", "movie", "music", "other"]:
        if key in config_copy and config_copy[key]:
            config_copy[key] = normalize_windows_path(config_copy[key])
    
    with open(CONFIG_FILE, "w", encoding='utf-8') as f:
        json.dump(config_copy, f, indent=4)

# ===== LIBRARY & FFMPEG CHECKS =====
MISSING_LIBS = []
FFMPEG_AVAILABLE = False

def check_ffmpeg():
    """Checks if ffmpeg is available in the system PATH"""
    try:
        # Check if ffmpeg is in PATH
        if shutil.which("ffmpeg"):
            return True
        # Fallback: try running it directly
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        return True
    except:
        return False

FFMPEG_AVAILABLE = check_ffmpeg()

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError: 
    MISSING_LIBS.append("watchdog")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError: 
    MISSING_LIBS.append("requests")
    REQUESTS_AVAILABLE = False

try:
    from tmdbv3api import TMDb, Search, TV, Movie, Episode
    TMDB_AVAILABLE = True
except ImportError: 
    TMDB_AVAILABLE = False

try:
    import mutagen
    from mutagen.easyid3 import EasyID3
    MUTAGEN_AVAILABLE = True
except ImportError: 
    MUTAGEN_AVAILABLE = False

try:
    import acoustid
    ACOUSTID_AVAILABLE = True
except ImportError: 
    ACOUSTID_AVAILABLE = False

# ===== UTILITY FUNCTIONS =====
def safe_path_join(base, *paths):
    try:
        final_path = os.path.abspath(os.path.join(base, *paths))
        base_path = os.path.abspath(base)
        if not final_path.startswith(base_path): 
            return None
        return final_path
    except: 
        return None

# ===== INTELLIGENT PARSER =====
class IntelligentParser:
    def __init__(self):
        self.patterns = {
            "quality": ["1080p", "720p", "480p", "2160p", "4k", "hdr", "bluray", "web-dl", "webrip", "dvdrip", "hdtv"],
            "codec": ["x264", "x265", "h264", "hevc", "aac", "ac3", "dts", "atmos", "truehd"],
            "group": ["rarbg", "yify", "yts", "eztv", "psa", "tgx"],
            "edition": ["extended", "unrated", "directors cut", "remastered"]
        }

    def clean_filename_aggressive(self, filename):
        name = os.path.splitext(filename)[0]
        name = name.replace('.', ' ').replace('_', ' ').replace('-', ' ')
        
        # Stop at Year
        year_match = re.search(r'\b(19|20)\d{2}\b', name)
        if year_match: 
            name = name[:year_match.end()]
            
        # Strip patterns
        for category in self.patterns.values():
            for term in category:
                name = re.sub(rf'\b{term}\b', '', name, flags=re.IGNORECASE)
        
        # Parentheses logic
        def paren_handler(match):
            content = match.group(1)
            keep = [r'^\d{4}$', r'^US$', r'^UK$', r'^Extended$']
            if any(re.match(p, content, re.IGNORECASE) for p in keep):
                return f" ({content})"
            return ""
        
        name = re.sub(r'\((.*?)\)', paren_handler, name)
        name = re.sub(r'\[.*?\]', '', name)
        return re.sub(r'\s+', ' ', name).strip()

# ===== FREE API LAYER =====
class FreeMetadataAPIs:
    @staticmethod
    def _safe_get(url, headers=None, retries=3):
        if not REQUESTS_AVAILABLE: 
            return None
        for i in range(retries):
            try:
                res = requests.get(url, headers=headers, timeout=5)
                if res.status_code == 200: 
                    return res.json()
                if res.status_code == 429: 
                    time.sleep((i + 1) * 2)
            except: 
                time.sleep(1)
        return None

    @staticmethod
    def tv_maze_search(query):
        url = f"http://api.tvmaze.com/singlesearch/shows?q={quote(query)}"
        data = FreeMetadataAPIs._safe_get(url)
        if data:
            return {
                "name": data.get("name"), 
                "year": data.get("premiered", "")[:4]
            }
        return None

    @staticmethod
    def musicbrainz_search(query):
        headers = {"User-Agent": "MediaSorter/1.0"}
        url = f"https://musicbrainz.org/ws/2/recording/?query={quote(query)}&fmt=json"
        data = FreeMetadataAPIs._safe_get(url, headers)
        if data and data.get("recordings"):
            rec = data["recordings"][0]
            return {
                "title": rec.get("title"),
                "artist": rec.get("artist-credit", [{}])[0].get("name", "Unknown")
            }
        return None

# ===== MEDIA CLASSIFIER =====
class MediaClassifier:
    def __init__(self, config):
        self.config = config
        self.parser = IntelligentParser()
        self.tmdb_key = config.get("api_key")
        self.acoustid_key = config.get("acoustid_key")
        
        self.use_tmdb = False
        if TMDB_AVAILABLE and self.tmdb_key:
            try:
                self.tmdb = TMDb()
                self.tmdb.api_key = self.tmdb_key
                self.tmdb.language = 'en'
                self.search = Search()
                self.episode_api = Episode()
                self.use_tmdb = True
            except Exception as e:
                print(f"TMDB init failed: {e}")

    def sanitize(self, name):
        name = str(name).strip()
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        return name.rstrip('.')

    def get_tv_details(self, filename):
        clean_name = self.parser.clean_filename_aggressive(filename)
        
        season, episode = "01", "01"
        patterns = [
            r'(?:s|season)\s?(\d{1,2})\s?(?:e|x|episode)\s?(\d{1,2})',
            r'(\d{1,2})x(\d{1,2})'
        ]
        
        found_ep = False
        for p in patterns:
            match = re.search(p, filename, re.IGNORECASE)
            if match:
                season = f"{int(match.group(1)):02d}"
                episode = f"{int(match.group(2)):02d}"
                clean_name = re.sub(match.group(0), '', clean_name, flags=re.IGNORECASE).strip()
                found_ep = True
                break
        
        series_name, year, ep_title = clean_name, "", ""

        if self.config.get("use_ai_correction", True):
            tv_data = FreeMetadataAPIs.tv_maze_search(series_name)
            if tv_data:
                series_name = tv_data.get("name", series_name)
                year = tv_data.get("year", "")

        if self.use_tmdb:
            try:
                results = self.search.tv_shows({"query": series_name})
                if results:
                    show = results[0]
                    series_name = show.name
                    if not year and hasattr(show, 'first_air_date') and show.first_air_date:
                        year = show.first_air_date[:4]
                    if found_ep:
                        try:
                            det = self.episode_api.details(show.id, int(season), int(episode))
                            if hasattr(det, 'name'): 
                                ep_title = det.name
                        except: 
                            pass
            except: 
                pass

        return self.sanitize(series_name), year, season, episode, self.sanitize(ep_title)

    def get_movie_details(self, filename):
        clean_name = self.parser.clean_filename_aggressive(filename)
        year = ""
        
        year_match = re.search(r'\b(19|20)\d{2}\b', clean_name)
        if year_match:
            year = year_match.group()
            clean_name = clean_name.replace(year, '').strip(" ()")

        if self.use_tmdb:
            try:
                results = self.search.movies({"query": clean_name, "year": year if year else None})
                if results:
                    m = results[0]
                    clean_name = m.title
                    if hasattr(m, 'release_date') and m.release_date: 
                        year = m.release_date[:4]
            except: 
                pass
            
        return self.sanitize(clean_name), year

    def get_music_details(self, file_path):
        filename = os.path.basename(file_path)
        artist, title, album = "Unknown Artist", os.path.splitext(filename)[0], "Unknown Album"
        track, disc = "", ""

        # Try AcoustID - Only if key exists AND ffmpeg is installed
        if ACOUSTID_AVAILABLE and self.acoustid_key and FFMPEG_AVAILABLE:
            try:
                results = acoustid.match(self.acoustid_key, file_path)
                for score, _, t_m, a_m in results:
                    if score > 0.8:
                        artist, title = a_m, t_m
                        break
            except Exception as e:
                print(f"AcoustID error: {e}")

        # Try mutagen
        if MUTAGEN_AVAILABLE:
            try:
                f = mutagen.File(file_path, easy=True)
                if f:
                    artist = f.get('artist', [artist])[0]
                    album = f.get('album', [album])[0]
                    title = f.get('title', [title])[0]
                    tr = f.get('tracknumber', [''])[0]
                    if tr: 
                        track = tr.split('/')[0].zfill(2)
                    dn = f.get('discnumber', [''])[0]
                    if dn: 
                        disc = dn.split('/')[0]
            except Exception as e:
                print(f"Mutagen error: {e}")

        # Fallback to MusicBrainz
        if artist == "Unknown Artist" and self.config.get("use_ai_correction", True):
            clean = self.parser.clean_filename_aggressive(filename)
            mb = FreeMetadataAPIs.musicbrainz_search(clean)
            if mb: 
                title, artist = mb.get("title", title), mb.get("artist", artist)

        return self.sanitize(artist), self.sanitize(album), self.sanitize(title), track, disc

# ===== PROCESSOR =====
class Processor:
    def __init__(self, config, log_callback, update_stat_callback):
        self.config = config
        self.log = log_callback
        self.update_stat = update_stat_callback
        self.classifier = MediaClassifier(config)

    def process_file(self, file_path):
        if not os.path.exists(file_path): 
            return False
        
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        
        # Ignore non-media files
        ignore_exts = ['.txt', '.nfo', '.jpg', '.png', '.exe', '.url', '.db', '.part', '.tmp', '.crdownload']
        if ext in ignore_exts: 
            return False

        final_path, log_cat, dest_root = None, "other", None

        try:
            # MUSIC
            if ext in ['.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a']:
                dest_root = self.config.get("music", "")
                if dest_root:
                    art, alb, tit, trk, dsc = self.classifier.get_music_details(file_path)
                    prefix = f"{dsc}-{trk}" if (trk and dsc and dsc != '1') else (trk if trk else "")
                    new_name = f"{prefix} - {tit}{ext}" if prefix else f"{art} - {tit}{ext}"
                    if dsc and dsc != "1":
                        final_path = safe_path_join(dest_root, art, alb, f"Disc {dsc}", new_name)
                    else:
                        final_path = safe_path_join(dest_root, art, alb, new_name)
                    log_cat = "music"

            # VIDEO
            elif ext in ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.m4v']:
                is_tv = bool(re.search(r'(s\d+|season)', filename, re.IGNORECASE))
                if is_tv:
                    dest_root = self.config.get("tv", "")
                    if dest_root:
                        nm, yr, s, e, t = self.classifier.get_tv_details(filename)
                        folder = f"{nm} ({yr})" if yr else nm
                        season_folder = f"Season {s}"
                        new_name = f"{nm} - S{s}E{e} - {t}{ext}" if t else f"{nm} - S{s}E{e}{ext}"
                        final_path = safe_path_join(dest_root, folder, season_folder, new_name)
                        log_cat = "tv"
                else:
                    dest_root = self.config.get("movie", "")
                    if dest_root:
                        nm, yr = self.classifier.get_movie_details(filename)
                        new_name = f"{nm} ({yr}){ext}" if yr else f"{nm}{ext}"
                        final_path = safe_path_join(dest_root, new_name)
                        log_cat = "movies"

            # Fallback
            if not final_path:
                dest_root = self.config.get("other", "")
                log_cat = "other"
                if dest_root:
                    final_path = safe_path_join(dest_root, filename)

            # Move file
            if final_path:
                os.makedirs(os.path.dirname(final_path), exist_ok=True)
                
                # Handle duplicates
                base, extension = os.path.splitext(final_path)
                c = 1
                while os.path.exists(final_path):
                    final_path = f"{base}_{c}{extension}"
                    c += 1
                
                shutil.move(file_path, final_path)
                self.log(f"Moved: {os.path.basename(final_path)}", "success")
                self.update_stat(log_cat)
                return True
            else:
                self.log(f"No destination for: {filename}", "warning")

        except Exception as e:
            self.log(f"Error processing {filename}: {str(e)}", "error")
        
        return False

# ===== CORE LOGIC =====
class ProcessingQueue:
    def __init__(self, max_cache=2000):
        self.queue = queue.Queue(maxsize=5000)
        self.lock = threading.Lock()
        self.processed = OrderedDict()
        self.max_cache = max_cache

    def add_file(self, file_path):
        with self.lock:
            if file_path in self.processed:
                if time.time() - self.processed[file_path] < 300: 
                    return False
                else: 
                    del self.processed[file_path]
            
            if len(self.processed) > self.max_cache:
                while len(self.processed) > self.max_cache * 0.9: 
                    self.processed.popitem(last=False)
            
            try:
                self.queue.put(file_path, block=False)
                self.processed[file_path] = time.time()
                return True
            except queue.Full: 
                return False

class WorkerPool:
    def __init__(self, processor, queue_manager, num_workers=2):
        self.processor = processor
        self.queue_manager = queue_manager
        self.num_workers = num_workers
        self.workers = []
        self.running = False

    def start(self):
        self.running = True
        for _ in range(self.num_workers):
            t = threading.Thread(target=self._loop, daemon=True)
            t.start()
            self.workers.append(t)

    def stop(self): 
        self.running = False

    def _loop(self):
        while self.running:
            try:
                path = self.queue_manager.queue.get(timeout=1)
                if self._stable(path):
                    if self.processor.process_file(path):
                        self._cleanup(os.path.dirname(path))
                self.queue_manager.queue.task_done()
            except queue.Empty: 
                continue
            except Exception as e:
                print(f"Worker error: {e}")

    def _stable(self, path, timeout=30):
        start = time.time()
        last_size, stable_count = -1, 0
        while time.time() - start < timeout:
            if not os.path.exists(path): 
                return False
            try:
                size = os.path.getsize(path)
                if size == last_size and size > 0: 
                    stable_count += 1
                else: 
                    stable_count = 0
                last_size = size
                if stable_count >= 3:
                    # Try to open to check if locked
                    with open(path, 'ab'): 
                        pass
                    return True
            except: 
                stable_count = 0
            time.sleep(1)
        return False

    def _cleanup(self, folder):
        try:
            junk = ['.txt', '.nfo', '.jpg', '.png', '.url', '.exe', '.srt']
            if not self.processor.config.get("monitor"):
                return
            if os.path.abspath(folder) == os.path.abspath(self.processor.config["monitor"]): 
                return
            for f in os.listdir(folder):
                if os.path.splitext(f)[1].lower() in junk:
                    try: 
                        os.remove(os.path.join(folder, f))
                    except: 
                        pass
            if not os.listdir(folder): 
                os.rmdir(folder)
        except Exception as e:
            print(f"Cleanup error: {e}")

class HeartbeatEngine:
    def __init__(self, config, queue_manager, log_func):
        self.config = config
        self.queue_manager = queue_manager
        self.log = log_func
        self.running = False

    def start(self):
        if self.running: 
            return
        self.running = True
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self): 
        self.running = False

    def _run(self):
        while self.running:
            p = self.config.get("monitor")
            if p and os.path.exists(p): 
                self._scan(p)
            for _ in range(10): 
                if not self.running: 
                    break
                time.sleep(1)

    def _scan(self, folder, depth=0):
        if depth > 3: 
            return
        try:
            for item in os.listdir(folder):
                p = os.path.join(folder, item)
                if os.path.isfile(p): 
                    self.queue_manager.add_file(p)
                elif os.path.isdir(p): 
                    self._scan(p, depth+1)
        except: 
            pass

# ===== CONTROLLER =====
class MediaController:
    def __init__(self):
        self.config = load_config()
        self.queue = None
        self.workers = None
        self.heartbeat = None
        self.observer = None
        self.monitoring = False
        self.processor = None

    def log(self, message, msg_type="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{msg_type.upper()}] {message}")
        try: 
            eel.js_add_log(message, msg_type)
        except: 
            pass

    def update_stat(self, category):
        if category in STATS:
            STATS[category] += 1
            try: 
                eel.js_update_stats(STATS['tv'], STATS['movies'], STATS['music'], STATS['other'])
            except: 
                pass

    def start_monitoring(self):
        if self.monitoring: 
            return False
        
        self.config = load_config()
        monitor_path = self.config.get("monitor", "")
        if not monitor_path:
            self.log("Monitor folder not configured", "error")
            return False
        
        if not os.path.exists(monitor_path):
            self.log(f"Monitor folder does not exist: {monitor_path}", "error")
            return False

        self.log("Starting monitoring...", "info")
        
        try:
            self.queue = ProcessingQueue()
            self.processor = Processor(self.config, self.log, self.update_stat)
            
            self.workers = WorkerPool(self.processor, self.queue)
            self.workers.start()
            
            self.heartbeat = HeartbeatEngine(self.config, self.queue, self.log)
            self.heartbeat.start()
            
            if "watchdog" not in MISSING_LIBS:
                try:
                    from watchdog.observers import Observer
                    from watchdog.events import FileSystemEventHandler
                    
                    class MediaHandler(FileSystemEventHandler):
                        def __init__(self, queue, config): 
                            self.q = queue
                            self.c = config
                        
                        def on_created(self, e): 
                            self._handle_event(e)
                        
                        def on_moved(self, e): 
                            self._handle_event(e, True)
                        
                        def _handle_event(self, e, moved=False):
                            if e.is_directory: 
                                return
                            p = e.dest_path if moved else e.src_path
                            
                            # Anti-loop
                            for key in ["tv", "movie", "music", "other"]:
                                d = self.c.get(key)
                                if d and os.path.commonpath([os.path.abspath(p), os.path.abspath(d)]) == os.path.abspath(d): 
                                    return

                            if not p.endswith('.tmp'): 
                                self.q.add_file(p)
                    
                    self.observer = Observer()
                    handler = MediaHandler(self.queue, self.config)
                    self.observer.schedule(handler, monitor_path, recursive=True)
                    self.observer.start()
                    self.log("File system observer started", "success")
                except Exception as e:
                    self.log(f"Watchdog error: {e}", "warning")
            else:
                self.log("Watchdog not available - using periodic scanning", "warning")
            
            self.monitoring = True
            self.log(f"Monitoring started on: {monitor_path}", "success")
            
            # Initial sweep
            threading.Thread(target=self._initial_sweep, daemon=True).start()
            return True
            
        except Exception as e:
            self.log(f"Failed to start monitoring: {e}", "error")
            return False

    def stop_monitoring(self):
        if not self.monitoring:
            return
        
        self.log("Stopping monitoring...", "warning")
        
        if self.observer:
            try:
                self.observer.stop()
                self.observer.join()
                self.log("File system observer stopped", "info")
            except:
                pass
        
        if self.heartbeat:
            self.heartbeat.stop()
        
        if self.workers:
            self.workers.stop()
        
        self.monitoring = False
        self.log("Monitoring stopped", "warning")

    def _initial_sweep(self):
        folder = self.config.get("monitor")
        if not folder or not os.path.exists(folder): 
            return
        count = 0
        try:
            for root, _, files in os.walk(folder):
                for file in files:
                    if self.queue.add_file(os.path.join(root, file)): 
                        count += 1
            if count > 0:
                self.log(f"Initial sweep queued {count} files", "info")
        except Exception as e:
            self.log(f"Sweep error: {e}", "error")

# ===== GLOBAL CONTROLLER =====
controller = MediaController()

# ===== EEL EXPOSED FUNCTIONS =====
@eel.expose
def get_config():
    return controller.config

@eel.expose
def get_initial_data():
    return {
        "config": controller.config,
        "stats": STATS,
        "is_monitoring": controller.monitoring,
        "missing_libs": MISSING_LIBS,
        "ffmpeg_installed": FFMPEG_AVAILABLE
    }

@eel.expose
def save_config_from_js(data):
    try:
        controller.config.update(data)
        save_config_file(controller.config)
        return {"success": True, "message": "Configuration saved"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@eel.expose
def select_folder():
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder = filedialog.askdirectory()
        root.destroy()
        return normalize_windows_path(folder) if folder else ""
    except:
        return ""

@eel.expose
def start_monitoring():
    try:
        success = controller.start_monitoring()
        return {"success": success, "is_monitoring": controller.monitoring}
    except Exception as e:
        return {"success": False, "error": str(e)}

@eel.expose
def stop_monitoring():
    try:
        controller.stop_monitoring()
        return {"success": True, "is_monitoring": controller.monitoring}
    except Exception as e:
        return {"success": False, "error": str(e)}

@eel.expose
def run_mass_import():
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder = filedialog.askdirectory()
        root.destroy()
        
        if folder and os.path.exists(folder):
            def mass_worker():
                count = 0
                proc = Processor(controller.config, controller.log, controller.update_stat)
                for root, _, files in os.walk(folder):
                    for file in files:
                        if proc.process_file(os.path.join(root, file)): 
                            count += 1
                controller.log(f"Mass import finished. Moved {count} files.", "success")
                eel.js_show_toast(f"Import Complete: {count} files", "success")
            
            threading.Thread(target=mass_worker, daemon=True).start()
            return {"success": True, "message": f"Starting mass import from {folder}"}
        else:
            return {"success": False, "message": "No folder selected"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@eel.expose
def test_parser(filename):
    try:
        parser = IntelligentParser()
        classifier = MediaClassifier(controller.config)
        
        clean = parser.clean_filename_aggressive(filename)
        
        # Test TV detection
        is_tv = bool(re.search(r'(s\d+|season)', filename, re.IGNORECASE))
        result = {"original": filename, "cleaned": clean, "is_tv": is_tv}
        
        if is_tv:
            name, year, season, episode, title = classifier.get_tv_details(filename)
            result.update({
                "type": "tv",
                "series_name": name,
                "year": year,
                "season": season,
                "episode": episode,
                "episode_title": title
            })
        else:
            name, year = classifier.get_movie_details(filename)
            result.update({
                "type": "movie",
                "movie_name": name,
                "year": year
            })
        
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ===== TEST FUNCTION =====
@eel.expose
def test_connection():
    return "Python backend is working!"

# ===== WINDOWS BROWSER DETECTION =====
def get_windows_browser():
    """Get the best available browser on Windows"""
    browsers = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "chrome",  # Try PATH
        "msedge",  # Try PATH
        "default"  # System default
    ]
    
    for browser in browsers:
        if browser == "default":
            return browser
        if browser in ["chrome", "msedge"]:
            try:
                if shutil.which(browser):
                    return browser
            except:
                continue
        else:
            if os.path.exists(browser):
                return browser
    
    return None

# ===== SIMPLIFIED MAIN =====
if __name__ == "__main__":
    print("=" * 60)
    print("Media Sorter Pro - Starting...")
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")
    print(f"Current directory: {os.getcwd()}")
    print("=" * 60)
    
    # Ensure web directory exists
    web_dir = get_resource_path('web')
    web_dir = os.path.abspath(web_dir)
    
    print(f"Web directory: {web_dir}")
    
    if not os.path.exists(web_dir):
        print(f"Creating web directory: {web_dir}")
        os.makedirs(web_dir, exist_ok=True)
    
    # Check for required HTML files
    index_path = os.path.join(web_dir, 'index.html')
    if not os.path.exists(index_path):
        print(f"WARNING: index.html not found at {index_path}")
        print("Creating placeholder HTML file...")
        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Media Sorter Pro</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 40px; 
            background: #0a0a0f; 
            color: white; 
        }
        .container { 
            max-width: 800px; 
            margin: 0 auto; 
            text-align: center; 
            padding: 40px; 
        }
        .spinner { 
            border: 5px solid #333; 
            border-top: 5px solid #6366f1; 
            border-radius: 50%; 
            width: 50px; 
            height: 50px; 
            animation: spin 1s linear infinite; 
            margin: 20px auto; 
        }
        @keyframes spin { 
            0% { transform: rotate(0deg); } 
            100% { transform: rotate(360deg); } 
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Media Sorter Pro</h1>
        <div class="spinner"></div>
        <p>Loading application...</p>
        <p>If this message persists, check if index.html exists in the web folder.</p>
    </div>
    <script type="text/javascript" src="/eel.js"></script>
    <script>
        setTimeout(() => location.reload(), 2000);
    </script>
</body>
</html>""")
            print("✓ Created placeholder index.html")
        except Exception as e:
            print(f"✗ Failed to create index.html: {e}")
    
    try:
        # Initialize Eel
        print("Initializing Eel...")
        eel.init(web_dir)
        print("✓ Eel initialized successfully")
    except Exception as e:
        print(f"✗ Eel initialization failed: {e}")
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    try:
        # Configure browser for Windows
        mode = 'chrome'  # Default mode
        
        if sys.platform == "win32":
            browser = get_windows_browser()
            if browser:
                print(f"Using browser: {browser}")
                if browser.endswith('.exe'):
                    mode = browser  # Use full path
                else:
                    mode = browser
            else:
                mode = None  # Let Eel use default
                print("Using default system browser")
        
        # Get available port
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
        sock.close()
        
        print(f"\n" + "=" * 60)
        print(f"Starting web server on: http://127.0.0.1:{port}")
        print(f"Browser mode: {mode}")
        print("=" * 60 + "\n")
        
        # SIMPLIFIED startup - remove problematic parameters
        print("Starting web interface...")
        
        # Start with minimal parameters
        eel.start(
            'index.html',
            host='127.0.0.1',
            port=port,
            mode=mode,
            size=(1200, 800)
        )
        
    except (SystemExit, KeyboardInterrupt):
        print("\n" + "=" * 60)
        print("Graceful shutdown requested...")
        print("=" * 60)
        if controller and controller.monitoring:
            controller.stop_monitoring()
        sys.exit(0)
        
    except Exception as e:
        print(f"\n" + "=" * 60)
        print(f"FATAL ERROR: {e}")
        print("=" * 60)
        traceback.print_exc()
        
        # Try ultra-simple fallback
        print("\nTrying ultra-simple startup...")
        try:
            eel.start('index.html', mode=None, port=0, host='localhost')
        except Exception as e2:
            print(f"Simple startup also failed: {e2}")
            
            # Try manual access
            print(f"\nYou can try accessing manually at: http://127.0.0.1:{port}")
            print("Or try running with a different browser:")
            print("  python MediaSorter.py --mode=edge")
            print("  python MediaSorter.py --mode=chrome")
            print("  python MediaSorter.py --mode=default")
        
        # Keep console open
        try:
            input("\nPress Enter to exit...")
        except:
            pass
        
        sys.exit(1)