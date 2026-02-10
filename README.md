# 🎬 Media Sorter Pro

A powerful, automated media organization tool with a modern GUI. It monitors your downloads folder and automatically sorts files into TV Shows, Movies, and Music folders using intelligent filename parsing and metadata APIs.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-win)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)]https://creativecommons.org/licenses/by/4.0/)

## ✨ Features

* **Automated Monitoring:** Watches folders in real-time using `watchdog`.
* **Intelligent Parsing:** Detects TV shows (S01E01), Movies (Year), and quality tags.
* **Modern GUI:** Built with Python (Eel) and HTML/CSS/JS for a clean, dark-mode interface.
* **Music Fingerprinting:** Uses **AcoustID** to identify music files even with bad filenames.
* **Metadata APIs:** Integrates with TMDB, TVMaze, and MusicBrainz for accurate sorting.
* **Safe Moves:** Checks for file stability (to avoid moving files currently downloading) and handles duplicates.

## 🛠️ Installation

### Prerequisites
* Python 3.8 or higher
* **FFmpeg** (Required for Music Fingerprinting). [Download here](https://www.gyan.dev/ffmpeg/builds/) and add to your system PATH or place `ffmpeg.exe` in the root folder.

### Setup
1.  Clone the repository:
    ```bash
    git clone [https://github.com/yourusername/media-sorter-pro.git](https://github.com/yourusername/media-sorter-pro.git)
    cd media-sorter-pro
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Run the application:
    ```bash
    python MediaSorter.py
    ```

## 📦 Building for Windows (.exe)

To create a standalone executable that runs without Python installed:

1.  Install PyInstaller:
    ```bash
    pip install pyinstaller
    ```

2.  Run the build command (PowerShell):
    ```powershell
    python -m PyInstaller --noconsole --onefile --add-data 'web;web' --icon=NONE MediaSorter.py
    ```

3.  The executable will appear in the `dist/` folder.
    * **Note:** If using Music features, copy `ffmpeg.exe` into the `dist/` folder next to your new executable.

## ⚙️ Configuration

The app uses a `sorter_config.json` file to store your preferences. You can configure these in the "Configuration" tab of the GUI:

* **Monitor Path:** Where files arrive (e.g., Downloads).
* **Destination Paths:** Where files should go (TV, Movies, Music).
* **API Keys (Optional):**
    * **TMDB:** For movie posters and accurate metadata.
    * **AcoustID:** For audio fingerprinting.

## 📂 Project Structure

```text
/
├── MediaSorter.py       # Main Python logic
├── requirements.txt     # Python dependencies
├── web/                 # GUI Source Code
│   ├── index.html
│   ├── main.js
│   └── styles.css
└── sorter_config.json   # User config (auto-generated)
