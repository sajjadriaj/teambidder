from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename
import json
import uuid
import os
from datetime import datetime
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auction.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
from models import db
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Store active auctions in memory for real-time updates
active_auctions = {}

# Import models
from models import Auction, Player, Participant, Bid, ChatMessage

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@app.route('/create_auction', methods=['GET', 'POST'])
def create_auction():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            sport = request.form.get('sport')
            budget_per_team = request.form.get('budget_per_team')
            max_players_per_team = request.form.get('max_players_per_team', 11)
            
            if not name or not sport or not budget_per_team:
                flash('Name, sport, and budget are required')
                return redirect(url_for('create_auction'))
            
            try:
                budget_per_team = float(budget_per_team)
                if budget_per_team < 50000:
                    flash('Budget must be at least $50,000')
                    return redirect(url_for('create_auction'))
                    
                max_players_per_team = int(max_players_per_team)
                if max_players_per_team < 1 or max_players_per_team > 50:
                    flash('Max players per team must be between 1 and 50')
                    return redirect(url_for('create_auction'))
            except ValueError:
                flash('Invalid budget amount or max players per team')
                return redirect(url_for('create_auction'))
            
            # Handle file upload
            if 'players_file' not in request.files:
                flash('Players file is required')
                return redirect(url_for('create_auction'))
            
            file = request.files['players_file']
            if file.filename == '':
                flash('No file selected')
                return redirect(url_for('create_auction'))
            
            if file and file.filename.endswith('.json'):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Parse JSON file
                try:
                    with open(file_path, 'r') as f:
                        players_data = json.load(f)
                    
                    # Create auction
                    auction = Auction(name=name, sport=sport, budget_per_team=budget_per_team, max_players_per_team=max_players_per_team)
                    db.session.add(auction)
                    db.session.flush()
                    
                    # Add admin as participant
                    admin = Participant(
                        auction_id=auction.id,
                        name=f"Admin_{auction.id[:8]}",
                        role='admin'
                    )
                    db.session.add(admin)
                    db.session.flush()  # Ensure admin gets an ID
                    session['participant_id'] = admin.id
                    
                    # Create players from JSON
                    for player_data in players_data:
                        player = Player(
                            auction_id=auction.id,
                            name=player_data['name'],
                            position=player_data['position'],
                            rating=float(player_data['rating']),
                            starting_bid=float(player_data['starting_bid']),
                            player_metadata=json.dumps({k: v for k, v in player_data.items() 
                                               if k not in ['name', 'position', 'rating', 'starting_bid']})
                        )
                        db.session.add(player)
                    
                    db.session.commit()
                    
                    # Initialize auction state
                    active_auctions[auction.id] = {
                        'status': 'lobby',
                        'current_player': None,
                        'countdown': 0,
                        'participants': {}
                    }
                    
                    # Clean up uploaded file
                    os.remove(file_path)
                    
                    return redirect(url_for('auction_lobby', auction_id=auction.id))
                    
                except json.JSONDecodeError:
                    flash('Invalid JSON file format')
                    return redirect(url_for('create_auction'))
                except Exception as e:
                    flash(f'Error processing file: {str(e)}')
                    return redirect(url_for('create_auction'))
            else:
                flash('Please upload a JSON file')
                return redirect(url_for('create_auction'))
                
        except Exception as e:
            flash(f'Error creating auction: {str(e)}')
            return redirect(url_for('create_auction'))
    
    return render_template('create_auction.html')

@app.route('/auction/<auction_id>')
def auction_lobby(auction_id):
    auction = Auction.query.get_or_404(auction_id)
    
    # Check if user has access to this auction
    participant_id = session.get('participant_id')
    if not participant_id:
        flash('You must join the auction with an invitation code first')
        return redirect(url_for('index'))
    
    participant = db.session.get(Participant, participant_id)
    if not participant:
        flash('Invalid participant session')
        return redirect(url_for('index'))
    
    if participant.auction_id != auction_id:
        flash('You do not have access to this auction')
        return redirect(url_for('index'))
    
    # Check if user is admin
    is_admin = participant.role == 'admin'
    
    players = Player.query.filter_by(auction_id=auction_id).all()
    participants = Participant.query.filter_by(auction_id=auction_id, is_active=True).all()
    
    # Get stats
    total_players = len(players)
    total_bidders = len([p for p in participants if p.role == 'bidder'])
    total_visitors = len([p for p in participants if p.role == 'visitor'])
    
    return render_template('auction_lobby.html', 
                         auction=auction,
                         players=players,
                         participants=participants,
                         is_admin=is_admin,
                         total_players=total_players,
                         total_bidders=total_bidders,
                         total_visitors=total_visitors)

