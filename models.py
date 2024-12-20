from database import db
from datetime import datetime


class Leagues(db.Model):
    __tablename__ = 'leagues'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    url = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, nullable=True)

    matches = db.relationship("Matches", back_populates="league")

    def __init__(self, name, url, created_at):
        self.name = name
        self.url = url
        self.created_at = created_at

    def __repr__(self):
        return f"<Leagues(name='{self.name}', url='{self.url}')>"

    def json(self):
        return {'id': self.id, 'name': self.name, 'url': self.url}


class StreamSources(db.Model):
    __tablename__ = 'stream_sources'
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'))
    link = db.Column(db.String)
    source = db.Column(db.String)

    match = db.relationship("Matches", back_populates="stream_sources")

    def __init__(self, match_id, link, source):
        self.match_id = match_id
        self.link = link
        self.source = source

    def json(self):
        return {'id': self.id, 'match_id': self.match_id, 'link': self.link, 'source': self.source}


class Matches(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    team1name = db.Column(db.String, nullable=True, index=True)
    team2name = db.Column(db.String, nullable=True, index=True)
    link = db.Column(db.String, nullable=True)
    time = db.Column(db.String, nullable=True)
    date = db.Column(db.String, nullable=True)
    league_id = db.Column(db.Integer, db.ForeignKey('leagues.id'), index=True)
    datetime = db.Column(db.DateTime, nullable=True)
    expected_end_at = db.Column(db.DateTime, nullable=True)
    live_at = db.Column(db.DateTime, nullable=True)
    live_end_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=True)
    description = db.Column(db.String, nullable=True)
    last_crawl_time = db.Column(db.DateTime, nullable=True, default=None)
    source_found_at = db.Column(db.DateTime, nullable=True, default=None)
    isCrawling = db.Column(db.Boolean, nullable=False, default=False)

    # maybe later
    user_checked_at = db.Column(db.DateTime, nullable=True)
    # source_found_at = db.Column(db.DateTime, nullable=True)

    league = db.relationship("Leagues", back_populates="matches")
    stream_sources = db.relationship(
        "StreamSources", back_populates="match", cascade="all, delete-orphan")

    def __init__(self, team1name, team2name, link, time, date, league_id, datetime, live_at=None, description=None, last_crawl_time=None, isCrawling=False, created_at=None, live_end_at=None, expected_end_at=None, source_found_at=None, user_checked_at=None):
        self.team1name = team1name
        self.team2name = team2name
        self.link = link
        # match's current time
        self.time = time
        # match created time
        self.date = date
        self.league_id = league_id
        # match start time
        self.datetime = datetime
        self.expected_end_at = expected_end_at
        self.live_at = live_at
        self.live_end_at = live_end_at
        self.created_at = created_at
        self.description = description
        self.last_crawl_time = last_crawl_time
        self.isCrawling = isCrawling
        self.source_found_at = source_found_at
        self.user_checked_at = user_checked_at

    @property
    def isLive(self):
        """Returns True if the match is live, based on the current time."""
        current_time = datetime.now()
        # Check if the current time is within the match start and expected end times
        scheduled_time = self.datetime <= current_time < self.expected_end_at
        if scheduled_time:
            return scheduled_time
        if not self.live_end_at or not self.live_at:
            return False
        live_now = self.live_at <= current_time < self.live_end_at
        return live_now

    def json(self):
        return {
            'id': self.id,
            'team1name': self.team1name,
            'team2name': self.team2name,
            'link': self.link,
            'time': self.time,
            'date': self.date,
            'league_id': self.league_id,
            'datetime': self.datetime,
            'expected_end_at': self.expected_end_at,
            'live_at': self.live_at,
            'live_end_at': self.live_end_at,
            'description': self.description,
            'last_crawl_time': self.last_crawl_time,
            'isCrawling': self.isCrawling,
            'isLive': self.isLive,
            'source_found_at': self.source_found_at,
            'user_checked_at': self.user_checked_at,
        }

    def __repr__(self):
        return f"<Matches(id={self.id}, team1name='{self.team1name}', team2name='{self.team2name}', live_at={self.live_at}, description='{self.description}', last_crawl_time='{self.last_crawl_time}', datetime='{self.datetime}')>"
