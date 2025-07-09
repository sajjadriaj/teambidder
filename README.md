# Auction System

A real-time web-based auction system built with Flask and WebSockets, featuring live bidding, countdown timers, and multi-user support.

## Features

- 🏟️ **Real-time Auctions** - Live bidding with WebSocket updates
- 👥 **Multi-user Support** - Admin, Bidders, and Visitors with different permissions
- ⏱️ **Countdown Timers** - 60-second auction start countdown and bid timers
- 📱 **Responsive Design** - Works on desktop, tablet, and mobile
- 🔐 **Secure Access** - 8-character invitation codes for different user roles
- 📊 **Budget Tracking** - Real-time budget and spending calculations
- 💬 **Live Chat** - Real-time communication during auctions
- 🎨 **Modern UI** - Clean, intuitive interface with Tailwind CSS

## Quick Start

### Prerequisites
- Python 3.8+
- Modern web browser

### Installation
```bash
# Clone and setup
git clone <repository-url>
cd auction

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

The application will be available at `http://localhost:5000`

### Basic Usage

1. **Create an Auction**
   - Go to the home page and click "Create Auction"
   - Fill in auction details and upload a players JSON file
   - Get your invitation codes (Admin, Bidder, Visitor)

2. **Join as Bidders**
   - Share the bidder invitation code with team owners
   - They can join using the code and their team name

3. **Start the Auction**
   - As admin, click "Start Auction" when ready
   - 60-second countdown begins
   - Auction starts automatically with the first player

4. **Bid on Players**
   - Bidders can place bids during the bidding window
   - Real-time updates across all connected users
   - Highest bidder wins when timer expires

## Testing

The application includes comprehensive test suites for both end-to-end functionality and UI testing.

### Quick Test
```bash
# Run all tests
./test.sh

# Run only end-to-end tests
./test.sh e2e

# Run only UI tests (Selenium)
./test.sh ui selenium

# Run UI tests with Playwright
./test.sh ui playwright
```

### Test Types

#### End-to-End Tests
- **Simple E2E**: Basic auction workflow testing
- **Advanced E2E**: Comprehensive testing with WebSocket support

#### UI Tests
- **Selenium**: Traditional browser automation testing
- **Playwright**: Modern, fast browser testing
- **PyTest**: Structured testing with detailed reporting

### Test Coverage
- ✅ Auction creation and player upload
- ✅ 8-character invitation code generation
- ✅ Multi-bidder joining process
- ✅ Countdown timer functionality
- ✅ Real-time bidding and updates
- ✅ Budget tracking and validation
- ✅ Error handling and edge cases
- ✅ Responsive design testing
- ✅ Cross-browser compatibility

### Installing Test Dependencies
```bash
# Install basic testing
pip install requests beautifulsoup4

# Install UI testing frameworks
pip install selenium playwright pytest
playwright install chromium

# Or let the test script handle it
./test.sh install ui
```

### Environment Variables
```bash
# Run tests in headless mode
HEADLESS=true ./test.sh ui

# Use specific browser
TEST_BROWSER=firefox ./test.sh ui selenium
```

## Project Structure

```
auction/
├── app.py                  # Main Flask application
├── models.py               # Database models
├── requirements.txt        # Dependencies
├── test.sh                 # Unified test runner
├── static/                 # CSS, JS, images
├── templates/              # HTML templates
├── tests/                  # Test suite
│   ├── test_e2e_simple.py      # Simple E2E tests
│   ├── test_e2e_advanced.py    # Advanced E2E tests
│   ├── test_ui_selenium.py     # Selenium UI tests
│   ├── test_ui_playwright.py   # Playwright UI tests
│   ├── test_ui_pytest.py       # PyTest structured tests
│   └── test_players.json       # Test data
├── instance/               # Database files
└── uploads/                # Temporary uploads
```

## Player Data Format

Upload player data as JSON:

```json
[
  {
    "name": "Player Name",
    "position": "Position",
    "rating": 95,
    "starting_bid": 500000,
    "age": 30,
    "nationality": "Country"
  }
]
```

## API Endpoints

### Core Routes
- `GET /` - Home page
- `POST /create_auction` - Create new auction
- `GET /auction/<id>` - Auction lobby
- `GET /auction/<id>/view` - Live auction view
- `GET /join/<code>` - Join with invitation code
- `POST /join_auction` - Process join form

### WebSocket Events
- `join_auction` - Join auction room
- `send_message` - Send chat message
- `place_bid` - Place bid on player
- `countdown_start` - Auction countdown begins
- `auction_start` - Auction becomes active
- `new_bid` - New bid notification
- `player_sold` - Player sale completion

## Configuration

### Environment Variables
- `FLASK_ENV`: Set to `development` for debug mode
- `SECRET_KEY`: Flask secret key for sessions
- `DATABASE_URL`: Database connection string (default: SQLite)
- `HEADLESS`: Run UI tests in headless mode
- `TEST_BROWSER`: Specify browser for testing (chrome|firefox)

### Application Settings
- **Default Budget**: $2,000,000 per team
- **Default Max Players**: 11 per team
- **Countdown Timer**: 60 seconds
- **Bid Timer**: 30 seconds per player
- **Code Length**: 8 characters

## Development

### Running in Development
```bash
export FLASK_ENV=development
python app.py
```

### Database Management
```bash
# Initialize database (automatic on first run)
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Reset database
rm instance/auction.db
```

### Adding Features
1. Update models in `models.py`
2. Add routes in `app.py`
3. Create/update templates
4. Add corresponding tests
5. Run test suite: `./test.sh`

## Troubleshooting

### Common Issues

#### Application Won't Start
- Check Python version (3.8+ required)
- Install dependencies: `pip install -r requirements.txt`
- Check port 5000 availability

#### Database Errors
- Delete `instance/auction.db` to reset
- Check file permissions in instance directory

#### WebSocket Issues
- Ensure browser supports WebSockets
- Check firewall settings
- Try different browser

#### Testing Issues
- Ensure Flask app is running: `python app.py`
- Install test dependencies: `./test.sh install ui`
- For UI tests, install browser drivers

### Test Commands
```bash
# Show help
./test.sh help

# Run specific test type
./test.sh e2e                    # End-to-end only
./test.sh ui selenium            # Selenium UI tests
./test.sh ui playwright          # Playwright UI tests
./test.sh ui pytest             # PyTest structured tests
./test.sh ui all                 # All UI frameworks

# Install dependencies
./test.sh install ui             # UI testing deps
./test.sh install all            # All dependencies

# Clean up artifacts
./test.sh clean
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `./test.sh`
5. Submit a pull request

## License

This project is licensed under the MIT License.

---