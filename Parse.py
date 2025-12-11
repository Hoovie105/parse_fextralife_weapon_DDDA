import requests
from bs4 import BeautifulSoup
import re
import os
from urllib.parse import urlparse, urlunparse

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

    def _download_image(self, image_url, weapon_name):
        """
        Downloads an image from a URL and saves it to the local directory.
        (Internal method denoted by leading underscore)
        """
        
        # 1. Create a safe, unique filename
        # Get the file extension from the URL path
        parsed_url = urlparse(image_url)
        _, file_extension = os.path.splitext(parsed_url.path)

        # Clean the weapon name to use it as a base filename
        safe_name = re.sub(r'[^\w\-_\.]', '', weapon_name.replace(' ', '_'))
        
        filename = f"{safe_name}{file_extension}"
        local_path = os.path.join(self.download_dir, filename)

        try:
            # Use requests to download the image file
            print(f"Downloading {weapon_name} from {image_url}...")
            img_data = requests.get(image_url, stream=True, headers=self.HEADERS)
            img_data.raise_for_status() 

            with open(local_path, 'wb') as handler:
                # Write the content in chunks
                for chunk in img_data.iter_content(chunk_size=8192):
                    handler.write(chunk)

            # Return the path relative to the script's execution
            return local_path

        except requests.exceptions.RequestException as e:
            print(f"Error downloading image for {weapon_name}: {e}")
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
        # 3. Image (REVISED for download)
        # -------------------------------------------------------
        data["image_path"] = None
        infobox = soup.find("div", {"id": "infobox"})
        if infobox:
            img = infobox.find("img")
            if img and img.get("src") and data["name"]:
                relative_url = img.get("src")
                absolute_url = self.BASE_URL + relative_url
                
                # Use the internal download method
                local_storage_path = self._download_image(absolute_url, data["name"])
                data["image_path"] = local_storage_path

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
        
        for a_tag in soup.find_all("a"):
            img_tag = a_tag.find("img", src=re.compile("icon_Vocation_", re.IGNORECASE))
            
            if img_tag:
                raw_text = a_tag.text
                clean_vocation = " ".join(raw_text.split()).strip()
                
                if clean_vocation and clean_vocation.lower() not in ["vocations", "click here", ""]:
                    if clean_vocation not in data["vocations"]:
                        data["vocations"].append(clean_vocation)
                            
        return data

if __name__ == "__main__":
    # 1. Instantiate the class. This automatically creates the 'weapon_images' folder.
    scraper = FextralifeWeaponScraper(download_dir="scraped_weapon_data")

    # 2. Define the URL to scrape
    url_meniscus = "https://dragonsdogma.wiki.fextralife.com/Aneled+Meniscus"
    
    # 3. Call the parse_weapon method on the instance
    weapon_meniscus_data = scraper.parse_weapon(url_meniscus)
    
    # 4. Print the results
    print(f"\n--- Aneled Meniscus Scrape Complete ---")
    print(weapon_meniscus_data)