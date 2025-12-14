# ==========================================
# Dragon's Dogma – Armor Scraper (Fextralife)
# ==========================================

import requests
from bs4 import BeautifulSoup
import re
import os
import json
import time
from urllib.parse import urlparse


# ============================================================
# ARMOR LIST SCRAPER (TABLE-BASED, MAIN PAGE IMAGE EXTRACTION)
# ============================================================

class FextralifeArmorListScraper:
    BASE_URL = "https://dragonsdogma.wiki.fextralife.com"
    ARMOR_LIST_URL = "https://dragonsdogma.wiki.fextralife.com/Armor"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    def get_armor_links(self, url=ARMOR_LIST_URL):
        """
        Returns a list of tuples:
        (armor_name, armor_page_url, main_page_image_url)
        """

        try:
            r = requests.get(url, headers=self.HEADERS)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error accessing {url}: {e}")
            return []

        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        seen = set()

        for tbody in soup.find_all("tbody"):
            for tr in tbody.find_all("tr", recursive=False):
                a = tr.find("a", class_="wiki_link", href=True)
                if not a:
                    continue

                name = a.text.strip()
                href = a["href"].strip()
                if not name or not href:
                    continue

                # -------- image from MAIN PAGE --------
                img = a.find("img")
                image_url = None
                if img:
                    image_url = (
                        img.get("data-src")
                        or img.get("data-original")
                        or img.get("src")
                    )
                    if image_url and image_url.startswith("/"):
                        image_url = self.BASE_URL + image_url

                page_url = self.BASE_URL + href if href.startswith("/") else href

                if page_url in seen:
                    continue

                seen.add(page_url)
                results.append((name, page_url, image_url))

        return results


# ============================================================
# SHARED ITEM PARSER (WEAPONS / ARMOR)
# ============================================================

