from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from os import environ
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = environ.get('DB_URL')
app.config['JWT_SECRET_KEY'] = 'xkYRtIG8FiHStcS5iS2aqsBeSFZcaj43cPDcX1Yph60GrQUbXC8YJP6MfOXV1DIv'
db = SQLAlchemy(app)
jwt = JWTManager(app)

class Match(db.Model):
    __tablename__ = 'matches'

    id = db.Column(db.Integer, primary_key=True)
    team1name = db.Column(db.String(80), nullable=False)
    team2name = db.Column(db.String(80), nullable=False)
    link = db.Column(db.String(200), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    league_id = db.Column(db.Integer, nullable=False)
    datetime = db.Column(db.DateTime, nullable=False)

    def json(self):
        return {
            'id': self.id,
            'team1name': self.team1name,
            'team2name': self.team2name,
            'link': self.link,
            'time': self.time,
            'date': self.date,
            'league_id': self.league_id,
            'datetime': self.datetime.strftime('%Y-%m-%d %H:%M:%S')
        }

db.create_all()

# Authorization decorator to protect all endpoints
def authorization_required(fn):
    @wraps(fn)  # Use wraps to preserve the original function metadata
    def wrapper(*args, **kwargs):
        if 'Authorization' not in request.headers:
            return make_response(jsonify({'message': 'Authorization header is missing'}), 401)
        
        try:
            access_token = request.headers['Authorization'].split(' ')[1]
            get_jwt_identity(access_token)
        except Exception as e:
            return make_response(jsonify({'message': 'Invalid token'}), 401)
        
        return fn(*args, **kwargs)
    
    return wrapper


# create a test route
@app.route('/test', methods=['GET'])
def test():
    return make_response(jsonify({'message': 'test route'}), 200)

# create a match
@app.route('/matches', methods=['POST'])
# @authorization_required
def create_match():
    try:
        data = request.get_json()
        required_fields = ['team1name', 'team2name', 'link', 'time', 'date', 'league_id', 'datetime']
        for field in required_fields:
            if field not in data:
                return make_response(jsonify({'message': f'Missing required field: {field}'}), 400)
        
        # Validate data types
        if not isinstance(data['team1name'], str) or not isinstance(data['team2name'], str):
            return make_response(jsonify({'message': 'Team names must be strings'}), 400)
        if not isinstance(data['link'], str) or not isinstance(data['time'], str) or not isinstance(data['date'], str):
            return make_response(jsonify({'message': 'Link, time, and date must be strings'}), 400)
        if not isinstance(data['league_id'], int):
            return make_response(jsonify({'message': 'League ID must be an integer'}), 400)
        
        new_match = Match(
            team1name=data['team1name'],
            team2name=data['team2name'],
            link=data['link'],
            time=data['time'],
            date=data['date'],
            league_id=data['league_id'],
            datetime=data['datetime']
        )
        db.session.add(new_match)
        db.session.commit()
        return make_response(jsonify({'message': 'match created'}), 201)
    except Exception as e:
        return make_response(jsonify({'message': 'error creating match', 'error': str(e)}), 500)


# get all matches
@app.route('/matches', methods=['GET'])
# @authorization_required
def get_matches():
    try:
        matches = Match.query.all()
        return make_response(jsonify([match.json() for match in matches]), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'error getting matches', 'error': str(e)}), 500)

# get a match by id
@app.route('/matches/<int:id>', methods=['GET'])
# @authorization_required
def get_match(id):
    try:
        match = Match.query.filter_by(id=id).first()
        if match:
            return make_response(jsonify({'match': match.json()}), 200)
        return make_response(jsonify({'message': 'match not found'}), 404)
    except Exception as e:
        return make_response(jsonify({'message': 'error getting match', 'error': str(e)}), 500)

# update a match
@app.route('/matches/<int:id>', methods=['PUT'])
# @authorization_required
def update_match(id):
    try:
        match = Match.query.filter_by(id=id).first()
        if match:
            data = request.get_json()
            match.team1name = data.get('team1name', match.team1name)
            match.team2name = data.get('team2name', match.team2name)
            match.link = data.get('link', match.link)
            match.time = data.get('time', match.time)
            match.date = data.get('date', match.date)
            match.league_id = data.get('league_id', match.league_id)
            match.datetime = data.get('datetime', match.datetime)
            db.session.commit()
            return make_response(jsonify({'message': 'match updated'}), 200)
        return make_response(jsonify({'message': 'match not found'}), 404)
    except Exception as e:
        return make_response(jsonify({'message': 'error updating match', 'error': str(e)}), 500)

# delete a match
@app.route('/matches/<int:id>', methods=['DELETE'])
# @authorization_required
def delete_match(id):
    try:
        match = Match.query.filter_by(id=id).first()
        if match:
            db.session.delete(match)
            db.session.commit()
            return make_response(jsonify({'message': 'match deleted'}), 200)
        return make_response(jsonify({'message': 'match not found'}), 404)
    except Exception as e:
        return make_response(jsonify({'message': 'error deleting match', 'error': str(e)}), 500)
