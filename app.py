from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from os import environ
from models import Matches, Leagues, StreamSources
from database import db
from datetime import datetime, timedelta
import pytz


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = environ.get('DB_URL') if environ.get(
    'DB_URL') else 'postgresql://sportstream:cXK99Y82erOm4608@localhost:5436/sportstream'
db.init_app(app)

mongolia_tz = pytz.timezone('Asia/Ulaanbaatar')

CORS(app, supports_credentials=True)


@app.route('/matches', methods=['POST'])
def create_match():
    try:
        data = request.get_json()
        required_fields = ['team1name', 'team2name',
                           'link', 'time', 'date', 'league_id', 'datetime']
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
        live_matches = Matches.query.filter(
            Matches.datetime <= datetime.now(),
            Matches.expected_end_at >= datetime.now()
        ).all()
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
        current_time_mongolia = datetime.now(
            mongolia_tz).replace(microsecond=0, tzinfo=None)
        # Get the current time and subtract 3 hours
        three_hours_ago = current_time_mongolia - timedelta(hours=3)

        # Query for matches in this league with datetime no older than 3 hours ago
        matches = Matches.query.filter(
            Matches.league_id == league.id,
            Matches.datetime >= three_hours_ago
        ).all()

        return make_response(jsonify([match.json() for match in matches]), 200)
    except Exception as e:
        app.logger.error(f"Error getting matches: {str(e)}")
        return make_response(jsonify({'message': 'Error getting matches', 'error': str(e)}), 500)


@app.route('/matches/<int:match_id>/stream_sources', methods=['GET'])
def get_stream_sources_for_match(match_id):
    try:
        match = Matches.query.get(match_id)
        if not match:
            return make_response(jsonify({'message': 'Match not found'}), 404)
        if not match.isLive:
            return make_response(jsonify({'message': 'Match is not live'}), 200)
        all_sources = StreamSources.query.filter_by(match_id=match_id).all()
        return make_response(jsonify([source.json() for source in all_sources]), 200)

    except Exception as e:
        app.logger.error(f"Error getting stream sources for match: {str(e)}")
        return make_response(jsonify({'message': 'Error getting stream sources', 'error': str(e)}), 500)


if __name__ == '__main__':
    app.run(debug=False, port=5000)