class FextralifeWeaponScraper:
    BASE_URL = "https://dragonsdogma.wiki.fextralife.com"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    def __init__(self, download_dir="item_images"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    # ---------------------------
    # Image helpers
    # ---------------------------

    def _extract_real_image_url(self, img):
        if not img:
            return None

        for key in ("data-srcset", "srcset"):
            val = img.get(key)
            if val:
                parts = [p.strip() for p in val.split(",") if p.strip()]
                if parts:
                    return parts[-1].split()[0]

        for key in ("data-src", "data-original", "data-image", "data-url"):
            val = img.get(key)
            if val:
                return val

        return img.get("src")

    def _normalize_image_url(self, url):
        if not url:
            return None
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return self.BASE_URL + url
        return self.BASE_URL + "/" + url

    def _download_image(self, image_url, item_name):
        parsed = urlparse(image_url)
        _, ext = os.path.splitext(parsed.path)

        safe_name = re.sub(r"[^\w\-_.]", "", item_name.replace(" ", "_"))
        filename = f"{safe_name}{ext or '.png'}"
        path = os.path.join(self.download_dir, filename)

        if os.path.exists(path):
            return path

        for attempt in range(3):
            try:
                r = requests.get(image_url, stream=True, headers=self.HEADERS, timeout=10)
                r.raise_for_status()
                with open(path, "wb") as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                return path
            except Exception as e:
                time.sleep(2 ** attempt)

        return None

    # ============================================================
    # PARSE ITEM PAGE (UNCHANGED CORE LOGIC)
    # ============================================================

    def parse_weapon(self, url, main_page_image_url=None):
        try:
            r = requests.get(url, headers=self.HEADERS)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error accessing {url}: {e}")
            return None

        soup = BeautifulSoup(r.text, "html.parser")
        data = {"wiki_link": url}

        # -------- Name --------
        try:
            data["name"] = soup.find("title").text.split("|")[0].strip()
        except:
            data["name"] = "Unknown Item"

        # -------------------------------------------------------
        # Description (handles <p>, <em>, and blockquote variants)
        # -------------------------------------------------------
        data["description"] = None

        # 1) Original behavior: 3rd paragraph
        p_tags = soup.find_all("p")
        if len(p_tags) > 2:
            text = p_tags[2].get_text(strip=True)
            if text:
                data["description"] = text

        # 2) Fallback: emphasized description (<em>)
        if not data["description"]:
            # Prefer <em> near the top of the page
            for em in soup.find_all("em"):
                text = em.get_text(strip=True)
                # Heuristic: real descriptions are sentence-like
                if (
                    text
                    and len(text) > 10
                    and text.count(" ") > 2
                ):
                    # Strip surrounding quotes
                    data["description"] = text.strip('“”"')
                    break

        # 3) Normalize whitespace
        if data["description"]:
            data["description"] = " ".join(data["description"].split())

        # -------- Image (MAIN PAGE FIRST) --------
        data["image_path"] = None

        if main_page_image_url:
            absolute = self._normalize_image_url(main_page_image_url)
            data["image_path"] = self._download_image(absolute, data["name"])

        # -------- Fallback to subpage --------
        if not data["image_path"]:
            infobox = soup.find("div", id="infobox")
            if infobox:
                img = infobox.find("img")
                if img:
                    candidate = self._extract_real_image_url(img)
                    if candidate:
                        absolute = self._normalize_image_url(candidate)
                        data["image_path"] = self._download_image(absolute, data["name"])

      # -------- Locations --------
        data["locations"] = []

        for h in soup.find_all(["h2", "h3"]):
            header_text = h.get_text(strip=True).lower()

            if "where to find" in header_text or "location" in header_text:
                ul = h.find_next("ul")
                if ul:
                    data["locations"] = [
                        " ".join(li.get_text(strip=True).split())
                        for li in ul.find_all("li")
                        if "click here" not in li.get_text(strip=True).lower()
                    ]
                break

        # -------- Stats --------
        data["stats"] = {}
        infobox = soup.find("div", id="infobox")
        if infobox:
            for tr in infobox.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) >= 2:
                    k = tds[0].text.strip()
                    v = tds[1].text.strip()
                    if k and v:
                        data["stats"][k] = v

        # -------- Vocations --------
        data["vocations"] = []

        for img in soup.find_all("img", src=re.compile(r"icon_Vocation_", re.I)):
            vocation = None

            # 1) Preferred: anchor text
            parent_a = img.find_parent("a")
            if parent_a:
                text = parent_a.get_text(strip=True)
                if text:
                    vocation = text

            # 2) Fallback: filename / alt / title (supports hyphens)
            if not vocation:
                source = img.get("alt") or img.get("title") or img.get("src")
                if source:
                    match = re.search(
                        r"icon[_\- ]?Vocation[_\- ]?([A-Za-z\- ]+)",
                        source,
                        re.I
                    )
                    if match:
                        vocation = match.group(1)

            if vocation:
                # Normalize formatting
                vocation = vocation.replace("_", " ").replace("-", " ").strip()
                vocation = " ".join(word.capitalize() for word in vocation.split())

                if vocation not in data["vocations"]:
                    data["vocations"].append(vocation)


        return data


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    list_scraper = FextralifeArmorListScraper()
    print("Fetching armor links...")
    armor_links = list_scraper.get_armor_links()
    print(f"Found {len(armor_links)} armor pages\n")

    scraper = FextralifeWeaponScraper(download_dir="scraped_armor_images")
    all_armor = []

    for i, (name, url, img_url) in enumerate(armor_links, 1):
        print(f"[{i}/{len(armor_links)}] Parsing {name}")
        data = scraper.parse_weapon(url, main_page_image_url=img_url)
        if data:
            data["id"] = i
            all_armor.append(data)

    with open("all_armor_data.json", "w", encoding="utf-8") as f:
        json.dump(all_armor, f, indent=2, ensure_ascii=False)

    print("\n✔ Armor scrape complete")
    print(f"✔ Saved {len(all_armor)} armor items")
