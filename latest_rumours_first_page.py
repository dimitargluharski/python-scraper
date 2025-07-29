import requests
from bs4 import BeautifulSoup
import json
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def parse_player_row(row):
    tds = row.find_all("td", recursive=False)
    if not tds or len(tds) < 9:
        return None

    # Player info
    img_tag = tds[0].find("img")
    player_img = img_tag["src"] if img_tag else ""
    player_name = tds[0].find("a").text.strip() if tds[0].find("a") else ""
    position = tds[0].find_all("td")[-1].text.strip() if tds[0].find_all("td") else ""

    age = tds[1].text.strip()

    nationality_img = tds[2].find("img")
    nationality_flag = nationality_img["src"] if nationality_img else ""
    nationality = nationality_img["title"] if nationality_img else ""

    # Current club
    current_club_td = tds[3]
    current_club_name = current_club_td.find("a", title=True)["title"] if current_club_td.find("a", title=True) else "Without Club"
    current_club_league = current_club_td.find_all("td")[-1].text.strip() if current_club_td.find_all("td") else ""

    # Interested club
    interested_club_td = tds[4]
    interested_club_name = interested_club_td.find("a", title=True)["title"] if interested_club_td.find("a", title=True) else ""
    interested_club_league = interested_club_td.find_all("td")[-1].text.strip() if interested_club_td.find_all("td") else ""

    contract_expires = tds[5].text.strip()
    market_value = tds[6].text.strip()

    probability_text = tds[8].get_text(strip=True)
    probability = probability_text if "%" in probability_text else ""

    return {
        "player_name": player_name,
        "position": position,
        "age": age,
        "nationality": nationality,
        "nationality_flag": nationality_flag,
        "player_image": player_img,
        "current_club": current_club_name,
        "current_club_league": current_club_league,
        "interested_club": interested_club_name,
        "interested_club_league": interested_club_league,
        "contract_expires": contract_expires,
        "market_value": market_value,
        "probability": probability
    }

def scrape_all_pages():
    all_players = []
    page = 1

    while True:
        print(f"Scraping page {page}...")
        params = {"page": page, "plus": "1"}
        response = requests.get(BASE_URL, headers=HEADERS, params=params)
        soup = BeautifulSoup(response.content, "html.parser")

        table = soup.find("table", class_="items")
        if not table:
            break

        tbody = table.find("tbody")
        rows = tbody.find_all("tr", recursive=False)

        if not rows:
            break

        for row in rows:
            player_data = parse_player_row(row)
            if player_data:
                all_players.append(player_data)

        # Pagination check
        pager = soup.select_one(".pager .tm-pagination__list")
        if pager and "last" in pager.text.lower() and f">{page}<" in pager.text:
            page += 1
            time.sleep(1)  # avoid rate-limiting
        else:
            break

    return all_players

if __name__ == "__main__":
    players = scrape_all_pages()
    with open("latest_rumours_first_page_data.json", "w", encoding="utf-8") as f:
        json.dump(players, f, ensure_ascii=False, indent=2)
    print(f"Done. Collected {len(players)} players.")
