# Ultimate Media Organiser

**Version:** 1.2 (Active Cleanup)
**Developer:** Chris Hedley

A robust, automated Python tool designed to sort, rename, and organise media files (TV, Movies, Music) into a clean, Plex/Emby-compliant folder structure.

It features live folder monitoring, mass import capabilities, and advanced identification using TMDB for video and AcoustID audio fingerprinting for music.

---

## 🚀 Key Features

### 1. Intelligent Identification
* **TV Shows:** Identifies Series, Season, Episode, and fetches the specific Episode Title using the TMDB API.
* **Movies:** Identifies Movie Name and Release Year.
* **Music:** Uses **Audio Fingerprinting** (AcoustID) to listen to the audio file. This allows it to identify songs even if the filename is generic (e.g., "Track01.mp3") or has missing tags.

### 2. Plex-Ready Renaming
Automatically strips "scene" tags (1080p, x264, RARBG, etc.) and renames files to match strict media server standards:
* **TV:** `Series Name (Year) \ Series Name - S01E01 - Episode Title.ext`
* **Movies:** `Movie Title (Year).ext`
* **Music:** `Artist Name \ Album Name \ 01 - Track Title.ext` (Supports Multi-Disc `1-01` numbering).

### 3. Active Cleanup
* After moving media files, the tool actively scans the source sub-folders.
* If only "junk" files remain (txt, nfo, jpg, url, samples), it automatically deletes them and removes the empty folder to keep your Downloads directory clean.

### 4. Dual Modes
* **Live Monitoring:** Runs in the background. As soon as a file is downloaded or dragged into your "Inbound" folder, it is instantly processed.
* **Mass Import:** Allows you to select an existing folder (like an old USB drive or hard drive) and process thousands of files in one go.

---

## 🛠️ Installation & Setup

### 1. Prerequisites
You must have **Python 3.8** or higher installed.

### 2. Install Python Libraries
Open your terminal or command prompt and run the following command:

```bash
pip install watchdog tmdbv3api mutagen pyacoustid

```

### 3. The Audio Engine (Crucial)

For music fingerprinting to work, you must install the **Chromaprint** engine.

1. Download the **fpcalc** tool for Windows from: https://acoustid.org/chromaprint
2. Extract the zip file.
3. **Copy `fpcalc.exe` and paste it into the same folder as this script.**

---

## ⚙️ Configuration (API Keys)

To get the full power of this tool, you need free API keys. The GUI has status indicators to show if these are working.

1. **TMDB Key (for TV/Movies):**
* Sign up at https://www.themoviedb.org/
* Go to Settings > API to generate a key.


2. **AcoustID Key (for Music):**
* Sign in at https://acoustid.org/
* Click "Register an application" to get a key.



*Note: The tool will still function without keys using basic filename guessing, but accuracy will be significantly lower.*

---

## 📖 How to Use

Run the script using Python:

```bash
python MediaSorter.py

```

### The Interface

1. **API Keys:** Enter your TMDB and AcoustID keys in the top fields.
2. **Inbound Monitor:** Browse and select your Downloads folder (or wherever files arrive).
3. **Destinations:** Select the root folders for your TV, Movie, and Music libraries.
4. **Buttons:**
* **Start Watching:** Locks the configuration and begins monitoring the Inbound folder for new files.
* **Mass Import:** Opens a dialog to select a folder. It will recursively find every media file inside that folder and organise it.



---

## ⚠️ File Sorting Logic

**Files are processed based on extension:**

* **Music:** .mp3, .flac, .wav, .aac, .ogg, .m4a
* **Video:** .mkv, .mp4, .avi, .mov, .wmv, .flv, .webm, .m4v

**Files ignored (Junk):**

* .txt, .nfo, .jpg, .png, .exe, .srt, .url, .ini, .db, .sfv, .part, .crdownload

---

## 📝 Disclaimer

This product uses the TMDB API but is not endorsed or certified by TMDB.
This tool performs file deletion (cleanup) and renaming. While safe, always ensure you have backups of critical data before running mass operations.

```

```