@app.route('/join/<code>')
def join_auction(code):
    # Find auction by admin, bidder, or visitor code
    auction = Auction.query.filter(
        (Auction.admin_code == code) | (Auction.bidder_code == code) | (Auction.visitor_code == code)
    ).first()
    
    if not auction:
        flash('Invalid invitation code')
        return redirect(url_for('index'))
    
    # Determine role
    if auction.admin_code == code:
        role = 'admin'
    elif auction.bidder_code == code:
        role = 'bidder'
    else:
        role = 'visitor'
    
    # Check if auction has started and role is bidder
    if auction.status != 'lobby' and role == 'bidder':
        flash('Cannot join as bidder after auction has started')
        return redirect(url_for('auction_view', auction_id=auction.id))
    
    return render_template('join_auction.html', auction=auction, role=role, code=code)

@app.route('/join_auction', methods=['POST'])
def join_auction_post():
    code = request.form.get('code')
    name = request.form.get('name')
    
    if not code or not name:
        flash('Code and name are required')
        return redirect(url_for('index'))
    
    # Find auction
    auction = Auction.query.filter(
        (Auction.admin_code == code) | (Auction.bidder_code == code) | (Auction.visitor_code == code)
    ).first()
    
    if not auction:
        flash('Invalid invitation code')
        return redirect(url_for('index'))
    
    # Determine role
    if auction.admin_code == code:
        role = 'admin'
    elif auction.bidder_code == code:
        role = 'bidder'
    else:
        role = 'visitor'
    
    # Check if auction has started and role is bidder
    if auction.status != 'lobby' and role == 'bidder':
        flash('Cannot join as bidder after auction has started')
        return redirect(url_for('auction_view', auction_id=auction.id))
    
    # For admin role, check if admin already exists
    if role == 'admin':
        existing_admin = Participant.query.filter_by(
            auction_id=auction.id,
            role='admin'
        ).first()
        
        if existing_admin:
            # Admin already exists, sign in as existing admin
            session['participant_id'] = existing_admin.id
            existing_admin.is_active = True
            db.session.commit()
        else:
            # Create new admin (shouldn't happen normally)
            participant = Participant(
                auction_id=auction.id,
                name=name,
                role=role
            )
            db.session.add(participant)
            db.session.commit()
            session['participant_id'] = participant.id
    else:
        # Check if participant already exists
        existing = Participant.query.filter_by(
            auction_id=auction.id,
            name=name,
            role=role
        ).first()
        
        if existing:
            session['participant_id'] = existing.id
            existing.is_active = True
            db.session.commit()
        else:
            # Create new participant
            participant = Participant(
                auction_id=auction.id,
                name=name,
                role=role
            )
            db.session.add(participant)
            db.session.commit()
            session['participant_id'] = participant.id
    
    # Redirect based on auction status
    if auction.status == 'lobby':
        return redirect(url_for('auction_lobby', auction_id=auction.id))
    else:
        return redirect(url_for('auction_view', auction_id=auction.id))

@app.route('/auction/<auction_id>/view')
def auction_view(auction_id):
    auction = Auction.query.get_or_404(auction_id)
    
    # Check if user has access to this auction
    participant_id = session.get('participant_id')
    if not participant_id:
        flash('You must join the auction with an invitation code first')
        return redirect(url_for('index'))
    
    participant = db.session.get(Participant, participant_id)
    if not participant or participant.auction_id != auction_id:
        flash('You do not have access to this auction')
        return redirect(url_for('index'))
    
    if auction.status == 'lobby':
        return redirect(url_for('auction_lobby', auction_id=auction_id))
    
    current_player = None
    if auction.current_player_id:
        current_player = db.session.get(Player, auction.current_player_id)
    
    players = Player.query.filter_by(auction_id=auction_id).all()
    participants = Participant.query.filter_by(auction_id=auction_id, is_active=True).all()
    
    return render_template('auction_view.html',
                         auction=auction,
                         current_player=current_player,
                         players=players,
                         participants=participants,
                         participant=participant)

