# Simp Scraper
A multi-threaded simpcity.cr thread multi-page scraping tool

## Usage
### Source
- Download the source using [github](https://github.com/Mogrul/SSDownloader/archive/refs/heads/main.zip) or `git clone https://github.com/Mogrul/SSDownloader`
- Create a virtual python environment using `python -m venv .venv`
- Activate the environment using `.venv\Scripts\activate`
- Install the required packages using `pip install -r requirements.txt`
- Login to SimpCity on a browser and extract the sites cookies using a tool like [addon](https://addons.mozilla.org/en-GB/firefox/addon/get-cookies-txt-locally/)
- Name the file `simpcity.txt` and place it into a directory called `.cookies` of the root directory
- Run the main.py URL and it should download to the value set in `config.yaml`

### Executable (Recommended)
- Download the executable from [Latest Release](https://github.com/Mogrul/SSDownloader/releases/latest)
- Extract the files into a directory of your choosing.
- Open a terminal from that directory
- Login to SimpCity on a browser and extract the sites cookies using a tool like [addon](https://addons.mozilla.org/en-GB/firefox/addon/get-cookies-txt-locally/)
- Name the file `simpcity.txt` and place it into a directory called `.cookies` of the root directory
- Run `.\SimpScraper.exe URL` and it should download to the value set in `config.yaml`

## Supported sites
- https://turbo.cr/
- https://goonbox.cr/
- https://pixeldrain.com/
- https://cyberdrop.cr/
- https://bunkr.cr/

## Config
```yaml
# Download settings.
downloads:
  output: Downloads
  
  # Remove duplicate files after downloading thread.
  remove_image_duplicates: True
  remove_video_duplicates: True
  similarity_threshold: 0.9 # % to delete files at .1 = 10%

  # Number of bytes to read/write at a time when downloading.
  # 1048576 = 1 MiB
  chunk_size: 1048576

# Network and thread settings.
network:
  # HTTP request timeout in seconds.
  timeout: 30

  # User agent to use in HTTP requests.
  user_agent: {}

  # Number of concurrent download workers.
  workers: 10

# Filtering options
filters:
  # List of domains to ignore.
  # Leave empty to allow all domains.
  excluded_domains: []

  # Example:
  # excluded_domains:
  #   - bunkr
  #   - goonbox
```
