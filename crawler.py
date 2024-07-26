from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import Leagues, Matches
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pytz
from datetime import datetime, timedelta
import sys
import chromedriver_autoinstaller
from apscheduler.schedulers.background import BackgroundScheduler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

db: SQLAlchemy = None
app: Flask = None

def insert_default_leagues():
    default_leagues = [
        {"name": "Basketball", "url": "https://get.rnbastreams.com"},
        {"name": "Soccer", "url": "https://reddit15.sportshub.stream"},
        {"name": "Volleyball", "url": "https://volleyball3.sportshub.stream/"},
    ]

    for league_info in default_leagues:
        existing_league = Leagues.query.filter_by(name=league_info['name']).first()
        if not existing_league:
            new_league = Leagues(name=league_info['name'], url=league_info['url'])
            db.session.add(new_league)
    db.session.commit()

def setup_driver():
    chrome_driver_path = chromedriver_autoinstaller.install()
    chrome_options = Options()
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--proxy-bypass-list=*")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-browser-side-navigation")

    service = Service(executable_path=chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def scheduleNbaCrawler(driver, league):
    print("BASKETBALL CRAWLER", file=sys.stderr)

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
            matchTime_no_tz = matchTime.replace(" EST", "")
            time_str = matchTime_no_tz + " " + dayH2
            matchTimeConverted = convert_to_utc_psql_format(time_str)
            matchURL = li.find_element(By.TAG_NAME, "a").get_attribute("href")

            isLive = bool(li.find_elements(By.CLASS_NAME, 'live-label'))

            existing_match = Matches.query.filter_by(
                team1name=team1Name,
                team2name=team2Name,
                time=matchTime,
                link=matchURL,
                date=time_str,
                league_id=league.id  # Use dynamic league ID
            ).first()

            if not existing_match:
                new_match = Matches(
                    team1name=team1Name,
                    team2name=team2Name,
                    time=matchTime,
                    link=matchURL,
                    date=time_str,
                    league_id=league.id,  # Use dynamic league ID
                    datetime=matchTimeConverted,
                    isLive=isLive
                )
                db.session.add(new_match)
            elif isLive and not existing_match.isLive:
                existing_match.isLive = True  # Update the match to live

        db.session.commit()
    except Exception as e:
        print(f"An error occurred during web scraping for {league.name}:", e, file=sys.stderr)
        db.session.rollback()
    finally:
        driver.quit()



def scheduleCrawler(driver, league):
    print("SOCCER CRAWLER HERE", file=sys.stderr)

    print(league.url, file=sys.stderr)
    driver.get(league.url)
    wait = WebDriverWait(driver, 10)

    try:
        contentDiv = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'list-events')))
        print("CONTENT DIV", contentDiv, file=sys.stderr)

        day = contentDiv.find_element(By.TAG_NAME, 'h4').text

        fixturesLis = contentDiv.find_elements(By.CLASS_NAME, 'wrap-events-item')
        print("LIST DIV", fixturesLis, file=sys.stderr)

        for li in fixturesLis:
            team1Name = li.find_element(By.CLASS_NAME, 'mr-5').text
            print("Team names", team1Name, file=sys.stderr)

            matchURL = li.find_element(By.TAG_NAME, "a").get_attribute("href")
            print("MATCH URL", matchURL, file=sys.stderr)

            matchDate = li.find_element(By.CLASS_NAME, 'event-desc')
            print("MATCH DATE", matchDate.text, file=sys.stderr)

            matchDateConverted = convert_buff_to_utc_psql_format(matchDate.text)
            print("MATCH DATE CONV", matchDateConverted, file=sys.stderr)

            isLive = bool(li.find_elements(By.CLASS_NAME, 'live-label'))

            existing_match = Matches.query.filter_by(
                team1name=team1Name,
                link=matchURL,
                date=day,
                datetime=matchDateConverted,
                league_id=league.id  # Use dynamic league ID
            ).first()
            print("EXISTING MATCH", existing_match, file=sys.stderr)
            if not existing_match:
                new_match = Matches(
                    team1name=team1Name,
                    team2name="",
                    time="",
                    link=matchURL,
                    date=day,
                    datetime=matchDateConverted,
                    league_id=league.id,  # Use dynamic league ID
                    isLive=isLive
                )
                print("NEW MATCH TO ADD", new_match, file=sys.stderr)
                db.session.add(new_match)
                print("SINGLE SOCCER MATCH +", file=sys.stderr)
            elif isLive and not existing_match.isLive:
                existing_match.isLive = True  # Update the match to live

        db.session.commit()
        print("SOCCER MATCHES ADDED", file=sys.stderr)
    except Exception as e:
        print(f"An error occurred during web scraping for {league.name}:", e, file=sys.stderr)
        db.session.rollback()
    finally:
        driver.quit()



