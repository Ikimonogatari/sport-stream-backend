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
from datetime import datetime
import sys

import chromedriver_autoinstaller
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()

db: SQLAlchemy = None
app: Flask = None
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

            existing_match = Matches.query.filter_by(team1name=team1Name, team2name=team2Name, time=matchTime, link=matchURL, date=time_str, league_id=1).first()
            if not existing_match:
                matchTimeConverted = convert_to_utc_psql_format(time_str)
                new_match = Matches(team1name=team1Name, team2name=team2Name, time=matchTime, link=matchURL, date=time_str, league_id=1, datetime=matchTimeConverted)
                db.session.add(new_match)
              
        db.session.commit()
    except Exception as e:
        print(f"An error occurred during web scraping for {league.name}:", e, file=sys.stderr)
        db.session.rollback()
    finally:
        driver.quit()
        
def convert_to_utc_psql_format(date_str):

    date_format = "%H:%M %a %d %b %Y"
    naive_datetime = datetime.strptime(date_str, date_format)
    est = pytz.timezone('US/Eastern')
    aware_datetime = est.localize(naive_datetime)
    utc_datetime = aware_datetime.astimezone(pytz.utc)
    psql_compatible_string = utc_datetime.strftime('%Y-%m-%dT%H:%M:%S%z')

    return psql_compatible_string

def main(appArg: Flask, dbArg: SQLAlchemy):
    global db, app
    app = appArg
    db = dbArg

    with app.app_context():
        insert_default_leagues()

        chrome_driver_path = chromedriver_autoinstaller.install()
        chrome_options = Options()
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--proxy-bypass-list=*")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-browser-side-navigation")

        try:
            # Initialize the Chrome webdriver using the updated path
            service = Service(executable_path=chrome_driver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            league = Leagues.query.filter_by(name="NBA").first()

            if league:
                scheduleCrawler(driver, league)  # Pass the league object

            else:
                print("League not found in the database.", file=sys.stderr)

        except Exception as e:
            print("Failed to connect to database or run crawler:", e, file=sys.stderr)
        
        finally:
            db.session.close()

if __name__ == '__main__':
    scheduler.add_job(main, 'interval', hours=6, args=[db, app])
    scheduler.start()
    