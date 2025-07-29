import requests
from bs4 import BeautifulSoup
import json
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv
import os

load_dotenv()

BASE_URL = os.environ['BASE_URL']
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def setup_session():
    """Configure session with retry mechanism"""
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    )
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.headers.update(HEADERS)
    return session

def parse_player_row(row):
    tds = row.find_all("td", recursive=False)
    if not tds or len(tds) < 9:
        return None

    try:
        # Player info
        img_tag = tds[0].find("img", class_="bilderrahmen-fixed")
        player_img = img_tag["src"] if img_tag and img_tag.has_attr("src") else ""
        
        player_link = tds[0].find("a", href=lambda x: x and "/profil/spieler/" in x)
        player_name = player_link.text.strip() if player_link else ""
        
        position = tds[0].find("td", string=lambda text: text and text.strip() in ["Goalkeeper", "Defender", "Midfielder", "Forward"])
        position = position.text.strip() if position else ""

        # Age and nationality
        age = tds[1].text.strip()
        
        nationality_img = tds[2].find("img", class_="flaggenrahmen")
        nationality_flag = nationality_img["src"] if nationality_img else ""
        nationality = nationality_img["title"] if nationality_img else ""

        # Clubs info
        def parse_club(td):
            club_link = td.find("a", href=lambda x: x and "/startseite/verein/" in x)
            club_name = club_link["title"] if club_link else "Without Club"
            
            league_link = td.find("a", href=lambda x: x and "/wettbewerb/" in x)
            league = league_link.text.strip() if league_link else ""
            
            return club_name, league

        current_club, current_league = parse_club(tds[3])
        interested_club, interested_league = parse_club(tds[4])

        # Contract and value
        contract_expires = tds[5].text.strip()
        market_value = tds[6].text.strip()
        
        # Probability (cleaning the text)
        probability = tds[8].get_text(" ", strip=True)
        probability = "".join(c for c in probability if c.isdigit() or c == '%')

        return {
            "player_name": player_name,
            "position": position,
            "age": age,
            "nationality": nationality,
            "nationality_flag": nationality_flag,
            "player_image": player_img if not player_img.startswith("data:image") else "",
            "current_club": current_club,
            "current_club_league": current_league,
            "interested_club": interested_club,
            "interested_club_league": interested_league,
            "contract_expires": contract_expires,
            "market_value": market_value,
            "probability": probability
        }
    except Exception as e:
        print(f"Error parsing row: {e}")
        return None

def scrape_all_pages():
    all_players = []
    page = 1
    total_pages = 1
    session = setup_session()

    while page <= total_pages:
        print(f"Processing page {page}/{total_pages}...")
        
        try:
            params = {"page": page}
            response = session.get(BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Update total pages from pagination
            pagination = soup.find("ul", class_="tm-pagination")
            if pagination:
                page_items = pagination.find_all("li", class_="tm-pagination__list-item")
                page_numbers = [int(item.text) for item in page_items if item.text.isdigit()]
                if page_numbers:
                    total_pages = max(page_numbers)
            
            # Parse table
            table = soup.find("table", class_="items")
            if not table:
                break
                
            tbody = table.find("tbody")
            rows = tbody.find_all("tr", recursive=False) if tbody else []
            
            for row in rows:
                player_data = parse_player_row(row)
                if player_data:
                    all_players.append(player_data)
            
            # Check if we should continue
            next_page = soup.find("li", class_="tm-pagination__list-item--icon-next-page")
            if not next_page or "tm-pagination__list-item--disabled" in next_page.get("class", []):
                break
                
            page += 1
            time.sleep(2 + abs(1 - time.time() % 1))  # Random delay 2-3 seconds
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break

    return all_players

if __name__ == "__main__":
    print("Starting scraper...")
    start_time = time.time()
    
    try:
        players = scrape_all_pages()
        print(f"Successfully collected {len(players)} players")
        
        with open("latest_rumours_all_pages_data.json", "w", encoding="utf-8") as f:
            json.dump(players, f, ensure_ascii=False, indent=2)
            
        print(f"Data saved to latest_rumours_first_page.json")
        print(f"Execution time: {time.time() - start_time:.2f} seconds")
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"Critical error: {e}")