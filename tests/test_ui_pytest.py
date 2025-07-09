#!/usr/bin/env python3
"""
PyTest-based UI Testing for Auction System
==========================================

This script uses PyTest with Selenium for structured UI testing.
It provides better test organization, fixtures, and reporting.

Requirements:
- pip install pytest selenium pytest-html
- Chrome/ChromeDriver or Firefox/GeckoDriver

Usage:
    pytest test_ui_pytest.py -v
    pytest test_ui_pytest.py --html=report.html
"""

import pytest
import json
import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

BASE_URL = "http://localhost:5000"
WAIT_TIMEOUT = 30

class TestData:
    """Test data container"""
    AUCTION_NAME = "PyTest Auction"
    SPORT = "Football"
    BUDGET = 2000000
    MAX_PLAYERS = 4
    
    BIDDERS = [
        "Manchester United",
        "Chelsea FC", 
        "Arsenal FC"
    ]
    
    PLAYERS = [
        {
            "name": "Lionel Messi",
            "position": "Forward",
            "rating": 95,
            "starting_bid": 500000,
            "age": 36,
            "nationality": "Argentina"
        },
        {
            "name": "Cristiano Ronaldo",
            "position": "Forward",
            "rating": 93,
            "starting_bid": 450000,
            "age": 38,
            "nationality": "Portugal"
        },
        {
            "name": "Kylian Mbappé",
            "position": "Forward",
            "rating": 91,
            "starting_bid": 400000,
            "age": 24,
            "nationality": "France"
        }
    ]

@pytest.fixture(scope="session")
def browser():
    """Browser fixture for the entire test session"""
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    # Add headless option based on environment
    if os.environ.get('HEADLESS', 'false').lower() == 'true':
        options.add_argument('--headless')
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    
    yield driver
    
    driver.quit()

@pytest.fixture(scope="session")
def test_players_file():
    """Create test players file"""
    file_path = "/tmp/pytest_players.json"
    with open(file_path, 'w') as f:
        json.dump(TestData.PLAYERS, f, indent=2)
    
    yield file_path
    
    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)

@pytest.fixture(scope="session")
def auction_data(browser, test_players_file):
    """Create auction and return auction data"""
    # Navigate to create auction
    browser.get(BASE_URL)
    create_button = WebDriverWait(browser, WAIT_TIMEOUT).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Create Auction"))
    )
    create_button.click()
    
    # Fill form
    WebDriverWait(browser, WAIT_TIMEOUT).until(
        EC.presence_of_element_located((By.ID, "name"))
    )
    
    browser.find_element(By.ID, "name").send_keys(TestData.AUCTION_NAME)
    browser.find_element(By.ID, "sport").send_keys(TestData.SPORT)
    browser.find_element(By.ID, "budget_per_team").send_keys(str(TestData.BUDGET))
    browser.find_element(By.ID, "max_players_per_team").send_keys(str(TestData.MAX_PLAYERS))
    
    # Upload file
    file_input = browser.find_element(By.ID, "players_file")
    file_input.send_keys(test_players_file)
    
    # Submit
    submit_button = browser.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()
    
    # Wait for redirect and extract auction ID
    WebDriverWait(browser, WAIT_TIMEOUT).until(
        EC.url_contains("/auction/")
    )
    
    auction_id = browser.current_url.split("/auction/")[1]
    
    # Extract invitation codes
    invitation_codes = {}
    code_elements = browser.find_elements(By.CSS_SELECTOR, "code")
    
    for code_element in code_elements:
        code_text = code_element.text.strip()
        if len(code_text) == 8:
            parent_text = code_element.find_element(By.XPATH, "../..").text.lower()
            if "admin" in parent_text:
                invitation_codes["admin"] = code_text
            elif "bidder" in parent_text:
                invitation_codes["bidder"] = code_text
            elif "visitor" in parent_text:
                invitation_codes["visitor"] = code_text
    
    return {
        "id": auction_id,
        "codes": invitation_codes
    }

