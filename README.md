# Fextralife Weapon & Armor Scraper for Dragon's Dogma: Dark Arisen

Python scripts to scrape weapon and armor data from the Dragon's Dogma: Dark Arisen Wiki on Fextralife:
https://dragonsdogma.wiki.fextralife.com

This project parses item pages to extract names, stats, resistances, vocations, locations, descriptions, and item images, and produces clean JSON output for weapons and armor.

---

## Features

- Scrapes armor and weapon pages from the Fextralife Wiki
- Downloads item images
- Parses stats, elemental resistances, and debilitation resistances
- Detects equipable vocations for each item
- Extracts locations (where items are found or purchased)
- Extracts concise item descriptions
- Generates JSON output (clean, normalized)
- Validation script to check JSON for null values

---

## Repository Structure

```text
.
├── FextralifeWeaponScraper.py        # Main parser for weapons (also used for armor)
├── FextralifeArmorListScraper.py    # Scraper for armor list and page links
├── scraped_weapon_data/             # Downloaded weapon images
├── scraped_armor_images/            # Downloaded armor images
├── all_weapons_data.json            # Parsed weapon data
├── all_armor_data.json              # Parsed armor data
├── validate_json_no_nulls.py        # Utility script to validate JSON
└── README.md
```

---

## Requirements

- Python 3.8+
- requests
- beautifulsoup4

(You may want to run inside a virtual environment.)

---

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/Hoovie105/parse_fextralife_weapon_DDDA.git
cd parse_fextralife_weapon_DDDA
pip install requests beautifulsoup4
```

---

## Usage

Run the scrapers in this order:

```bash
python FextralifeArmorListScraper.py
python FextralifeWeaponScraper.py
```

- Scraped images will be saved into `scraped_weapon_data/` and `scraped_armor_images/`.
- Parsed JSON files will be saved as `all_weapons_data.json` and `all_armor_data.json`.

Validate the generated JSON (example):

```bash
python validate_json_no_nulls.py all_weapons_data.json
python validate_json_no_nulls.py all_armor_data.json
```

---

## Notes & Caveats

- Some wiki pages may be incomplete or missing images; the scrapers include fallbacks for missing values.
- Elemental and debilitation resistances are normalized for consistent JSON formatting.
- Locations, descriptions, and vocations are cleaned/normalized to improve readability.
- If you plan to run heavy scraping, please respect the target site's robots.txt and rate-limit your requests.

---

## Contributing

- Feel free to open issues or pull requests to improve parsing, add more normalization rules, or add tests.
- Attribution is appreciated for derived projects.

---

## License

This project is intended for personal use, learning, and development. Attribution is appreciated if used in derived projects.

---

Author: Hoovie105
