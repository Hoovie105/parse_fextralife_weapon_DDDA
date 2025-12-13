# 256 weapons wiki pages total
# 16 weapons starting with Dwells-In-Light ending at wounded heart do not have links (add maually to wiki then scrape)
# some weapon elements dont have text
import requests
from bs4 import BeautifulSoup
import re
import os
import json
import time
from urllib.parse import urlparse

class FextralifeWeaponsListScraper:
    """
    A class to scrape the weapons list page and extract links to individual weapons.
    Provides methods to retrieve all weapon URLs from the Fextralife weapons page.
    """
    
    BASE_URL = "https://dragonsdogma.wiki.fextralife.com"
    WEAPONS_LIST_URL = "https://dragonsdogma.wiki.fextralife.com/Weapons"
    
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self):
        """Initializes the weapons list scraper."""
        pass

    def get_weapon_links(self, url=None):
        """
        Scrapes the weapons list page and extracts all weapon links.
        Weapons are organized by category (Daggers, Longswords, etc.) with images.
        
        :param url: Optional URL to scrape (defaults to WEAPONS_LIST_URL)
        :return: A list of tuples containing (weapon_name, weapon_url)
        """
        if url is None:
            url = self.WEAPONS_LIST_URL
        
        try:
            r = requests.get(url, headers=self.HEADERS)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error accessing {url}: {e}")
            return []
        
        soup = BeautifulSoup(r.text, "html.parser")
        weapon_links = []

        # Find a reasonable content container (robust to class name variations)
        content = soup.find("div", class_="page-content") or soup.find("div", class_="content") or soup

        # Collect all wiki_link anchors that appear inside any "row" blocks (these hold weapon tiles),
        # but also be resilient if the site uses slightly different structure.
        anchors = []
        for div in content.find_all("div", class_=lambda c: c and "row" in c.split()):
            for a in div.find_all("a", href=True, class_="wiki_link"):
                href = a.get("href").strip()
                title = (a.get("title") or a.text or "").strip()
                if not title:
                    continue
                anchors.append((title, href))

        # Fallback: if no anchors found in rows, collect all wiki_link anchors on the page
        if not anchors:
            for a in content.find_all("a", href=True, class_="wiki_link"):
                href = a.get("href").strip()
                title = (a.get("title") or a.text or "").strip()
                if not title:
                    continue
                anchors.append((title, href))

        # Basic blacklist to exclude navigation / category links that are not individual weapons
        blacklist_titles = set([
            "Dragons Dogma Wiki", "Wiki", "Quests", "Merchants", "Gransys", "Bitterblack Isle",
            "Enemies", "Skills", "Vocation", "Bosses", "Combat", "Weapon Information",
            "Weapon Types", "Weapon Skills Guide", "Weapon", "Weapons", "Navigation", "Search Results"
        ])
        blacklist_hrefs_prefix = ("/file", "#", "//")

        # Build unique list preserving order
        seen = set()
        unique_links = []
        for title, href in anchors:
            # remove site prefix from title when present
            clean_name = title.replace("Dragons Dogma ", "").replace("Dragon's Dogma ", "").strip()

            # filter out obvious non-weapon links
            if not href or href.lower().startswith(blacklist_hrefs_prefix):
                continue
            if any(bt.lower() == clean_name.lower() for bt in blacklist_titles):
                continue
            # Previously we skipped single-word titles ending with 's' as probable category pages.
            # That heuristic incorrectly filtered out valid single-word weapon names
            # (e.g. "Meniscus"). Rely on explicit blacklist titles and href prefixes
            # instead to avoid dropping legitimate weapons.

            # normalize absolute URL
            if href.startswith("/"):
                absolute_url = self.BASE_URL + href
            else:
                absolute_url = href

            if absolute_url in seen:
                continue
            seen.add(absolute_url)
            unique_links.append((clean_name, absolute_url))

        return unique_links


