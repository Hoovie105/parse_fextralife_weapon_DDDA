import requests
from bs4 import BeautifulSoup
import re
import os

def parse_fextralife_weapon(url):
    r = requests.get(url, 
                     headers = {
                         "User-Agent": (
                             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/120.0.0.0 Safari/537.36"
                         ),
                         "Accept-Language": "en-US,en;q=0.9",
    })

    soup = BeautifulSoup(r.text, "html.parser")

    data = {}

    # -------------------------------------------------------
    # 1. Name
    # -------------------------------------------------------
    raw_title = soup.find("title").text.strip()
    data["name"] = raw_title.split("|")[0].strip()

   # -------------------------------------------------------
    # 2. Description (Targeting the second <p> tag)
    # -------------------------------------------------------
    
    # Use find_all to get a list of all <p> tags
    p_tags = soup.find_all("p")

    second_p_tag = p_tags[2]

    # Extract and clean the text
    raw_text = second_p_tag.text.strip()
    description = " ".join(raw_text.split()) # Normalize whitespace

    data["description"] = description

    # -------------------------------------------------------
    # 3. Image
    # -------------------------------------------------------
    data["image"] = None
    infobox = soup.find("div", {"id": "infobox"})
    if infobox:
        img = infobox.find("img")
        if img:
            data["image"] = img.get("src")

    # -------------------------------------------------------
    # 4. Where to Find (Revised for clean text)
    # -------------------------------------------------------
    data["locations"] = []
    for h in soup.find_all(["h2", "h3"]):
        if "Where to Find" in h.text:
            ul = h.find_next("ul")
            if ul:
                # Apply normalization: replace \xa0 and newlines with spaces, then normalize to a single space
                clean_locations = []
                for li in ul.find_all("li"):
                    raw_text = li.text
                    
                    # Normalize whitespace: replaces all types of whitespace (including \xa0 and \n) 
                    # with a single space, then strips leading/trailing space.
                    clean_text = " ".join(raw_text.split()).strip()
                    
                    if clean_text and 'Click here' not in clean_text:
                        clean_locations.append(clean_text)
                        
                data["locations"] = clean_locations
            break

    # -------------------------------------------------------
    # 5. Base Stats (Handles Infobox, Main Table, and UL/LI Lists)
    # -------------------------------------------------------
    data["stats"] = {}
    
    # 5a. Stats from the Infobox (Weight, Value, Weapon Type, etc.)
    infobox = soup.find("div", {"id": "infobox"})
    if infobox:
        for tr in infobox.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) >= 2:
                key = cells[0].text.strip()
                val = cells[1].text.strip()
                if key and val and key.lower() != data["name"].lower():
                    data["stats"][key] = val
                        
    # 5c. Stats from UL/LI lists
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
    # 6. Vocations (FINAL, MOST ROBUST REVISION)
    # -------------------------------------------------------
    data["vocations"] = []
    
    # Find all anchor tags (<a>) across the entire document
    for a_tag in soup.find_all("a"):
        
        # Check if the anchor tag contains an <img> tag that looks like a Vocation icon
        img_tag = a_tag.find("img", src=re.compile("icon_Vocation_", re.IGNORECASE))
        
        if img_tag:
            # The clean vocation name is the text of the anchor tag, cleaned up.
            raw_text = a_tag.text
            clean_vocation = " ".join(raw_text.split()).strip()
            
            # Ensure we don't accidentally grab empty text or boilerplate
            if clean_vocation and clean_vocation.lower() not in ["vocations", "click here", ""]:
                if clean_vocation not in data["vocations"]:
                    data["vocations"].append(clean_vocation)
                        
    return data


# Example usage:
url_meniscus = "https://dragonsdogma.wiki.fextralife.com/Aneled+Meniscus"
weapon_meniscus = parse_fextralife_weapon(url_meniscus)
print(f"--- Aneled Meniscus Test (Vocations Should Be Correct) ---")
print(weapon_meniscus)