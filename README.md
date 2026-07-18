
<div align="right">
  <img src="https://count.getloli.com/@Mogrul?name=Mogrul&theme=rule34&padding=7&offset=0&align=top&scale=1&pixelated=1&darkmode=1">
</div>

# Simpcity Scraper
A multi-threaded scraper for simpcity.cr threads that automatically crawls through multiple pages, extracts external media URLs from posts, and downloads the associated content.

Once a thread has been processed, the tool can optionally scan downloaded images and videos for duplicates, helping eliminate redundant files and keep your collection organized.

Downloaded files are named using the original post date and a unique identifier generated from the direct media URL and original filename. This ensures that different files receive distinct IDs while the same file downloaded multiple times will always produce the same identifier, preventing duplicate downloads.

<p align="center">
  <img src="https://github.com/Mogrul/SimpCity-Scraper/blob/main/assets/header.jpg" alt="Logo" width="300">
</p>

## Usage
### Executable (Recommended)
- Download the executable from [Latest Release](https://github.com/Mogrul/SimpCity-Scraper/releases/latest)
- Extract the files into a directory of your choosing.
- Open a terminal from that directory
- Login to SimpCity on a browser and extract the sites cookies using a tool like [addon](https://addons.mozilla.org/en-GB/firefox/addon/get-cookies-txt-locally/)
- Name the file `simpcity.txt` and place it into a directory called `.cookies` of the root directory
- Run `.\SimpCityScraper-1.1.1-win-x86_64.exe URL` and it should download to the value set in `config.yaml`

### Source
- Download the source using [github](https://github.com/Mogrul/SimpCity-Scraper/archive/refs/heads/main.zip) or `git clone https://github.com/Mogrul/SSDownloader`
- Create a virtual python environment using `python -m venv .venv`
- Activate the environment using `.venv\Scripts\activate`
- Install the required packages using `pip install -r requirements.txt`
- Login to SimpCity on a browser and extract the sites cookies using a tool like [addon](https://addons.mozilla.org/en-GB/firefox/addon/get-cookies-txt-locally/)
- Name the file `simpcity.txt` and place it into a directory called `.cookies` of the root directory
- Run the main.py URL and it should download to the value set in `config.yaml`

## Supported sites
- https://bunkr.cr
- https://cyberdrop.cr
- https://gofile.io
- https://goonbox.cr
- https://pixeldrain.com
- https://turbo.cr

## Arguments
- `URLs`: Default required argument, a list of simpcity.cr thread URLs to scrape
- `-pc / --print-config`: Prints the current configuration settings from config.toml
- `-cd / --check-duplicates (PATH)`: Combined with `-i / --images` and or `-v / --videos` to check for duplicates without starting any downloads
- `-w / --watched`: Automatically import your watched threads to the download list
- `--debug`: Set the output to terminal to debug mode, printing a more verbose output

## Config
```toml
links = [] # Links to download from SimpCity

[downloads]
location = "Downloads" # Location to where the downloads will go
skip_domains = ["bunkr.cr"] # Skip domains to download from, empty for all
watched_threads = false # Extract watched threads from your simpcity account to download

[database]
enabled = false # Disable / Enable the database functionality
location = "data/data.db" # Location where the database will be generated

[duplication]
images = false # To check for duplicate images
videos = false # To check for duplicate videos -- intensive
threshold = 0.9 # Threshold to mark files as duplicate: 0.1 = 10% similarity
samples = 3 # Amount of samples to get when checking video duplicates
ffmpeg_path = "C:\\ffmpeg\\bin\\ffmpeg.exe" # Path to FFMPEG for video checking (cuda compatible version best)
ffprobe_path = "C:\\ffmpeg\\bin\\ffprobe.exe" # For probing video files to get frame counts

[network]
timeout = 10 # Time in seconds before a request times out
chunk_size = 1048576 # Chunk size in bytes to download at
cookies = ".cookies" # Folder where cookies.txt files are located

[network.headers]
User-Agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
Accept = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
Accept-Encoding = "gzip, deflate, zstd"
Connection = "keep-alive"
```