@pytest.fixture(scope="session")
def bidder_sessions(browser, auction_data):
    """Create bidder sessions"""
    if not auction_data["codes"].get("bidder"):
        pytest.skip("No bidder code available")
    
    bidder_code = auction_data["codes"]["bidder"]
    bidder_windows = []
    
    for i, bidder_name in enumerate(TestData.BIDDERS):
        # Open new window for each bidder (except first)
        if i > 0:
            browser.execute_script("window.open('');")
            browser.switch_to.window(browser.window_handles[-1])
        
        # Join auction
        browser.get(f"{BASE_URL}/join/{bidder_code}")
        
        name_field = WebDriverWait(browser, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.ID, "name"))
        )
        name_field.send_keys(bidder_name)
        
        submit_button = browser.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        
        # Wait for redirect
        WebDriverWait(browser, WAIT_TIMEOUT).until(
            EC.url_contains("/auction/")
        )
        
        bidder_windows.append(browser.current_window_handle)
    
    return bidder_windows

class TestAuctionUI:
    """Main UI test class"""
    
    def test_home_page_loads(self, browser):
        """Test home page loading"""
        browser.get(BASE_URL)
        
        assert "Auction System" in browser.title
        
        create_button = browser.find_element(By.LINK_TEXT, "Create Auction")
        assert create_button.is_displayed()
        
        join_section = browser.find_element(By.ID, "join-code")
        assert join_section.is_displayed()
    
    def test_auction_creation(self, auction_data):
        """Test auction creation"""
        assert auction_data["id"] is not None
        assert len(auction_data["id"]) > 0
        assert auction_data["codes"].get("bidder") is not None
    
    def test_invitation_codes_format(self, auction_data):
        """Test invitation codes format"""
        codes = auction_data["codes"]
        
        for code_type, code in codes.items():
            assert len(code) == 8
            assert code.isalnum()
            assert code.isupper()
    
    def test_copy_functionality(self, browser, auction_data):
        """Test copy button functionality"""
        browser.get(f"{BASE_URL}/auction/{auction_data['id']}")
        
        copy_buttons = browser.find_elements(By.CSS_SELECTOR, "button[onclick*='copyCode']")
        assert len(copy_buttons) > 0
        
        for button in copy_buttons:
            # Click copy button
            button.click()
            
            # Wait for feedback
            time.sleep(1)
            
            # Check for success indicator
            button_html = button.get_attribute("innerHTML")
            assert "check" in button_html.lower()
            
            # Wait for reset
            time.sleep(2)
    
    def test_bidder_joining(self, bidder_sessions):
        """Test bidder joining process"""
        assert len(bidder_sessions) >= 2
        
        # Test passes if fixture runs successfully
        # (bidder_sessions fixture handles the actual joining)
    
    def test_participants_display(self, browser, auction_data, bidder_sessions):
        """Test participants display in UI"""
        browser.switch_to.window(bidder_sessions[0])
        
        participants = browser.find_elements(By.CSS_SELECTOR, ".participant-item, .participant")
        assert len(participants) >= 2
        
        # Check if bidder names appear
        participant_texts = [p.text for p in participants]
        participant_text = " ".join(participant_texts)
        
        assert any(bidder in participant_text for bidder in TestData.BIDDERS)
    
    def test_start_auction_button(self, browser, auction_data, bidder_sessions):
        """Test start auction button"""
        browser.switch_to.window(bidder_sessions[0])  # Admin window
        
        start_button = WebDriverWait(browser, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[onclick*='startAuction']"))
        )
        
        assert start_button.is_displayed()
        assert start_button.is_enabled()
    
    def test_auction_start_countdown(self, browser, auction_data, bidder_sessions):
        """Test auction start and countdown"""
        browser.switch_to.window(bidder_sessions[0])  # Admin window
        
        # Start auction
        start_button = browser.find_element(By.CSS_SELECTOR, "button[onclick*='startAuction']")
        start_button.click()
        
        # Wait for countdown modal
        countdown_modal = WebDriverWait(browser, WAIT_TIMEOUT).until(
            EC.visibility_of_element_located((By.ID, "countdownModal"))
        )
        
        assert countdown_modal.is_displayed()
        
        # Check countdown timer
        countdown_timer = browser.find_element(By.ID, "countdown-timer")
        initial_time = int(countdown_timer.text)
        
        assert initial_time > 0
        assert initial_time <= 60
        
        # Wait a few seconds and check if counting down
        time.sleep(5)
        current_time = int(countdown_timer.text)
        
        assert current_time < initial_time
    
    @pytest.mark.slow
    def test_countdown_completion(self, browser, auction_data, bidder_sessions):
        """Test countdown completion (slow test)"""
        browser.switch_to.window(bidder_sessions[0])
        
        # Wait for countdown to complete (this is a slow test)
        countdown_timer = browser.find_element(By.ID, "countdown-timer")
        
        # Wait up to 70 seconds for countdown
        start_time = time.time()
        while time.time() - start_time < 70:
            try:
                current_time = int(countdown_timer.text)
                if current_time <= 0:
                    break
                time.sleep(1)
            except:
                break
        
        # Wait for redirect
        WebDriverWait(browser, WAIT_TIMEOUT).until(
            EC.url_contains("/view")
        )
        
        assert "/view" in browser.current_url
    
    def test_auction_view_page(self, browser, auction_data, bidder_sessions):
        """Test auction view page"""
        browser.switch_to.window(bidder_sessions[0])
        
        # Navigate to auction view
        browser.get(f"{BASE_URL}/auction/{auction_data['id']}/view")
        
        # Check for current player display
        current_player = WebDriverWait(browser, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".current-player, .player-info"))
        )
        
        assert current_player.is_displayed()
        
        # Check for bid form
        bid_form = browser.find_element(By.CSS_SELECTOR, "form[onsubmit*='bid'], .bid-form")
        assert bid_form.is_displayed()
    
    def test_bid_form_elements(self, browser, auction_data, bidder_sessions):
        """Test bid form elements"""
        browser.switch_to.window(bidder_sessions[0])
        browser.get(f"{BASE_URL}/auction/{auction_data['id']}/view")
        
        # Check bid input
        bid_input = browser.find_element(By.CSS_SELECTOR, "input[name='amount'], #bid-amount")
        assert bid_input.is_displayed()
        
        # Check submit button
        submit_button = browser.find_element(By.CSS_SELECTOR, "button[type='submit']")
        assert submit_button.is_displayed()
    
    def test_error_handling(self, browser):
        """Test error handling"""
        # Test invalid auction ID
        browser.get(f"{BASE_URL}/auction/invalid-id")
        
        # Should redirect to home or show error
        assert browser.current_url == BASE_URL or "404" in browser.page_source
        
        # Test invalid join code
        browser.get(f"{BASE_URL}/join/INVALID1")
        
        # Should redirect or show error
        assert browser.current_url == BASE_URL or "Invalid" in browser.page_source

class TestAuctionResponsive:
    """Responsive design tests"""
    
    def test_mobile_viewport(self, browser, auction_data):
        """Test mobile viewport"""
        browser.set_window_size(375, 667)  # iPhone size
        
        browser.get(f"{BASE_URL}/auction/{auction_data['id']}")
        
        # Check if page is responsive
        body = browser.find_element(By.TAG_NAME, "body")
        assert body.is_displayed()
        
        # Reset to desktop size
        browser.set_window_size(1920, 1080)
    
    def test_tablet_viewport(self, browser, auction_data):
        """Test tablet viewport"""
        browser.set_window_size(768, 1024)  # iPad size
        
        browser.get(f"{BASE_URL}/auction/{auction_data['id']}")
        
        # Check if page is responsive
        body = browser.find_element(By.TAG_NAME, "body")
        assert body.is_displayed()
        
        # Reset to desktop size
        browser.set_window_size(1920, 1080)

# Pytest configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )

# Custom pytest fixtures for reporting
@pytest.fixture(autouse=True)
def log_test_info(request):
    """Log test information"""
    print(f"\n🧪 Running test: {request.node.name}")
    yield
    print(f"✅ Completed test: {request.node.name}")

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"])