class FextralifeWeaponScraper:
    """
    A class to scrape weapon details and download associated images
    from a Fextralife Dragon's Dogma wiki page.
    """
    
    # Base URL for the wiki, used to construct absolute image URLs
    BASE_URL = "https://dragonsdogma.wiki.fextralife.com"
    
    # Common headers to make requests look like a browser
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, download_dir="weapon_images"):
        """
        Initializes the scraper with a specific directory for image downloads.
        """
        self.download_dir = download_dir
        # Ensure the download directory exists upon initialization
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    # ---------------------------
    # Minimal Patch: image extractor
    # ---------------------------
    def _extract_real_image_url(self, img):
        """
        Extracts the real image URL from common lazy-load attributes.
        Prefers high-resolution candidates from srcset-like attributes, then
        data-src, data-original, data-image, data-url, and finally src.
        Returns None if nothing usable is found.
        """
        if img is None:
            return None

        # 1) data-srcset or data-srcset variations (choose the last/largest candidate)
        for key in ("data-srcset", "srcset"):
            val = img.get(key)
            if val:
                # srcset format: "url1 1x, url2 2x" or "url1 480w, url2 800w"
                parts = [p.strip() for p in val.split(",") if p.strip()]
                if parts:
                    # prefer the last entry (usually largest)
                    last = parts[-1]
                    # the URL is the first token in that part
                    url = last.split()[0]
                    if url:
                        return url

        # 2) data-src, data-original, data-image, data-url (common lazy attributes)
        for key in ("data-src", "data-original", "data-image", "data-url", "data-lazy", "data-src-large"):
            val = img.get(key)
            if val:
                return val

        # 3) src attribute fallback (may be alpha-only but keep as last resort)
        src = img.get("src")
        if src:
            return src

        return None

    def _normalize_image_url(self, url):
        """
        Normalize relative image URLs to absolute ones and handle protocol-relative URLs.
        """
        if not url:
            return None
        url = url.strip()
        # protocol-relative
        if url.startswith("//"):
            return "https:" + url
        # absolute URL already
        if url.startswith("http://") or url.startswith("https://"):
            return url
        # relative path on the same domain
        if url.startswith("/"):
            return self.BASE_URL + url
        # sometimes images are given without leading slash
        # try joining with base
        return self.BASE_URL + "/" + url

    def _download_image(self, image_url, weapon_name):
        """
        Downloads an image from a URL and saves it to the local directory.
        Includes retry logic with exponential backoff to handle server delays.
        (Internal method denoted by leading underscore)
        """
        
        # 1. Create a safe, unique filename
        # Get the file extension from the URL path
        parsed_url = urlparse(image_url)
        _, file_extension = os.path.splitext(parsed_url.path)

        # Clean the weapon name to use it as a base filename
        safe_name = re.sub(r'[^\w\-_\.]', '', weapon_name.replace(' ', '_'))
        
        filename = f"{safe_name}{file_extension}" if file_extension else f"{safe_name}.img"
        local_path = os.path.join(self.download_dir, filename)

        # Retry configuration
        max_retries = 3
        retry_delay = 2  # Start with 2 seconds
        
        for attempt in range(max_retries):
            try:
                # Use requests to download the image file
                print(f"Downloading {weapon_name} from {image_url}...")
                img_data = requests.get(image_url, stream=True, headers=self.HEADERS, timeout=10)
                img_data.raise_for_status() 

                with open(local_path, 'wb') as handler:
                    # Write the content in chunks
                    for chunk in img_data.iter_content(chunk_size=8192):
                        handler.write(chunk)

                # Return the path relative to the script's execution
                return local_path

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"Error downloading image for {weapon_name}: {e}")
                    print(f"Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    print(f"Failed to download image for {weapon_name} after {max_retries} attempts: {e}")
                    return None

    def parse_weapon(self, url):
        """
        Parses the Fextralife weapon page at the given URL, extracts data,
        and downloads the main weapon image.
        
        :param url: The URL of the Fextralife weapon page.
        :return: A dictionary containing the scraped weapon data.
        """
        
        try:
            r = requests.get(url, headers=self.HEADERS)
            r.raise_for_status() # Raise exception for bad status codes
        except requests.exceptions.RequestException as e:
            print(f"Error accessing URL {url}: {e}")
            return None

        soup = BeautifulSoup(r.text, "html.parser")
        data = {}
        
        # Store the wiki link
        data["wiki_link"] = url

        # -------------------------------------------------------
        # 1. Name
        # -------------------------------------------------------
        try:
            raw_title = soup.find("title").text.strip()
            data["name"] = raw_title.split("|")[0].strip()
        except:
            data["name"] = "Unknown Weapon" # Fallback

        # -------------------------------------------------------
        # 2. Description (Targeting the Blockquote/Paragraph)
        # -------------------------------------------------------
        p_tags = soup.find_all("p")
        data["description"] = None
        if len(p_tags) > 2:
            P3 = p_tags[2]
            raw_text = P3.text.strip()
            data["description"] = " ".join(raw_text.split()) # Normalize whitespace

        # -------------------------------------------------------
        # 3. Image (REVISED for download - with multiple fallback strategies)
        # -------------------------------------------------------
        data["image_path"] = None
        image_url = None
        
        # Strategy 1: Try infobox
        infobox = soup.find("div", {"id": "infobox"})
        if infobox:
            img = infobox.find("img")
            if img:
                candidate = self._extract_real_image_url(img)
                if candidate:
                    image_url = candidate

        # Strategy 2: Try to find any image with 'weapon' or the weapon name in src (preferring real attrs)
        if not image_url:
            for img in soup.find_all("img"):
                real = self._extract_real_image_url(img)
                if not real:
                    continue
                src = real.lower()
                name_token = data["name"].lower().replace(" ", "")
                # check for 'weapon' keyword or name slug in URL
                if "weapon" in src or (data["name"] and name_token in src.replace("_", "").replace("-", "")):
                    image_url = real
                    break
        
        # Strategy 3: Find largest image (likely the main weapon image)
        if not image_url:
            all_imgs = soup.find_all("img")
            if all_imgs:
                # Filter out obvious icons and small images
                def is_small_candidate(img):
                    # examine the best-guess URL from lazy attributes
                    candidate = self._extract_real_image_url(img)
                    if not candidate:
                        return True
                    lower = candidate.lower()
                    if any(small in lower for small in ["icon", "thumb", "avatar", "logo", "sprite", "badge"]):
                        return True
                    return False

                large_imgs = [img for img in all_imgs if not is_small_candidate(img)]
                if large_imgs:
                    # choose first of filtered list, but try to pick one with largest filename (heuristic)
                    chosen = large_imgs[0]
                    # prefer one with data-srcset or srcset last entry
                    for img in large_imgs:
                        if img.get("data-srcset") or img.get("srcset"):
                            chosen = img
                            break
                    candidate = self._extract_real_image_url(chosen)
                    if candidate:
                        image_url = candidate

        # If we found an image URL, download it
        if image_url and data["name"]:
            absolute_url = self._normalize_image_url(image_url)
            local_storage_path = self._download_image(absolute_url, data["name"])
            data["image_path"] = local_storage_path
        else:
            print(f"Warning: No image found for {data.get('name', 'Unknown')} (url: {url})")

        # -------------------------------------------------------
        # 4. Where to Find (Cleaned)
        # -------------------------------------------------------
        data["locations"] = []
        for h in soup.find_all(["h2", "h3"]):
            if "Where to Find" in h.text:
                ul = h.find_next("ul")
                if ul:
                    clean_locations = []
                    for li in ul.find_all("li"):
                        raw_text = li.text
                        clean_text = " ".join(raw_text.split()).strip()
                        
                        if clean_text and 'Click here' not in clean_text:
                            clean_locations.append(clean_text)
                            
                    data["locations"] = clean_locations
                break

        # -------------------------------------------------------
        # 5. Base Stats (Infobox, Main Table, UL/LI Lists)
        # -------------------------------------------------------
        data["stats"] = {}
        
        # 5a. Stats from the Infobox
        infobox = soup.find("div", {"id": "infobox"})
        if infobox:
            for tr in infobox.find_all("tr"):
                cells = tr.find_all("td")
                if len(cells) >= 2:
                    key = cells[0].text.strip()
                    val = cells[1].text.strip()
                    if key and val and key.lower() != data["name"].lower():
                        data["stats"][key] = val
                            
        # 5c. Stats from UL/LI lists (Non-numerical values allowed)
        for ul in soup.find_all("ul"):
            for li in ul.find_all("li", recursive=False): 
                strong_tag = li.find("strong")
                if strong_tag:
                    key = strong_tag.text.strip()
                    full_text = li.text.strip()
                    val_raw = full_text.replace(key, "", 1).strip()
                    val = re.sub(r"^\s*:\s*", "", val_raw).strip()
                    
                    if key and val:
                        data["stats"][key] = val

        # -------------------------------------------------------
        # 6. Vocations (Icon-based search)
        # -------------------------------------------------------
        data["vocations"] = []
        
        for li in soup.find_all("li"):
            img_tag = li.find("img", src=re.compile("icon_Vocation_", re.IGNORECASE))
            
            if img_tag:
                a_tag = li.find("a")
                if a_tag:
                    raw_text = a_tag.text
                    clean_vocation = " ".join(raw_text.split()).strip()
                    
                    if clean_vocation and clean_vocation.lower() not in ["vocations", "click here", ""]:
                        if clean_vocation not in data["vocations"]:
                            data["vocations"].append(clean_vocation)
                            
        return data

if __name__ == "__main__":
    # 1. Instantiate the weapons list scraper
    list_scraper = FextralifeWeaponsListScraper()
    
    # 2. Get all weapon links from the weapons list page
    print("Fetching weapon links from the weapons list page...")
    weapon_links = list_scraper.get_weapon_links()
    print(f"Found {len(weapon_links)} possible weapons!\n")
    
    # 3. Instantiate the weapon parser
    scraper = FextralifeWeaponScraper(download_dir="scraped_weapon_data")
    
    # 4. Parse each weapon with magic number 46 list pre-splice
    all_weapons_data = []
    for i, (weapon_name, weapon_url) in enumerate(weapon_links[46:], 1):
        print(f"[{i}/{len(weapon_links[46:])}] Parsing {weapon_name}...")
        weapon_data = scraper.parse_weapon(weapon_url)
        if weapon_data:
            # Add an ID to each weapon
            weapon_data["id"] = i
            all_weapons_data.append(weapon_data)
    
    print(f"\n--- Scrape Complete ---")
    print(f"Successfully parsed {len(all_weapons_data)} weapons")
    
    # 5. Save all weapon data to a JSON file
    output_file = "all_weapons_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_weapons_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nWeapon data saved to {output_file}")
    print(f"Total weapons in JSON: {len(all_weapons_data)}")