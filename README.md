# Get-img

A simple Python practice project that downloads all images from a web page.

## Features

- Uses `requests` to fetch page HTML
- Uses `BeautifulSoup` to parse all `img` tags
- Converts relative image links to full URLs
- Downloads images into the `images` folder by default
- Names files automatically like `img_001.jpg`
- Skips duplicate image URLs
- Supports browser mode for JavaScript-heavy pages

## Requirements

- Python 3.10+

## Install

```powershell
cd C:\Users\f2932\Desktop\code\Get-img
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
python main.py https://example.com
```

Choose a custom output folder:

```powershell
python main.py https://example.com --output my_images
```

Use browser mode for dynamic websites such as many shopping pages:

```powershell
python main.py "https://www.1688.com/..." --browser
```

## Project Files

- `main.py`: main crawler and downloader
- `requirements.txt`: Python dependencies
- `.gitignore`: files and folders not tracked by Git

## Notes

- Some websites block automated requests, so a few image downloads may fail.
- For JavaScript-rendered pages, use `--browser`.