@app.route('/auction/<auction_id>/start', methods=['POST'])
def start_auction(auction_id):
    auction = Auction.query.get_or_404(auction_id)
    
    # Check if user is admin
    participant_id = session.get('participant_id')
    if not participant_id:
        return jsonify({'error': 'Not authorized'}), 401
    
    participant = db.session.get(Participant, participant_id)
    if not participant or participant.auction_id != auction_id or participant.role != 'admin':
        return jsonify({'error': 'Not authorized'}), 401
    
    if auction.status != 'lobby':
        return jsonify({'error': 'Auction cannot be started'}), 400
    
    # Start countdown
    auction.status = 'countdown'
    db.session.commit()
    
    # Update active auction state
    active_auctions[auction_id]['status'] = 'countdown'
    active_auctions[auction_id]['countdown'] = 60
    
    # Emit countdown start to all participants
    socketio.emit('countdown_start', {'countdown': 60}, room=auction_id)
    
    # Start countdown thread
    threading.Thread(target=countdown_thread, args=(auction_id,)).start()
    
    return jsonify({'success': True})

@app.route('/recover_admin', methods=['POST'])
def recover_admin():
    data = request.get_json()
    auction_name = data.get('auction_name')
    
    if not auction_name:
        return jsonify({'success': False, 'message': 'Auction name is required'})
    
    # Find auction by name
    auction = Auction.query.filter_by(name=auction_name).first()
    
    if not auction:
        return jsonify({'success': False, 'message': 'Auction not found'})
    
    return jsonify({
        'success': True, 
        'admin_code': auction.admin_code,
        'auction_id': auction.id
    })

@app.route('/auction/<auction_id>/messages')
def get_chat_messages(auction_id):
    # Check if user has access to this auction
    participant_id = session.get('participant_id')
    if not participant_id:
        return jsonify({'error': 'Not authorized'}), 401
    
    participant = db.session.get(Participant, participant_id)
    if not participant or participant.auction_id != auction_id:
        return jsonify({'error': 'Not authorized'}), 401
    
    # Get recent chat messages
    messages = ChatMessage.query.filter_by(auction_id=auction_id)\
                               .order_by(ChatMessage.created_at.asc())\
                               .limit(50)\
                               .all()
    
    return jsonify({
        'messages': [message.to_dict() for message in messages]
    })

def countdown_thread(auction_id):
    with app.app_context():
        try:
            countdown = 60
            while countdown > 0:
                time.sleep(1)
                countdown -= 1
                if auction_id in active_auctions:
                    active_auctions[auction_id]['countdown'] = countdown
                    socketio.emit('countdown_update', {'countdown': countdown}, room=auction_id)
            
            # Start auction
            auction = db.session.get(Auction, auction_id)
            if not auction:
                print(f"Error: Auction {auction_id} not found")
                return
                
            auction.status = 'active'
            auction.started_at = datetime.utcnow()
            
            # Get first player
            first_player = Player.query.filter_by(auction_id=auction_id, status='available').first()
            print(f"First player for auction {auction_id}: {first_player}")
            
            if first_player:
                auction.current_player_id = first_player.id
                first_player.status = 'bidding'
                first_player.current_bid = first_player.starting_bid
            else:
                print(f"No available players found for auction {auction_id}")
                # Check if there are any players at all
                all_players = Player.query.filter_by(auction_id=auction_id).all()
                print(f"Total players in auction {auction_id}: {len(all_players)}")
                for player in all_players:
                    print(f"  - {player.name} (status: {player.status})")
            
            db.session.commit()
            
            # Update active auction state
            if auction_id in active_auctions:
                active_auctions[auction_id]['status'] = 'active'
                active_auctions[auction_id]['current_player'] = first_player.id if first_player else None
            
            # Emit auction start even if no players (so users can see the auction page)
            socketio.emit('auction_start', {
                'current_player': first_player.to_dict() if first_player else None
            }, room=auction_id)
            
            print(f"Auction {auction_id} started successfully")
            
        except Exception as e:
            print(f"Error in countdown_thread for auction {auction_id}: {str(e)}")
            import traceback
            traceback.print_exc()

# Socket handlers
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('join_auction')
def handle_join_auction(data):
    auction_id = data['auction_id']
    participant_id = session.get('participant_id')
    
    if not participant_id:
        emit('error', {'message': 'Not authorized'})
        return
    
    participant = db.session.get(Participant, participant_id)
    if not participant or participant.auction_id != auction_id:
        emit('error', {'message': 'Not authorized'})
        return
    
    join_room(auction_id)
    
    # Add participant to active auction
    if auction_id not in active_auctions:
        active_auctions[auction_id] = {
            'status': 'lobby',
            'current_player': None,
            'countdown': 0,
            'participants': {}
        }
    
    # Check if participant is already in the room
    was_already_joined = participant_id in active_auctions[auction_id]['participants']
    
    active_auctions[auction_id]['participants'][participant_id] = {
        'name': participant.name,
        'role': participant.role
    }
    
    emit('joined_auction', {'auction_id': auction_id, 'participant': participant.to_dict()})
    
    # Only notify others about new participant if they weren't already in the room
    if not was_already_joined:
        emit('participant_joined', {
            'participant': participant.to_dict()
        }, room=auction_id, include_self=False)

