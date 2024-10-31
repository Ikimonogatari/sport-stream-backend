from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from os import environ
import logging
from models import Matches, Leagues, StreamSources
from database import db
from datetime import datetime
from streamSourceCrawler import get_live_links, get_stream_sources
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import chromedriver_autoinstaller
app = Flask(__name__)
# app.logger.setLevel(logging.INFO)
app.config['SQLALCHEMY_DATABASE_URI'] = environ.get('DB_URL')
db.init_app(app)

CORS(app, supports_credentials=True)

@app.route('/matches', methods=['POST'])
def create_match():
    try:
        data = request.get_json()
        required_fields = ['team1name', 'team2name', 'link', 'time', 'date', 'league_id', 'datetime']
        if not all(field in data for field in required_fields):
            return make_response(jsonify({'message': 'Missing required fields'}), 400)
        
        new_match = Matches(**data)
        db.session.add(new_match)
        db.session.commit()
        return make_response(jsonify({'message': 'Match created'}), 201)
    except Exception as e:
        return make_response(jsonify({'message': 'Error creating match', 'error': str(e)}), 500)


@app.route('/matches', methods=['GET'])
def get_matches():
    try:
        now = datetime.now()
        future_matches = Matches.query.filter(Matches.datetime > now).all()
        return make_response(jsonify([match.json() for match in future_matches]), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'Error getting matches', 'error': str(e)}), 500)

@app.route('/all-matches', methods=['GET'])
def get_allmatches():
    try:
        all_matches = Matches.query.all()
        return make_response(jsonify([match.json() for match in all_matches]), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'Error getting matches', 'error': str(e)}), 500)

@app.route('/stream_sources', methods=['GET'])
def get_streamsources():
    try:
        stream_sources = StreamSources.query.all()
        return make_response(jsonify([stream_source.json() for stream_source in stream_sources]), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'Error getting stream sources', 'error': str(e)}), 500)

@app.route('/live-matches', methods=['GET'])
def get_live_matches():
    try:
        live_matches = Matches.query.filter_by(isLive=True).all()
        return make_response(jsonify([match.json() for match in live_matches]), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'Error getting live matches', 'error': str(e)}), 500)

@app.route('/leagues', methods=['GET'])
def get_leagues():
    try:
        leagues = Leagues.query.all()
        return make_response(jsonify([league.json() for league in leagues]), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'Error getting leagues', 'error': str(e)}), 500)

@app.route('/matches/<int:id>', methods=['GET'])
def get_match(id):
    try:
        match = Matches.query.get(id)
        if match:
            return make_response(jsonify({'match': match.json()}), 200)
        return make_response(jsonify({'message': 'Match not found'}), 404)
    except Exception as e:
        return make_response(jsonify({'message': 'Error getting match', 'error': str(e)}), 500)

@app.route('/matches/<int:id>', methods=['PUT'])
def update_match(id):
    try:
        match = Matches.query.get(id)
        if match:
            data = request.get_json()
            for key, value in data.items():
                setattr(match, key, value)
            db.session.commit()
            return make_response(jsonify({'message': 'Match updated'}), 200)
        return make_response(jsonify({'message': 'Match not found'}), 404)
    except Exception as e:
        return make_response(jsonify({'message': 'Error updating match', 'error': str(e)}), 500)

@app.route('/matches/<int:id>', methods=['DELETE'])
def delete_match(id):
    try:
        match = Matches.query.get(id)
        if match:
            db.session.delete(match)
            db.session.commit()
            return make_response(jsonify({'message': 'Match deleted'}), 200)
        return make_response(jsonify({'message': 'Match not found'}), 404)
    except Exception as e:
        return make_response(jsonify({'message': 'Error deleting match', 'error': str(e)}), 500)

@app.route('/matches/by-league', methods=['GET'])
def get_matches_by_league():
    try:
        app.logger.info("Received request for matches by league")
        
        league_name = request.args.get('league_name')
        app.logger.info(f"League name received: {league_name}")

        if not league_name:
            app.logger.warning("League name is missing")
            return make_response(jsonify({'message': 'League name is required'}), 400)

        league = Leagues.query.filter_by(name=league_name).first()
        if not league:
            app.logger.warning(f"League not found: {league_name}")
            return make_response(jsonify({'message': 'League not found'}), 404)

        matches = Matches.query.filter_by(league_id=league.id).all()
        return make_response(jsonify([match.json() for match in matches]), 200)
    except Exception as e:
        app.logger.error(f"Error getting matches: {str(e)}")
        return make_response(jsonify({'message': 'Error getting matches', 'error': str(e)}), 500)

@app.route('/matches/<int:match_id>/stream_sources', methods=['GET'])
def get_stream_sources_for_match(match_id):
    print("CRAWLING HERE FOR REAL NIGGA")
    # chrome_driver_path = chromedriver_autoinstaller.install()
    chrome_options = Options()
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--proxy-bypass-list=*")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-browser-side-navigation")
    # service = Service(executable_path=chrome_driver_path)
    driver = webdriver.Chrome(options=chrome_options)

    try:
        stream_sources = [] 
        match = Matches.query.get(match_id)
        if not match:
            return make_response(jsonify({'message': 'Match not found'}), 404)

        last_crawl_time = match.last_crawl_time or datetime.min

        if match.isCrawling or (datetime.now() - last_crawl_time).total_seconds() < 300:
            print("CRAWLING NEW SOURCES")
            stream_sources = StreamSources.query.filter_by(match_id=match_id).all()
            return make_response(jsonify([source.json() for source in stream_sources]), 200)

        # Set isCrawling to True and update the last_crawl_time
        match.isCrawling = True
        match.last_crawl_time = datetime.now()
        db.session.commit()

        # Start the crawler
        stream_links = get_live_links(driver, match.link)
        if stream_links:

            stream_sources = get_stream_sources(driver, stream_links)
            # Save sources to database
            for source in stream_sources:
                if not StreamSources.query.filter_by(match_id=match_id, link=source).first():
                    db.session.add(StreamSources(match_id=match_id, link=source))
            db.session.commit()

        match.isCrawling = False
        db.session.commit()

        # Return the fetched sources
        return make_response(jsonify(stream_sources), 200)
        # return make_response(jsonify([source.json() for source in stream_sources]), 200)
        
        # stream_sources = StreamSources.query.filter_by(match_id=match_id).all()
        # return make_response(jsonify([stream_source.json() for stream_source in stream_sources]), 200)
    except Exception as e:
        app.logger.error(f"Error getting stream sources for match: {str(e)}")
        return make_response(jsonify({'message': 'Error getting stream sources', 'error': str(e)}), 500)

import matchCrawler
import streamSourceCrawler
app.logger.info("main")
with app.app_context():
    db.create_all()
    matchCrawler.main_loop(app, db)
    streamSourceCrawler.main_loop(app, db)
    
    app.run(debug=False)
