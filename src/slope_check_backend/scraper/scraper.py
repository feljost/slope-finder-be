import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime


class SkiResortScraper:
    """Simple HTTP scraper for ski resort information"""

    def __init__(self):
        """Initialize the scraper"""
        self.current_data = None
        self.session = requests.Session()
        # Set a user agent to avoid being blocked
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def scrape_ski_resort(self, url: str):
        """
        Scrape ski resort information from skiresort.info

        Args:
            url: The URL of the ski resort snow report page

        Returns:
            dict: Dictionary containing pistes, lifts, and snow information
        """
        print(f"Fetching {url}...")

        response = self.session.get(url)
        response.raise_for_status()

        print(f"Page fetched successfully. Status code: {response.status_code}")

        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract data
        data = self.extract_resort_info(soup)
        self.current_data = data

        return data

    def extract_resort_info(self, soup):
        """
        Extract pistes, lifts, and snow information from the HTML

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            dict: Extracted information
        """
        data = {
            'pistes_km': None,
            'lifts': None,
            'snow_cm': None,
            'updated_on': None,
            'days_old': None
        }

        try:
            # Find the overview-resort-infos section
            resort_info = soup.find('div', class_='overview-resort-infos')

            if resort_info:
                # Extract all info-item-con divs
                info_items = resort_info.find_all('div', class_='info-item-con')

                for item in info_items:
                    info_text_div = item.find('div', class_='info-text')

                    if info_text_div:
                        text = info_text_div.get_text(strip=True)

                        # Check if this is the slopes/pistes info (contains icon-uE004-skirun or has "km" in text)
                        if item.find('i', class_=re.compile('icon.*skirun')) or 'km' in text:
                            # Extract pistes km (format: "32.3/41.2 km")
                            data['pistes_km'] = text
                            print(f"Found pistes: {text}")

                        # Check if this is the lift info (contains lift-icon)
                        elif item.find('i', class_=re.compile('lift-icon')):
                            # Extract lifts (format: "10/13")
                            data['lifts'] = text
                            print(f"Found lifts: {text}")

                        # Check if this is the snow info (contains fa-snowflake-o)
                        elif item.find('i', class_='fa fa-snowflake-o'):
                            # Extract snow depth (format: "59 cm")
                            data['snow_cm'] = text
                            print(f"Found snow: {text}")

        except Exception as e:
            print(f"Error extracting resort info: {e}")

        # Extract update date
        try:
            update_wrapper = soup.find('div', class_='update-wrapper')
            if update_wrapper:
                # Try to find the hidden div with date attribute first
                date_div = update_wrapper.find('div', id='snowreport-update-date')
                if date_div and date_div.get('date'):
                    date_str = date_div.get('date')
                    print(f"Found update date (from attribute): {date_str}")
                else:
                    # Fall back to finding the bold div with the date text
                    bold_divs = update_wrapper.find_all('div', class_='bold')
                    for div in bold_divs:
                        text = div.get_text(strip=True)
                        # Match date format like "20 Dec 2025"
                        if re.match(r'\d{1,2}\s+\w+\s+\d{4}', text):
                            date_str = text
                            print(f"Found update date (from text): {date_str}")
                            break

                if date_str:
                    data['updated_on'] = date_str

                    # Calculate days old
                    days_old = self.calculate_days_old(date_str)
                    data['days_old'] = days_old
                    print(f"Data is {days_old} day(s) old")

        except Exception as e:
            print(f"Error extracting update date: {e}")

        return data

    def calculate_days_old(self, date_str: str) -> int:
        """
        Calculate how many days old the data is

        Args:
            date_str: Date string in format "20.12.2025" or "20 Dec 2025"

        Returns:
            int: Number of days old
        """
        try:
            # Try parsing "20.12.2025" format first
            if '.' in date_str:
                update_date = datetime.strptime(date_str, '%d.%m.%Y')
            else:
                # Parse "20 Dec 2025" format
                update_date = datetime.strptime(date_str, '%d %b %Y')

            today = datetime.now()
            days_difference = (today - update_date).days

            return days_difference
        except Exception as e:
            print(f"Error calculating days old: {e}")
            return None


def main():
    from slope_check_backend.constants import ski_resorts
    """Main function to run the scraper"""
    scraper = SkiResortScraper()
    for resort in ski_resorts:
        url = resort["snowreport_url"]

        try:
            print("=" * 50)
            print(f"Scraping {resort['name']} ski resort...")
            print("=" * 50)

            data = scraper.scrape_ski_resort(url)

            print("\n" + "=" * 50)
            print("EXTRACTED DATA:")
            print("=" * 50)
            print(f"Pistes: {data['pistes_km']}")
            print(f"Lifts: {data['lifts']}")
            print(f"Snow: {data['snow_cm']}")
            print(f"Updated on: {data['updated_on']}")
            print(f"Days old: {data['days_old']}")
            print("=" * 50)

        except Exception as e:
            print(f"Error occurred: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