@socketio.on('send_message')
def handle_send_message(data):
    auction_id = data['auction_id']
    message = data['message']
    participant_id = session.get('participant_id')
    
    if not participant_id or not message.strip():
        emit('error', {'message': 'Invalid message'})
        return
    
    participant = db.session.get(Participant, participant_id)
    if not participant or participant.auction_id != auction_id:
        emit('error', {'message': 'Not authorized'})
        return
    
    # Save message to database
    chat_message = ChatMessage(
        auction_id=auction_id,
        participant_id=participant_id,
        message=message.strip()
    )
    db.session.add(chat_message)
    db.session.commit()
    
    # Emit message to all participants
    emit('new_message', {
        'message': chat_message.to_dict()
    }, room=auction_id)

@socketio.on('place_bid')
def handle_place_bid(data):
    auction_id = data['auction_id']
    player_id = data['player_id']
    bid_amount = float(data['bid_amount'])
    participant_id = session.get('participant_id')
    
    if not participant_id:
        emit('error', {'message': 'Not authorized'})
        return
    
    participant = db.session.get(Participant, participant_id)
    if not participant or participant.auction_id != auction_id or participant.role != 'bidder':
        emit('error', {'message': 'Not authorized to bid'})
        return
    
    auction = db.session.get(Auction, auction_id)
    player = db.session.get(Player, player_id)
    
    if not auction or not player or auction.status != 'active':
        emit('error', {'message': 'Invalid auction or player'})
        return
    
    if auction.current_player_id != player_id:
        emit('error', {'message': 'Not the current player'})
        return
    
    # Check if participant can afford the bid
    if not participant.can_afford_bid(bid_amount):
        emit('error', {'message': 'Insufficient budget'})
        return
    
    # Check if participant can bid for more players (player limit logic)
    if not participant.can_bid_for_players():
        emit('error', {'message': f'You already have {participant.get_player_count()} players (maximum {auction.max_players_per_team})'})
        return
    
    # Check minimum bid amount
    if bid_amount <= player.current_bid:
        emit('error', {'message': 'Bid must be higher than current bid'})
        return
    
    # Create and save bid
    bid = Bid(
        auction_id=auction_id,
        player_id=player_id,
        participant_id=participant_id,
        amount=bid_amount
    )
    db.session.add(bid)
    
    # Update player's current bid
    player.current_bid = bid_amount
    db.session.commit()
    
    # Emit bid to all participants
    emit('bid_placed', {
        'bid': bid.to_dict(),
        'player': player.to_dict()
    }, room=auction_id)

@socketio.on('end_player_bidding')
def handle_end_player_bidding(data):
    auction_id = data['auction_id']
    player_id = data['player_id']
    participant_id = session.get('participant_id')
    
    if not participant_id:
        emit('error', {'message': 'Not authorized'})
        return
    
    participant = db.session.get(Participant, participant_id)
    if not participant or participant.auction_id != auction_id or participant.role != 'admin':
        emit('error', {'message': 'Not authorized'})
        return
    
    auction = db.session.get(Auction, auction_id)
    player = db.session.get(Player, player_id)
    
    if not auction or not player or auction.status != 'active':
        emit('error', {'message': 'Invalid auction or player'})
        return
    
    if auction.current_player_id != player_id:
        emit('error', {'message': 'Not the current player'})
        return
    
    # Mark player as sold if there were bids
    highest_bid = Bid.query.filter_by(player_id=player_id).order_by(Bid.amount.desc()).first()
    if highest_bid:
        player.sold_to = highest_bid.participant_id
        player.status = 'sold'
    else:
        player.status = 'unsold'
    
    # Find next available player
    next_player = Player.query.filter_by(
        auction_id=auction_id, 
        status='available'
    ).first()
    
    if next_player:
        # Move to next player
        auction.current_player_id = next_player.id
        next_player.status = 'bidding'
        next_player.current_bid = next_player.starting_bid
        db.session.commit()
        
        emit('player_bidding_ended', {
            'player': player.to_dict(),
            'next_player': next_player.to_dict()
        }, room=auction_id)
    else:
        # End auction
        auction.status = 'completed'
        auction.ended_at = datetime.utcnow()
        auction.current_player_id = None
        db.session.commit()
        
        emit('player_bidding_ended', {
            'player': player.to_dict(),
            'auction_ended': True
        }, room=auction_id)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)