from models import Leagues
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pytz
from datetime import datetime
from app import app, db
import pytz
import sys
from webdriver_manager.chrome import ChromeDriverManager
import chromedriver_autoinstaller

chrome_driver_path = "/root/.wdm/drivers/chromedriver/linux64/114.0.5735.90/chromedriver"  # Update this with the correct path to your chromedriver

def insert_default_leagues():
    default_leagues = [
        {"name": "NBA", "url": "https://get.rnbastreams.com"},
    ]

    for league_info in default_leagues:
        existing_league = Leagues.query.filter_by(name=league_info['name']).first()
        if not existing_league:
            new_league = Leagues(name=league_info['name'], url=league_info['url'])
            db.session.add(new_league)
    db.session.commit()
    
def scheduleCrawler(driver, league):
    print("scheduleCrawler", file=sys.stderr)
    driver.get(league.url)
    wait = WebDriverWait(driver, 10)
    
    try:
        contentDiv = wait.until(EC.presence_of_element_located((By.ID, 'content')))
        
        # Crawl day
        header = contentDiv.find_element(By.CSS_SELECTOR, ".header")
        dayH2 = header.find_element(By.TAG_NAME, 'h2').text
        # Crawl match
        fixtures = contentDiv.find_element(By.ID, "fixtures")
        fixturesUl = fixtures.find_element(By.CSS_SELECTOR, ".competitions")
        fixturesLis = fixturesUl.find_elements(By.TAG_NAME, 'li')
        
        for li in fixturesLis:
            team1Name = li.find_element(By.CSS_SELECTOR, '.competition-cell-side1').text
            team2Name = li.find_element(By.CSS_SELECTOR, '.competition-cell-side2').text
            matchTimeSpan = li.find_element(By.CSS_SELECTOR, '.competition-cell-score')
            matchTime = matchTimeSpan.find_element(By.TAG_NAME, "span").text
            time_str = matchTime + " " + dayH2
            matchTimeConverted = convert_to_utc_psql_format(time_str)
            matchURL = li.find_element(By.TAG_NAME, "a").get_attribute("href")
            print(team1Name, team2Name, time_str, matchURL, matchTimeConverted, fike=sys.stderr)
        
    except Exception as e:
        print(f"An error occurred during web scraping for {league.name}:", e, file=sys.stderr)
        db.session.rollback()
    finally:
        driver.quit()
        
def convert_to_utc_psql_format(date_str):
    # Define the date format without the timezone
    date_format = "%H:%M %a %d %b %Y"
    
    # Parse the date string into a datetime object without the timezone
    naive_datetime = datetime.strptime(date_str[:-8], date_format)

    # Specify the timezone (EST in this case)
    est = pytz.timezone('US/Eastern')

    # Make the datetime object timezone aware
    aware_datetime = est.localize(naive_datetime)

    # Convert the datetime object to UTC
    utc_datetime = aware_datetime.astimezone(pytz.utc)

    # Format the datetime object as a string suitable for PostgreSQL
    psql_compatible_string = utc_datetime.strftime('%Y-%m-%dT%H:%M:%S%z')

    return psql_compatible_string

def main():
    with app.app_context():
        insert_default_leagues()

        # Find the path to the installed chromedriver
        # chrome_driver_path = ChromeDriverManager().install()
        chrome_driver_path = chromedriver_autoinstaller.install()

        print(chrome_driver_path, file=sys.stderr)

        try:
            # Initialize the Chrome webdriver using the updated path
            driver = webdriver.Chrome(chrome_driver_path)
            league = Leagues.query.filter_by(name="NBA").first()
            if league:
                scheduleCrawler(driver, league)  # Pass the league object
            else:
                print("League not found in the database.", file=sys.stderr)
        except Exception as e:
            print("Failed to connect to database or run crawler:", e, file=sys.stderr)
        finally:
            # Close the session to prevent any dangling transactions
            db.session.close()
            print("insterted default leagues", file=sys.stderr)

if __name__ == '__main__':
    main()