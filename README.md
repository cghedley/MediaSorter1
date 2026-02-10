# 🎬 Media Sorter Pro

A powerful, automated media organization tool featuring a modern GUI. Media Sorter Pro monitors your downloads folder in real-time and automatically moves files into organized TV Shows, Movies, and Music libraries using intelligent filename parsing and metadata APIs.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-win)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

* **Automated Monitoring:** Watches folders in real-time using `watchdog` – no manual scanning required.
* **Intelligent Parsing:**
    * Detects **TV Shows** (e.g., `S01E01`, `1x01`) and organizes them into `Show Name/Season XX/` folders.
    * Detects **Movies** and extracts years to create `Movie Name (Year)` folders.
    * Cleans junk tags (e.g., `1080p`, `x264`, `RARBG`) for clean filenames.
* **Music Fingerprinting:** Uses **AcoustID** (audio fingerprinting) to identify music files even if filenames are garbled (requires FFmpeg).
* **Modern GUI:** A clean, dark-mode interface built with HTML/JS and Python (`Eel`).
* **Safe File Handling:**
    * Prevents moving incomplete downloads by checking file stability.
    * Handles duplicate files automatically.
* **API Integration:** Connects to TMDB, TVMaze, and MusicBrainz for accurate metadata.

## 🛠️ Installation & Setup

### Prerequisites
1.  **Python 3.8+** installed.
2.  **FFmpeg** (Required for music identification).
    * [Download FFmpeg Essentials](https://www.gyan.dev/ffmpeg/builds/)
    * Extract `ffmpeg.exe` and place it in the project root folder.

### Installation
1.  Clone the repository:
    ```bash
    git clone [https://github.com/yourusername/media-sorter-pro.git](https://github.com/yourusername/media-sorter-pro.git)
    cd media-sorter-pro
    ```

2.  Install python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Run the application:
    ```bash
    python MediaSorter.py
    ```

## 📦 Building a Standalone .EXE

To distribute this application as a single executable file for Windows users who don't have Python installed:

1.  Install PyInstaller:
    ```bash
    pip install pyinstaller
    ```

2.  Run the build command (Note: this bundles the `web` folder inside the exe):
    ```powershell
    python -m PyInstaller --noconsole --onefile --add-data 'web;web' --icon=NONE MediaSorter.py
    ```

3.  **Important:** After building, navigate to the `dist/` folder and **copy `ffmpeg.exe`** into that folder. The EXE requires FFmpeg to sit next to it to process music files.

## ⚙️ Configuration

The application uses a `sorter_config.json` file to store settings. You can configure these easily via the GUI:

| Setting | Description |
| :--- | :--- |
| **Monitor Folder** | The folder where new downloads arrive (e.g., `C:\Downloads`). |
| **TV/Movie/Music** | Destination folders for sorted media. |
| **API Keys** | (Optional) TMDB and AcoustID keys for higher accuracy. |
| **AI Correction** | Enables online lookups to correct filenames (e.g., "bbt s01e01" -> "The Big Bang Theory"). |

## 📂 Project Structure

```text
/
├── MediaSorter.py       # Main Python backend logic
├── sorter_config.json   # User configuration (auto-generated)
├── requirements.txt     # Python dependencies
├── web/                 # GUI Frontend
│   ├── index.html
│   ├── main.js
│   └── styles.css
└── dist/                # Compiled .exe files appear here
