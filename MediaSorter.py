import traceback
import tkinter as tk
from tkinter import messagebox
import sys

# --- USER DETAILS ---
# You can edit these details here
APP_VERSION = "1.0"
DEVELOPER_NAME = "Chris Hedley"

# WE WRAP EVERYTHING IN A TRY BLOCK TO CATCH STARTUP CRASHES
try:
    import os
    import time
    import re
    import shutil
    import json
    import threading
    from tkinter import filedialog, scrolledtext, ttk

    # --- LIBRARIES CHECK ---
    MISSING_LIBS = []
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError: MISSING_LIBS.append("watchdog")

    try:
        from tmdbv3api import TMDb, Search, TV, Movie, Episode
        TMDB_AVAILABLE = True
    except ImportError: TMDB_AVAILABLE = False

    try:
        import mutagen
        from mutagen.easyid3 import EasyID3
        MUTAGEN_AVAILABLE = True
    except ImportError: MUTAGEN_AVAILABLE = False

    try:
        import acoustid
        ACOUSTID_AVAILABLE = True
    except ImportError: ACOUSTID_AVAILABLE = False

    # --- CONFIGURATION ---
    CONFIG_FILE = "sorter_config.json"

    def load_config():
        defaults = {
            "monitor": "", "tv": "", "movie": "", "music": "", "other": "", 
            "api_key": "", "acoustid_key": ""
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    defaults.update(json.load(f))
            except: pass
        return defaults

    def save_config(config_data):
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_data, f, indent=4)

    # --- INTELLIGENCE LAYER ---
    class MediaClassifier:
        def __init__(self, tmdb_key=None, acoustid_key=None):
            self.use_api = False
            self.acoustid_key = acoustid_key
            if TMDB_AVAILABLE and tmdb_key:
                self.tmdb = TMDb()
                self.tmdb.api_key = tmdb_key
                self.search = Search()
                self.episode_api = Episode()
                self.use_api = True

        def sanitize(self, name):
            name = str(name).strip()
            name = re.sub(r'[<>:"/\\|?*]', '', name)
            return name.rstrip('.')

        def clean_final_name(self, text):
            """Aggressively removes 'Scene' tags for the final filename."""
            text = text.replace('.', ' ').replace('_', ' ')
            junk_terms = [
                r'\b(19|20)\d{2}\b', r'\bS\d+E\d+\b', r'\bS\d+\b', 
                r'\b1080p\b', r'\b720p\b', r'\b480p\b', r'\b2160p\b', r'\b4k\b',
                r'\bBluRay\b', r'\bWEB-DL\b', r'\bWEBRip\b', r'\bDVD\b', r'\bDVDRip\b',
                r'\bHDR\b', r'\bHDR10\b', r'\bHEVC\b', r'\bx264\b', r'\bx265\b', r'\bH264\b', r'\bH265\b',
                r'\bAAC\b', r'\bAC3\b', r'\bDTS\b', r'\bAtmos\b', r'\bTrueHD\b',
                r'\bRARBG\b', r'\bYIFY\b', r'\bYTS\b', r'\bEZTV\b', r'\bPSA\b',
                r'\bPROPER\b', r'\bREPACK\b', r'\bEXTENDED\b', r'\bUNRATED\b', r'\bDIRECTORS CUT\b',
                r'\[.*?\]', r'\(.*?\)'
            ]
            for term in junk_terms:
                text = re.sub(term, '', text, flags=re.IGNORECASE)
            text = re.sub(r'\s+', ' ', text).strip()
            return text

        def get_tv_details(self, filename):
            match = re.search(r'(?:s|season)\s?(\d{1,2})\s?(?:e|x|episode)\s?(\d{1,2})', filename, re.IGNORECASE)
            if not match: match = re.search(r'(\d{1,2})x(\d{1,2})', filename, re.IGNORECASE)
            
            season_num = "01"
            episode_num = "01"
            if match:
                season_num = f"{int(match.group(1)):02d}"
                episode_num = f"{int(match.group(2)):02d}"

            series_name = "Unknown Series"
            episode_title = ""
            year = ""
            
            search_query = self.clean_final_name(filename)
            
            if self.use_api:
                try:
                    results = self.search.tv_shows({"query": search_query})
                    if results:
                        show = results[0]
                        series_name = show.name
                        if hasattr(show, 'first_air_date') and show.first_air_date:
                            year = show.first_air_date.split('-')[0]
                        try:
                            ep_details = self.episode_api.details(show.id, int(season_num), int(episode_num))
                            if hasattr(ep_details, 'name'):
                                episode_title = ep_details.name
                        except: pass
                except: pass
            
            if series_name == "Unknown Series": 
                series_name = search_query

            return self.sanitize(series_name), year, season_num, episode_num, self.sanitize(episode_title)

        def get_movie_details(self, filename):
            movie_name = self.clean_final_name(filename)
            year = ""
            if self.use_api:
                try:
                    results = self.search.movies({"query": movie_name})
                    if results:
                        top = results[0]
                        movie_name = top.title
                        if hasattr(top, 'release_date') and top.release_date:
                            year = top.release_date.split('-')[0]
                except: pass
            return self.sanitize(movie_name), year

        def get_music_details(self, file_path):
            filename = os.path.basename(file_path)
            tag_artist = "Unknown Artist"
            tag_album = "Unknown Album"
            tag_title = "Unknown Title"
            track = ""
            disc = ""

            fpcalc_path = "fpcalc.exe"
            if getattr(sys, 'frozen', False):
                fpcalc_path = os.path.join(sys._MEIPASS, "fpcalc.exe")
            if os.path.exists(fpcalc_path):
                os.environ["FPCALC"] = fpcalc_path

            if MUTAGEN_AVAILABLE:
                try:
                    audio = mutagen.File(file_path, easy=True)
                    if audio:
                        tag_artist = audio.get('artist', [tag_artist])[0]
                        tag_album = audio.get('album', [tag_album])[0]
                        tag_title = audio.get('title', [os.path.splitext(filename)[0]])[0]
                        tr = audio.get('tracknumber', [''])[0]
                        if tr: track = tr.split('/')[0].zfill(2)
                        dn = audio.get('discnumber', [''])[0]
                        if dn: disc = dn.split('/')[0]
                except: pass

            needs_fingerprint = (tag_artist == "Unknown Artist" or tag_title == "Unknown Title")
            if needs_fingerprint and ACOUSTID_AVAILABLE:
                try:
                    apikey = self.acoustid_key if self.acoustid_key else 'cSpUJKpD' 
                    if shutil.which("fpcalc") or os.path.exists(fpcalc_path):
                        results = acoustid.match(apikey, file_path)
                        for score, recording_id, title_match, artist_match in results:
                            if score > 0.8:
                                tag_artist = artist_match if artist_match else tag_artist
                                tag_title = title_match if title_match else tag_title
                                break
                except: pass

            return self.sanitize(tag_artist), self.sanitize(tag_album), self.sanitize(tag_title), track, disc

    # --- PROCESSING LOGIC ---
    class Processor:
        def __init__(self, config, log_callback):
            self.config = config
            self.log = log_callback
            self.classifier = MediaClassifier(config.get("api_key"), config.get("acoustid_key"))

        def process_file(self, file_path):
            if not os.path.exists(file_path): return False
            
            filename = os.path.basename(file_path)
            ext = os.path.splitext(filename)[1].lower()
            
            junk_exts = ['.txt', '.nfo', '.jpg', '.png', '.exe', '.srt', '.url', '.ini', '.db', '.sfv', '.part', '.crdownload', '.tmp']
            if ext in junk_exts: return False

            destination_root = None
            final_path = None
            log_category = "Unknown"

            if ext in ['.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a']:
                destination_root = self.config["music"]
                if destination_root:
                    artist, album, title, track, disc = self.classifier.get_music_details(file_path)
                    prefix = ""
                    if track:
                        prefix = f"{disc}-{track}" if (disc and disc != "1") else track
                    new_filename = f"{prefix} - {title}{ext}" if prefix else f"{artist} - {title}{ext}"
                    final_path = os.path.join(destination_root, artist, album, new_filename)
                    log_category = "Music"

            elif ext in ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']:
                is_tv = bool(re.search(r'(s\d{1,2}e\d{1,2})|(\d{1,2}x\d{1,2})', filename, re.IGNORECASE))
                if is_tv:
                    destination_root = self.config["tv"]
                    if destination_root:
                        name, year, season, episode, ep_title = self.classifier.get_tv_details(filename)
                        folder_name = f"{name} ({year})" if year else name
                        clean_ep_title = self.classifier.clean_final_name(ep_title) if ep_title else ""
                        clean_series_name = self.classifier.clean_final_name(name)
                        if clean_ep_title:
                            new_filename = f"{clean_series_name} - S{season}E{episode} - {clean_ep_title}{ext}"
                        else:
                            new_filename = f"{clean_series_name} - S{season}E{episode}{ext}"
                        final_path = os.path.join(destination_root, folder_name, new_filename)
                        log_category = f"TV ({folder_name})"
                else:
                    destination_root = self.config["movie"]
                    if destination_root:
                        title, year = self.classifier.get_movie_details(filename)
                        clean_title = self.classifier.clean_final_name(title)
                        new_filename = f"{clean_title} ({year}){ext}" if year else f"{clean_title}{ext}"
                        final_path = os.path.join(destination_root, new_filename)
                        log_category = "Movie"

            if not final_path:
                destination_root = self.config["other"]
                log_category = "Unsorted"
                if destination_root:
                    final_path = os.path.join(destination_root, filename)

            if final_path and destination_root:
                try:
                    dest_dir = os.path.dirname(final_path)
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)
                    base, extension = os.path.splitext(final_path)
                    counter = 1
                    while os.path.exists(final_path):
                        final_path = f"{base}_{counter}{extension}"
                        counter += 1
                    shutil.move(file_path, final_path)
                    self.log(f"SORTED [{log_category}]: {os.path.basename(final_path)}")
                    return True
                except Exception as e:
                    self.log(f"Error moving file: {e}")
                    return False
            return False

    # --- MONITOR HANDLER ---
    if "watchdog" not in MISSING_LIBS:
        class MediaHandler(FileSystemEventHandler):
            def __init__(self, processor, config):
                self.processor = processor
                self.config = config
                self.processed_files = set()

            def on_created(self, event):
                self._process_event(event)
            
            def on_moved(self, event):
                if not event.is_directory: self._handle_file(event.dest_path)

            def on_modified(self, event):
                self._process_event(event)

            def _process_event(self, event):
                if event.is_directory: return
                self._handle_file(event.src_path)

            def _handle_file(self, file_path):
                if file_path.endswith(('.tmp', '.crdownload', '.part')): return
                if file_path in self.processed_files: return
                for key in ["tv", "movie", "music", "other"]:
                    dest = self.config.get(key)
                    if dest and os.path.commonpath([file_path, dest]) == dest: return
                threading.Thread(target=self.process_wrapper, args=(file_path,)).start()

            def process_wrapper(self, file_path):
                if self.wait_for_file_ready(file_path):
                    if self.processor.process_file(file_path):
                        self.processed_files.add(file_path)
                        if len(self.processed_files) > 1000: self.processed_files.clear()
                        self.clean_empty_folder(os.path.dirname(file_path))

            def wait_for_file_ready(self, file_path):
                retries = 0
                max_retries = 30
                while retries < max_retries:
                    if not os.path.exists(file_path): return False
                    try:
                        os.rename(file_path, file_path)
                        size_1 = os.path.getsize(file_path)
                        time.sleep(1)
                        size_2 = os.path.getsize(file_path)
                        if size_1 == size_2 and size_1 > 0: return True
                    except OSError: pass
                    time.sleep(2)
                    retries += 1
                return False

            def clean_empty_folder(self, folder_path):
                monitor_root = os.path.abspath(self.config["monitor"])
                if os.path.abspath(folder_path) == monitor_root: return
                junk_exts = ['.txt', '.nfo', '.jpg', '.png', '.url', '.exe', '.srt', '.ini', '.db']
                try:
                    files = os.listdir(folder_path)
                    if not files:
                        os.rmdir(folder_path)
                        return
                    is_pure_junk = True
                    for f in files:
                        full_path = os.path.join(folder_path, f)
                        if os.path.isdir(full_path):
                            is_pure_junk = False
                            break
                        if os.path.splitext(f)[1].lower() not in junk_exts:
                            is_pure_junk = False
                            break
                    if is_pure_junk:
                        shutil.rmtree(folder_path)
                except: pass

    # --- GUI ---
    class SorterApp:
        def __init__(self, root):
            self.root = root
            self.root.title("Media Sorter (Plex Ready)")
            self.root.geometry("600x780")
            
            if MISSING_LIBS:
                messagebox.showerror("Missing Libraries", f"Missing:\n{', '.join(MISSING_LIBS)}\n\nRun: pip install watchdog tmdbv3api mutagen pyacoustid")
                root.destroy()
                return

            self.config = load_config()
            self.observer = None
            self.processor = None

            # HEADER
            header = tk.Frame(root)
            header.pack(pady=10)
            tk.Label(header, text="Ultimate Media Organiser", font=("Segoe UI", 16, "bold")).pack()
            tk.Label(header, text=f"v{APP_VERSION} | Dev: {DEVELOPER_NAME}", font=("Segoe UI", 8), fg="gray").pack()

            # Warnings
            fpcalc_path = "fpcalc.exe"
            if getattr(sys, 'frozen', False):
                fpcalc_path = os.path.join(sys._MEIPASS, "fpcalc.exe")
                
            if not TMDB_AVAILABLE:
                tk.Label(root, text="Warning: 'tmdbv3api' missing", fg="orange").pack()
            if not MUTAGEN_AVAILABLE:
                tk.Label(root, text="Warning: 'mutagen' missing", fg="red").pack()
            if not ACOUSTID_AVAILABLE:
                tk.Label(root, text="Warning: 'pyacoustid' missing", fg="red").pack()
            if ACOUSTID_AVAILABLE and not (shutil.which("fpcalc") or os.path.exists(fpcalc_path)):
                tk.Label(root, text="Warning: 'fpcalc.exe' not found!", fg="red").pack()

            # Keys Frame
            key_frame = tk.Frame(root)
            key_frame.pack(fill="x", padx=20, pady=5)
            
            tk.Label(key_frame, text="TMDB Key:", width=12, anchor="w").grid(row=0, column=0, sticky="w")
            self.api_var = tk.StringVar(value=self.config.get("api_key", ""))
            tk.Entry(key_frame, textvariable=self.api_var).grid(row=0, column=1, sticky="ew")

            tk.Label(key_frame, text="AcoustID Key:", width=12, anchor="w").grid(row=1, column=0, sticky="w")
            self.acoustid_var = tk.StringVar(value=self.config.get("acoustid_key", ""))
            tk.Entry(key_frame, textvariable=self.acoustid_var).grid(row=1, column=1, sticky="ew")
            
            key_frame.columnconfigure(1, weight=1)

            # Folders
            self.path_vars = {}
            paths_frame = tk.Frame(root)
            paths_frame.pack(fill="x", padx=20, pady=10)

            labels = {
                "monitor": "Inbound Monitor",
                "tv": "TV Destination",
                "movie": "Movie Destination",
                "music": "Music Destination",
                "other": "Other/Unsorted"
            }

            for key, text in labels.items():
                row = tk.Frame(paths_frame)
                row.pack(fill="x", pady=5)
                tk.Label(row, text=text, width=25, anchor="w").pack(side="left")
                var = tk.StringVar(value=self.config.get(key, ""))
                self.path_vars[key] = var
                tk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True, padx=5)
                ttk.Button(row, text="Browse", command=lambda k=key: self.browse_folder(k)).pack(side="left")

            # Controls
            tk.Label(root, text="Live Monitoring", font=("Segoe UI", 10, "bold")).pack(pady=(20, 5))
            monitor_frame = tk.Frame(root)
            monitor_frame.pack()
            self.btn_start = ttk.Button(monitor_frame, text="Start Watching", command=self.start_monitoring)
            self.btn_start.pack(side="left", padx=5)
            self.btn_stop = ttk.Button(monitor_frame, text="Stop Watching", command=self.stop_monitoring, state="disabled")
            self.btn_stop.pack(side="left", padx=5)

            tk.Label(root, text="Manual Operations", font=("Segoe UI", 10, "bold")).pack(pady=(20, 5))
            mass_frame = tk.Frame(root)
            mass_frame.pack()
            self.btn_mass = ttk.Button(mass_frame, text="Select Folder & Import All", command=self.run_mass_import)
            self.btn_mass.pack(side="left", padx=20)
            
            # ABOUT BUTTON (NEW)
            self.btn_about = ttk.Button(mass_frame, text="About / Help", command=self.show_about)
            self.btn_about.pack(side="left", padx=5)

            # Log
            self.log_area = scrolledtext.ScrolledText(root, height=8, state='disabled')
            self.log_area.pack(fill="both", expand=True, padx=20, pady=(20, 10))

            # Attribution
            attribution_frame = tk.Frame(root)
            attribution_frame.pack(side="bottom", pady=10)
            tk.Label(attribution_frame, text="POWERED BY TMDB & ACOUSTID", font=("Segoe UI", 10, "bold"), fg="#0d253f").pack()
            tk.Label(attribution_frame, text="This product uses the TMDB API but is not endorsed or certified by TMDB.", font=("Segoe UI", 8), fg="gray").pack()

        def browse_folder(self, key):
            folder = filedialog.askdirectory()
            if folder:
                self.path_vars[key].set(folder)
                self.save_current_config()

        def save_current_config(self):
            for k, v in self.path_vars.items():
                self.config[k] = v.get()
            self.config["api_key"] = self.api_var.get()
            self.config["acoustid_key"] = self.acoustid_var.get()
            save_config(self.config)

        def log(self, message):
            self.root.after(0, lambda: self._log(message))

        def _log(self, message):
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, message + "\n")
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')

        def show_about(self):
            info = (
                f"Media Organiser v{APP_VERSION}\n"
                f"Developer: {DEVELOPER_NAME}\n\n"
                "--- HOW TO USE ---\n"
                "1. SETUP: Enter your TMDB and AcoustID keys for full features.\n"
                "2. FOLDERS: Select your 'Inbound Monitor' (Downloads) and where you want files moved to.\n\n"
                "--- MODES ---\n"
                "LIVE MONITORING: Runs in the background. Any file saved or dragged into 'Inbound' is instantly sorted.\n\n"
                "MASS IMPORT: Select an existing folder (e.g. USB drive). The tool will process ALL files inside it.\n"
            )
            messagebox.showinfo("About / Help", info)

        def start_monitoring(self):
            self.save_current_config()
            if not self.config.get("monitor"):
                messagebox.showerror("Error", "Select a Monitored Folder.")
                return

            self.processor = Processor(self.config, self.log)
            handler = MediaHandler(self.processor, self.config)
            self.observer = Observer()
            self.observer.schedule(handler, self.config["monitor"], recursive=True)
            self.observer.start()
            
            self.btn_start.config(state="disabled")
            self.btn_stop.config(state="normal")
            self.log("--- Live Monitoring Started ---")

        def stop_monitoring(self):
            if self.observer:
                self.observer.stop()
                self.observer.join()
                self.observer = None
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
            self.log("--- Live Monitoring Stopped ---")

        def run_mass_import(self):
            self.save_current_config()
            source_folder = filedialog.askdirectory(title="Select Folder to Import From")
            if not source_folder: return
            
            if messagebox.askyesno("Confirm Import", "This will move and rename ALL media files. Continue?"):
                self.log(f"--- Starting Mass Import from: {source_folder} ---")
                threading.Thread(target=self._mass_import_thread, args=(source_folder,)).start()

        def _mass_import_thread(self, source_folder):
            processor = Processor(self.config, self.log)
            count = 0
            for root, dirs, files in os.walk(source_folder):
                for file in files:
                    if processor.process_file(os.path.join(root, file)): count += 1
            self.log(f"--- Mass Import Complete: {count} files processed ---")
            messagebox.showinfo("Complete", f"Processed {count} files.")

    if __name__ == "__main__":
        root = tk.Tk()
        SorterApp(root)
        root.mainloop()

# --- ERROR CATCHING BLOCK ---
except Exception as e:
    root = tk.Tk()
    root.withdraw()
    error_msg = traceback.format_exc()
    messagebox.showerror("Startup Error", f"The programme failed to start.\n\nError Details:\n{error_msg}")
    root.destroy()