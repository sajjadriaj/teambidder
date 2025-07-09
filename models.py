from datetime import datetime
import uuid
import json
import secrets
import string
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def generate_short_code():
    """Generate a short 8-character alphanumeric code."""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))

class Auction(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    sport = db.Column(db.String(50), nullable=False)
    budget_per_team = db.Column(db.Float, nullable=False, default=1000000)  # Budget for each bidder
    max_players_per_team = db.Column(db.Integer, nullable=False, default=11)  # Maximum players per bidder
    admin_code = db.Column(db.String(8), nullable=False, default=generate_short_code)
    bidder_code = db.Column(db.String(8), nullable=False, default=generate_short_code)
    visitor_code = db.Column(db.String(8), nullable=False, default=generate_short_code)
    status = db.Column(db.String(20), default='lobby')  # lobby, countdown, active, completed
    current_player_id = db.Column(db.String(36), db.ForeignKey('player.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    ended_at = db.Column(db.DateTime, nullable=True)
    
    players = db.relationship('Player', backref='auction', lazy=True, cascade='all, delete-orphan', 
                              foreign_keys='Player.auction_id')
    current_player = db.relationship('Player', foreign_keys=[current_player_id], post_update=True)
    participants = db.relationship('Participant', backref='auction', lazy=True, cascade='all, delete-orphan')
    bids = db.relationship('Bid', backref='auction', lazy=True, cascade='all, delete-orphan')
    chat_messages = db.relationship('ChatMessage', backref='auction', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'sport': self.sport,
            'budget_per_team': self.budget_per_team,
            'max_players_per_team': self.max_players_per_team,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None
        }

class Player(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    auction_id = db.Column(db.String(36), db.ForeignKey('auction.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(50), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    starting_bid = db.Column(db.Float, nullable=False)
    current_bid = db.Column(db.Float, nullable=True)
    sold_to = db.Column(db.String(36), db.ForeignKey('participant.id'), nullable=True)
    status = db.Column(db.String(20), default='available')  # available, bidding, sold, unsold
    player_metadata = db.Column(db.Text)  # JSON string for additional sport-specific data
    
    bids = db.relationship('Bid', backref='player', lazy=True, cascade='all, delete-orphan')
    owner = db.relationship('Participant', foreign_keys=[sold_to], overlaps="owned_players")
    
    @property
    def metadata_dict(self):
        """Parse player_metadata JSON string into a dictionary."""
        if self.player_metadata:
            try:
                return json.loads(self.player_metadata)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'position': self.position,
            'rating': self.rating,
            'starting_bid': self.starting_bid,
            'current_bid': self.current_bid,
            'status': self.status,
            'sold_to': self.sold_to,
            'player_metadata': json.loads(self.player_metadata) if self.player_metadata else {}
        }

class Participant(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    auction_id = db.Column(db.String(36), db.ForeignKey('auction.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # bidder, visitor, admin
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    bids = db.relationship('Bid', backref='participant', lazy=True, cascade='all, delete-orphan')
    chat_messages = db.relationship('ChatMessage', backref='participant', lazy=True, cascade='all, delete-orphan')
    owned_players = db.relationship('Player', foreign_keys='Player.sold_to', backref='buyer', overlaps="owner")
    
    def get_total_spending(self):
        """Calculate total amount spent by this participant"""
        total_spent = 0
        for player in Player.query.filter_by(auction_id=self.auction_id, sold_to=self.id).all():
            if player.current_bid:
                total_spent += player.current_bid
        return total_spent
    
    def get_remaining_budget(self):
        """Calculate remaining budget for this participant"""
        auction = db.session.get(Auction, self.auction_id)
        if not auction or self.role != 'bidder':
            return 0
        return auction.budget_per_team - self.get_total_spending()
    
    def can_afford_bid(self, bid_amount):
        """Check if participant can afford a bid"""
        if self.role != 'bidder':
            return False
        remaining_budget = self.get_remaining_budget()
        return remaining_budget >= bid_amount
    
    def get_player_count(self):
        """Get number of players owned by this participant"""
        return Player.query.filter_by(auction_id=self.auction_id, sold_to=self.id).count()
    
    def can_bid_for_players(self):
        """Check if participant can bid for more players based on team size limit"""
        if self.role != 'bidder':
            return False
        
        auction = db.session.get(Auction, self.auction_id)
        if not auction:
            return False
            
        current_player_count = self.get_player_count()
        return current_player_count < auction.max_players_per_team
    
    def to_dict(self):
        data = {
            'id': self.id,
            'name': self.name,
            'role': self.role,
            'joined_at': self.joined_at.isoformat(),
            'is_active': self.is_active
        }
        if self.role == 'bidder':
            data['total_spending'] = self.get_total_spending()
            data['remaining_budget'] = self.get_remaining_budget()
            data['player_count'] = self.get_player_count()
            data['can_bid'] = self.can_bid_for_players()
        return data

class Bid(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    auction_id = db.Column(db.String(36), db.ForeignKey('auction.id'), nullable=False)
    player_id = db.Column(db.String(36), db.ForeignKey('player.id'), nullable=False)
    participant_id = db.Column(db.String(36), db.ForeignKey('participant.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'player_id': self.player_id,
            'participant_id': self.participant_id,
            'participant_name': self.participant.name,
            'amount': self.amount,
            'created_at': self.created_at.isoformat()
        }

class ChatMessage(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    auction_id = db.Column(db.String(36), db.ForeignKey('auction.id'), nullable=False)
    participant_id = db.Column(db.String(36), db.ForeignKey('participant.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'participant_name': self.participant.name,
            'message': self.message,
            'created_at': self.created_at.isoformat()
        }