# Vinted Exporter

**A minimal Python tool for exporting photos and listing text from a Vinted profile you are authorized to access.**

[🇮🇹 Guida in italiano](README.it.md)

> [!WARNING]
> **Authorization required.** Vinted's [current Terms of Service](https://www.vinted.com/terms-and-conditions) prohibit unauthorized use of scraping/crawling tools and copying site content. Use this code only when Vinted has authorized the relevant automation and you have the necessary rights to the listings and photographs. This repository is educational and is **not** affiliated with, endorsed by, or an official integration of Vinted. It does not bypass CAPTCHAs or access controls.

## Features

- Discovers visible item links on a member's public profile, including items loaded during scrolling or via a *Show more* button when accessible.
- Opens each listing in a visible Chromium browser.
- Attempts to save the title, description, brand, price, currency, and all discoverable listing photos.
- Creates one folder per listing, with `descrizione.txt` and `prodotto.json`.
- Writes an overall `indice.json` with the items processed successfully enough to extract data.
- Can limit the number of listings, choose an output directory, and adjust the delay between listings.
- Skips previously completed items (identified by a `completo: true` value in the item's JSON).
- Does not require passwords, API keys, or cookies copied from your account.

**Status:** experimental / best effort. Browser selectors and Vinted page layouts can change without notice. Neither complete profile discovery nor full-resolution downloads are guaranteed. The script has offline unit tests but has **not** been validated against a live Vinted profile in this release.

## Requirements

- Python 3.10+ (recommended: Python 3.11 or newer).
- A desktop session able to display a Chromium browser (Linux, macOS, or Windows).
- Internet access for the browser and image requests.

## Installation

### Linux (Arch Linux)

```bash
sudo pacman -S --needed python python-pip

git clone https://github.com/YOUR-USERNAME/vinted-exporter.git
cd vinted-exporter

python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Replace `YOUR-USERNAME` with the account hosting your repository. Until the repository is published, use the downloaded project folder instead of `git clone`.

### Linux (Ubuntu / Debian)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install --with-deps chromium
```

Run the above commands from inside the project folder.

### macOS / Windows

Set up a Python 3.10+ environment, create and activate a virtual environment, then run:

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Windows PowerShell environment activation: `.venv\Scripts\Activate.ps1`.

## Quick start

In the activated virtual environment:

```bash
python vinted_export.py "https://www.vinted.it/member/123456-username"
```

**Process only five listings** for an initial test:

```bash
python vinted_export.py "https://www.vinted.it/member/123456-username" --max 5
```

**Choose an output folder** and specify a longer pause:

```bash
python vinted_export.py "https://www.vinted.it/member/123456-username" --output exports/my-shop --delay 4
```

Replace the example URL with the profile URL you are authorized to process.

The program opens Chromium, navigates to the supplied profile, and **waits for you to press Enter in the terminal**. Check the browser page first; handle any normal consent prompt manually. The program does not solve CAPTCHAs or bypass access restrictions. It then scrolls to discover item links and processes each item with a default 2-second delay.

## Options

| Option | Default | Description |
| --- | --- | --- |
| `profilo` | required | HTTPS profile URL in the form `https://www.vinted.it/member/123456-name` |
| `--max N` | `0` | Maximum number of items (0 = no explicit limit) |
| `--output PATH` | `vinted_export` | Export directory |
| `--delay SECONDS` | `2` | Pause between item pages; must be non-negative |
| `-h`, `--help` | — | Display usage help |

`--max 0` means no limit on the *discovered* listings: it does not guarantee that the entire catalog will be found.

## Output structure

```text
vinted_export/
├── 123456789-blue-nike-jacket/
│   ├── 01.webp
│   ├── 02.jpg
│   ├── descrizione.txt
│   └── prodotto.json
├── 123456790-adidas-hoodie/
│   ├── 01.webp
│   ├── descrizione.txt
│   └── prodotto.json
└── indice.json
```

Image extensions depend on the server's image content type (JPEG, PNG, or WebP). The script does not modify or convert image pixels, and doesn't guarantee that the largest possible image variant is available.

An example `prodotto.json` (illustrative data, not a real listing):

```json
{
  "titolo": "Blue Nike jacket",
  "descrizione": "Example condition and size notes",
  "prezzo": "25.00",
  "valuta": "EUR",
  "marca": "Nike",
  "urls_foto": ["https://images.vinted.net/example/photo.webp"],
  "id": "123456789",
  "url": "https://www.vinted.it/items/123456789-blue-nike-jacket",
  "foto": ["01.webp"],
  "errori": [],
  "completo": true
}
```

Some fields can be blank or `null`. `completo` is only `true` when a description and at least one image were obtained without image-download errors. A missing description can reflect selector changes, access restrictions, or a missing description in the source. `indice.json` is written after the processing loop and might not exist if the process is interrupted early.

## Tests

No live Vinted account, browser launch, or network is needed for the unit tests:

```bash
python -m unittest discover -s tests -v
python -m compileall -q vinted_export.py
```

## Troubleshooting

| Problem | What to check |
| --- | --- |
| `ModuleNotFoundError: playwright` | Activate `.venv` and install requirements again. |
| Chromium executable missing | Run `python -m playwright install chromium`. |
| Browser does not open on Linux | Run inside an active graphical session; make sure your environment supports Chromium and its dependencies. |
| No items found | Make sure the correct profile is visible; the layout may have changed or access may be restricted. Do not bypass restrictions. |
| No description/photos for an item | Not all fields are exposed consistently; selectors or gallery behavior may have changed. |
| Some images fail | The CDN may reject or stop serving individual URLs. Review the item's `errori` field. |
| Re-running does not overwrite an item | Completed items are skipped; remove that item's exported folder to re-export it. |

## Design and boundaries

- **Simple architecture:** one Python source file and Playwright; no databases, credentials, private endpoints, or proxy rotation.
- **No evasion:** no CAPTCHA solving, rate-limit workarounds, fingerprint spoofing, or anti-bot bypass.
- **Privacy:** don't commit exported images, descriptions, browser state, or other user content. The `.gitignore` excludes common export folders, but you should still inspect `git status` before pushing.
- **Rights & terms:** get Vinted's authorization for automated use and have rights to the exported materials. The ability to view a listing publicly does **not** grant permission to reproduce it elsewhere.
- **Limits:** visible-page extraction can miss items, metadata, or images; no promise of stable compatibility with Vinted.

## Contributing

Bug reports and small pull requests are welcome. Please include reproducible behavior and test fixtures that do **not** contain other people's listing content or personal data. Run the unit tests before submitting. Do not contribute features for bypassing CAPTCHAs, authentication, access controls, or anti-bot protections.

## License

MIT License — see [LICENSE](LICENSE). Third-party listing text and photos are **not** covered by this project's source-code license.