def convert_buff_to_utc_psql_format(date_str):
    print("date1",date_str, file=sys.stderr)

    # Extract the date and time text after the delimiter "/"
    _, date_time_text = date_str.split("/", 1)
   
    date_time_text = date_time_text.strip()  # Remove any leading/trailing whitespace
    print("date2",date_time_text, file=sys.stderr)
    # Extract the full date and time string components
    date_part, time_part = date_time_text.split(" at ")
    date_part = date_part.strip()
    time_part = time_part.strip()
    
    # Construct the full datetime string
    current_year = datetime.now().year
    full_date_str = f"{time_part} {date_part} {current_year}"
    
    # Define the format string to match the constructed date string
    date_format = "%H:%M %d %B %Y"
    
    # Parse the datetime string
    naive_datetime = datetime.strptime(full_date_str, date_format)
    
    # Localize to Eastern Time Zone
    est = pytz.timezone('US/Eastern')
    aware_datetime = est.localize(naive_datetime)
    
    # Convert to UTC
    utc_datetime = aware_datetime.astimezone(pytz.utc)
    
    # Format for PostgreSQL
    psql_compatible_string = utc_datetime.strftime('%Y-%m-%dT%H:%M:%S%z')
    
    return psql_compatible_string

def convert_to_utc_psql_format(date_str):
    date_format = "%H:%M %a %d %b %Y"
    naive_datetime = datetime.strptime(date_str, date_format)
    est = pytz.timezone('US/Eastern')
    aware_datetime = est.localize(naive_datetime)
    utc_datetime = aware_datetime.astimezone(pytz.utc)
    psql_compatible_string = utc_datetime.strftime('%Y-%m-%dT%H:%M:%S%z')

    return psql_compatible_string

def remove_expired_matches():
    with app.app_context():
        try:
            # Calculate the expiration time for matches (e.g., matches older than 6 hours)
            expiration_time = datetime.utcnow() - timedelta(hours=6)

            # Query the database for matches that have exceeded the expiration time
            expired_matches = db.session.query(Matches).filter(Matches.datetime < expiration_time).all()

            if expired_matches:
                # Iterate over the expired matches
                for match in expired_matches:
                    # Query and delete the stream sources associated with the expired match
                    db.session.query(Matches).filter(Matches.match_id == match.id).delete()

                # Commit the changes to the database
                db.session.commit()
                logger.info(f"Removed stream sources associated with {len(expired_matches)} expired matches.")
            else:
                logger.info("No expired matches found.")

        except Exception as e:
            # Rollback in case of any error
            db.session.rollback()
            logger.error(f"Error occurred while removing expired stream sources: {str(e)}")

def main(appArg: Flask, dbArg: SQLAlchemy):
    global db, app
    app = appArg
    db = dbArg

    with app.app_context():
        insert_default_leagues()

        try:
            # Initialize the Chrome webdriver using the updated path
            nbaleague = Leagues.query.filter_by(name="Basketball").first()
            if nbaleague:
                driver = setup_driver()
                scheduleNbaCrawler(driver, nbaleague)  # Pass the basketball league object
                print("NBA MATCHES ADDED", file=sys.stderr)

            # Get all leagues except the basketball league
            other_leagues = Leagues.query.filter(Leagues.name != "Basketball").all()

            # Schedule crawlers for the other leagues
            for league in other_leagues:
                driver = setup_driver()
                scheduleCrawler(driver, league)
                print(f"{league.name} MATCHES ADDED", file=sys.stderr)

        except Exception as e:
            print("Failed to connect to database or run crawler:", e, file=sys.stderr)
        
        finally:
            db.session.close()

if __name__ == '__main__':
    scheduler.add_job(main, 'interval', hours=6, args=[db, app])
    scheduler.add_job(remove_expired_matches, 'interval', hours=6) 
    scheduler.start()
