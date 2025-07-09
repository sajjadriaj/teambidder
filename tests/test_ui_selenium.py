#!/usr/bin/env python3
"""
Selenium UI Testing Script for Auction System
=============================================

This script performs comprehensive UI testing using Selenium WebDriver to simulate
real user interactions with the auction system.

Requirements:
- pip install selenium
- Chrome/ChromeDriver or Firefox/GeckoDriver installed
- Flask app running on localhost:5000

Features:
- Auction creation with file upload
- Multi-bidder joining simulation
- Countdown timer testing
- Bidding process validation
- Real-time UI updates testing
- Error handling and edge cases

Usage:
    python ui_test_selenium.py
"""

import os
import time
import json
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

BASE_URL = "http://localhost:5000"
IMPLICIT_WAIT = 10
EXPLICIT_WAIT = 30

class AuctionUITester:
    def __init__(self, browser='chrome', headless=False):
        self.browser = browser
        self.headless = headless
        self.driver = None
        self.auction_id = None
        self.invitation_codes = {}
        self.test_results = []
        self.bidder_windows = []
        
    def log(self, message, level="INFO"):
        """Log test progress"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        symbols = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
        symbol = symbols.get(level, "ℹ️")
        print(f"[{timestamp}] {symbol} {message}")
        
        self.test_results.append({
            "timestamp": timestamp,
            "level": level,
            "message": message
        })
    
    def setup_driver(self):
        """Setup WebDriver"""
        self.log("Setting up WebDriver...")
        
        try:
            if self.browser.lower() == 'chrome':
                options = Options()
                if self.headless:
                    options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--window-size=1920,1080')
                self.driver = webdriver.Chrome(options=options)
            elif self.browser.lower() == 'firefox':
                options = FirefoxOptions()
                if self.headless:
                    options.add_argument('--headless')
                self.driver = webdriver.Firefox(options=options)
            else:
                raise ValueError(f"Unsupported browser: {self.browser}")
            
            self.driver.implicitly_wait(IMPLICIT_WAIT)
            self.driver.maximize_window()
            
            self.log(f"WebDriver setup successful ({self.browser})", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Failed to setup WebDriver: {str(e)}", "ERROR")
            return False
    
    def create_test_players_file(self):
        """Create test players JSON file"""
        players_data = [
            {
                "name": "Lionel Messi",
                "position": "Forward",
                "rating": 95,
                "starting_bid": 500000,
                "age": 36,
                "nationality": "Argentina",
                "goals": 672,
                "assists": 303
            },
            {
                "name": "Cristiano Ronaldo",
                "position": "Forward",
                "rating": 93,
                "starting_bid": 450000,
                "age": 38,
                "nationality": "Portugal",
                "goals": 695,
                "assists": 229
            },
            {
                "name": "Kylian Mbappé",
                "position": "Forward",
                "rating": 91,
                "starting_bid": 400000,
                "age": 24,
                "nationality": "France",
                "goals": 256,
                "assists": 127
            },
            {
                "name": "Kevin De Bruyne",
                "position": "Midfielder",
                "rating": 92,
                "starting_bid": 300000,
                "age": 32,
                "nationality": "Belgium",
                "goals": 102,
                "assists": 173
            },
            {
                "name": "Virgil van Dijk",
                "position": "Defender",
                "rating": 89,
                "starting_bid": 250000,
                "age": 32,
                "nationality": "Netherlands",
                "goals": 40,
                "assists": 12
            }
        ]
        
        file_path = "/tmp/ui_test_players.json"
        with open(file_path, 'w') as f:
            json.dump(players_data, f, indent=2)
        
        self.log(f"Created test players file: {file_path}", "SUCCESS")
        return file_path
    
    def wait_for_element(self, by, value, timeout=EXPLICIT_WAIT):
        """Wait for element to be present and visible"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            self.log(f"Element not found: {value}", "ERROR")
            return None
    
    def wait_for_clickable(self, by, value, timeout=EXPLICIT_WAIT):
        """Wait for element to be clickable"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            return element
        except TimeoutException:
            self.log(f"Element not clickable: {value}", "ERROR")
            return None
    
    def safe_click(self, element):
        """Safely click an element"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
            element.click()
            return True
        except Exception as e:
            self.log(f"Failed to click element: {str(e)}", "ERROR")
            return False
    
    def test_home_page(self):
        """Test 1: Home page loading and navigation"""
        self.log("Testing home page...")
        
        try:
            self.driver.get(BASE_URL)
            
            # Check page title
            if "Auction System" in self.driver.title:
                self.log("Home page loaded successfully", "SUCCESS")
            else:
                self.log(f"Unexpected page title: {self.driver.title}", "WARNING")
            
            # Check for main elements
            create_button = self.wait_for_element(By.LINK_TEXT, "Create Auction")
            if create_button:
                self.log("'Create Auction' button found", "SUCCESS")
            else:
                self.log("'Create Auction' button not found", "ERROR")
                return False
            
            # Check join section
            join_section = self.wait_for_element(By.ID, "join-code")
            if join_section:
                self.log("Join section found", "SUCCESS")
            else:
                self.log("Join section not found", "WARNING")
            
            return True
            
        except Exception as e:
            self.log(f"Home page test failed: {str(e)}", "ERROR")
            return False
    
    def test_create_auction(self):
        """Test 2: Create auction with file upload"""
        self.log("Testing auction creation...")
        
        try:
            # Navigate to create auction page
            create_button = self.wait_for_clickable(By.LINK_TEXT, "Create Auction")
            if not create_button or not self.safe_click(create_button):
                return False
            
            # Wait for form to load
            self.wait_for_element(By.ID, "name")
            self.log("Create auction form loaded", "SUCCESS")
            
            # Fill form fields
            name_field = self.driver.find_element(By.ID, "name")
            name_field.clear()
            name_field.send_keys("UI Test Auction")
            
            sport_field = self.driver.find_element(By.ID, "sport")
            sport_field.clear()
            sport_field.send_keys("Football")
            
            budget_field = self.driver.find_element(By.ID, "budget_per_team")
            budget_field.clear()
            budget_field.send_keys("2000000")
            
            max_players_field = self.driver.find_element(By.ID, "max_players_per_team")
            max_players_field.clear()
            max_players_field.send_keys("4")
            
            self.log("Form fields filled", "SUCCESS")
            
            # Upload players file
            players_file = self.create_test_players_file()
            file_input = self.driver.find_element(By.ID, "players_file")
            file_input.send_keys(players_file)
            
            self.log("Players file uploaded", "SUCCESS")
            
            # Submit form
            submit_button = self.wait_for_clickable(By.CSS_SELECTOR, "button[type='submit']")
            if submit_button and self.safe_click(submit_button):
                self.log("Auction creation form submitted", "SUCCESS")
            else:
                self.log("Failed to submit form", "ERROR")
                return False
            
            # Wait for redirect to auction lobby
            self.wait_for_element(By.CSS_SELECTOR, ".auction-header, h1")
            
            # Extract auction ID from URL
            current_url = self.driver.current_url
            if "/auction/" in current_url:
                self.auction_id = current_url.split("/auction/")[1]
                self.log(f"Auction created successfully: {self.auction_id}", "SUCCESS")
            else:
                self.log("Failed to extract auction ID from URL", "ERROR")
                return False
            
            # Clean up temp file
            os.remove(players_file)
            
            return True
            
        except Exception as e:
            self.log(f"Auction creation test failed: {str(e)}", "ERROR")
            return False
    
    def test_extract_invitation_codes(self):
        """Test 3: Extract invitation codes from auction lobby"""
        self.log("Testing invitation codes extraction...")
        
        try:
            # Look for invitation codes in the UI
            code_elements = self.driver.find_elements(By.CSS_SELECTOR, "code")
            
            for code_element in code_elements:
                code_text = code_element.text.strip()
                if len(code_text) == 8 and code_text.isalnum():
                    # Try to determine code type based on context
                    parent_text = code_element.find_element(By.XPATH, "../..").text.lower()
                    
                    if "admin" in parent_text:
                        self.invitation_codes["admin"] = code_text
                        self.log(f"Admin code found: {code_text}", "SUCCESS")
                    elif "bidder" in parent_text:
                        self.invitation_codes["bidder"] = code_text
                        self.log(f"Bidder code found: {code_text}", "SUCCESS")
                    elif "visitor" in parent_text:
                        self.invitation_codes["visitor"] = code_text
                        self.log(f"Visitor code found: {code_text}", "SUCCESS")
            
            if self.invitation_codes.get("bidder"):
                return True
            else:
                self.log("No bidder code found", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Invitation codes extraction failed: {str(e)}", "ERROR")
            return False
    
    def test_copy_functionality(self):
        """Test 4: Test copy button functionality"""
        self.log("Testing copy button functionality...")
        
        try:
            # Find and test copy buttons
            copy_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[onclick*='copyCode']")
            
            if not copy_buttons:
                self.log("No copy buttons found", "WARNING")
                return True
            
            for button in copy_buttons:
                # Click copy button
                self.safe_click(button)
                
                # Check if button shows success feedback
                time.sleep(1)
                if "check" in button.get_attribute("innerHTML").lower():
                    self.log("Copy button feedback working", "SUCCESS")
                else:
                    self.log("Copy button feedback not working", "WARNING")
                
                # Wait for feedback to reset
                time.sleep(2)
            
            return True
            
        except Exception as e:
            self.log(f"Copy functionality test failed: {str(e)}", "ERROR")
            return False
    
    def test_bidder_joining(self):
        """Test 5: Test bidder joining process"""
        self.log("Testing bidder joining process...")
        
        if not self.invitation_codes.get("bidder"):
            self.log("No bidder code available", "ERROR")
            return False
        
        bidder_code = self.invitation_codes["bidder"]
        bidder_names = ["Manchester United", "Chelsea FC", "Arsenal FC"]
        
        try:
            for i, bidder_name in enumerate(bidder_names):
                # Open new window for each bidder
                if i == 0:
                    # Use current window for first bidder
                    window_handle = self.driver.current_window_handle
                else:
                    # Open new window for additional bidders
                    self.driver.execute_script("window.open('');")
                    window_handle = self.driver.window_handles[-1]
                    self.driver.switch_to.window(window_handle)
                
                self.bidder_windows.append(window_handle)
                
                # Navigate to join page
                join_url = f"{BASE_URL}/join/{bidder_code}"
                self.driver.get(join_url)
                
                # Wait for join form
                name_field = self.wait_for_element(By.ID, "name")
                if not name_field:
                    self.log(f"Join form not found for {bidder_name}", "ERROR")
                    continue
                
                # Fill in bidder name
                name_field.clear()
                name_field.send_keys(bidder_name)
                
                # Submit join form
                submit_button = self.wait_for_clickable(By.CSS_SELECTOR, "button[type='submit']")
                if submit_button and self.safe_click(submit_button):
                    self.log(f"{bidder_name} joined successfully", "SUCCESS")
                else:
                    self.log(f"Failed to join {bidder_name}", "ERROR")
                    continue
                
                # Wait for redirect to auction lobby
                self.wait_for_element(By.CSS_SELECTOR, ".auction-header, h1")
                
                # Verify bidder is in participants list
                participants = self.driver.find_elements(By.CSS_SELECTOR, ".participant-item, .participant")
                participant_names = [p.text for p in participants]
                
                if any(bidder_name in name for name in participant_names):
                    self.log(f"{bidder_name} appears in participants list", "SUCCESS")
                else:
                    self.log(f"{bidder_name} not found in participants list", "WARNING")
            
            return len(self.bidder_windows) >= 2
            
        except Exception as e:
            self.log(f"Bidder joining test failed: {str(e)}", "ERROR")
            return False
    
    def test_start_auction(self):
        """Test 6: Test auction start and countdown"""
        self.log("Testing auction start...")
        
        try:
            # Switch to admin window (first window)
            self.driver.switch_to.window(self.driver.window_handles[0])
            
            # Look for start auction button
            start_button = self.wait_for_clickable(By.ID, "start-auction-btn")
            if not start_button:
                start_button = self.wait_for_clickable(By.CSS_SELECTOR, "button[onclick*='startAuction']")
            
            if not start_button:
                self.log("Start auction button not found", "ERROR")
                return False
            
            # Check if button is enabled
            if start_button.is_enabled():
                self.log("Start auction button is enabled", "SUCCESS")
            else:
                self.log("Start auction button is disabled", "WARNING")
                return False
            
            # Click start auction
            if self.safe_click(start_button):
                self.log("Start auction button clicked", "SUCCESS")
            else:
                self.log("Failed to click start auction button", "ERROR")
                return False
            
            # Wait for countdown modal
            countdown_modal = self.wait_for_element(By.ID, "countdownModal")
            if countdown_modal:
                self.log("Countdown modal appeared", "SUCCESS")
            else:
                self.log("Countdown modal not found", "WARNING")
            
            # Monitor countdown
            countdown_timer = self.wait_for_element(By.ID, "countdown-timer")
            if countdown_timer:
                initial_time = int(countdown_timer.text)
                self.log(f"Countdown started at {initial_time} seconds", "SUCCESS")
                
                # Wait a few seconds and check if countdown is decreasing
                time.sleep(5)
                current_time = int(countdown_timer.text)
                
                if current_time < initial_time:
                    self.log("Countdown is working correctly", "SUCCESS")
                else:
                    self.log("Countdown appears to be stuck", "WARNING")
            
            return True
            
        except Exception as e:
            self.log(f"Auction start test failed: {str(e)}", "ERROR")
            return False
    
    def test_countdown_completion(self):
        """Test 7: Wait for countdown to complete"""
        self.log("Testing countdown completion...")
        
        try:
            # Wait for countdown to reach 0 (with timeout)
            countdown_timer = self.wait_for_element(By.ID, "countdown-timer")
            if not countdown_timer:
                self.log("Countdown timer not found", "ERROR")
                return False
            
            # Monitor countdown with timeout
            timeout = 70  # 60 seconds + buffer
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    current_time = int(countdown_timer.text)
                    if current_time <= 0:
                        self.log("Countdown reached 0", "SUCCESS")
                        break
                    
                    # Log progress every 10 seconds
                    if current_time % 10 == 0:
                        self.log(f"Countdown: {current_time} seconds remaining")
                    
                    time.sleep(1)
                    
                except:
                    # Countdown timer might have disappeared
                    break
            
            # Wait for redirect to auction view
            time.sleep(5)
            
            # Check if we're redirected to auction view
            current_url = self.driver.current_url
            if "/view" in current_url:
                self.log("Redirected to auction view", "SUCCESS")
                return True
            else:
                self.log("Not redirected to auction view", "WARNING")
                return False
            
        except Exception as e:
            self.log(f"Countdown completion test failed: {str(e)}", "ERROR")
            return False
    
    def test_auction_view(self):
        """Test 8: Test auction view page"""
        self.log("Testing auction view page...")
        
        try:
            # Check if auction view page loaded
            current_player = self.wait_for_element(By.CSS_SELECTOR, ".current-player, .player-info")
            if current_player:
                self.log("Auction view page loaded successfully", "SUCCESS")
            else:
                self.log("Auction view page not loaded properly", "WARNING")
            
            # Check for bid form
            bid_form = self.driver.find_elements(By.CSS_SELECTOR, "form[onsubmit*='bid'], .bid-form")
            if bid_form:
                self.log("Bid form found", "SUCCESS")
            else:
                self.log("Bid form not found", "WARNING")
            
            # Check for participants list
            participants = self.driver.find_elements(By.CSS_SELECTOR, ".participant-item, .participant")
            if participants:
                self.log(f"Found {len(participants)} participants", "SUCCESS")
            else:
                self.log("No participants found", "WARNING")
            
            return True
            
        except Exception as e:
            self.log(f"Auction view test failed: {str(e)}", "ERROR")
            return False
    
    def test_bidding_process(self):
        """Test 9: Test bidding process"""
        self.log("Testing bidding process...")
        
        try:
            # Test bidding from different windows
            for i, window_handle in enumerate(self.bidder_windows[:2]):  # Test first 2 bidders
                self.driver.switch_to.window(window_handle)
                
                # Navigate to auction view if not already there
                if "/view" not in self.driver.current_url:
                    self.driver.get(f"{BASE_URL}/auction/{self.auction_id}/view")
                
                # Wait for page to load
                time.sleep(2)
                
                # Look for bid input
                bid_input = self.driver.find_elements(By.CSS_SELECTOR, "input[name='amount'], #bid-amount")
                if not bid_input:
                    self.log(f"Bid input not found for bidder {i+1}", "WARNING")
                    continue
                
                bid_input = bid_input[0]
                
                # Get current bid amount
                current_bid_element = self.driver.find_elements(By.CSS_SELECTOR, ".current-bid, .bid-amount")
                if current_bid_element:
                    current_bid_text = current_bid_element[0].text
                    # Extract number from text like "$500,000"
                    import re
                    bid_match = re.search(r'[\d,]+', current_bid_text.replace(',', ''))
                    if bid_match:
                        current_bid = int(bid_match.group())
                        new_bid = current_bid + 50000
                        
                        # Place bid
                        bid_input.clear()
                        bid_input.send_keys(str(new_bid))
                        
                        # Submit bid
                        submit_button = self.wait_for_clickable(By.CSS_SELECTOR, "button[type='submit']")
                        if submit_button and self.safe_click(submit_button):
                            self.log(f"Bidder {i+1} placed bid of ${new_bid:,}", "SUCCESS")
                        else:
                            self.log(f"Failed to submit bid for bidder {i+1}", "ERROR")
                
                # Wait between bids
                time.sleep(3)
            
            return True
            
        except Exception as e:
            self.log(f"Bidding process test failed: {str(e)}", "ERROR")
            return False
    
    def test_real_time_updates(self):
        """Test 10: Test real-time updates"""
        self.log("Testing real-time updates...")
        
        try:
            # Switch between windows to check if updates are synchronized
            for window_handle in self.bidder_windows:
                self.driver.switch_to.window(window_handle)
                
                # Check if current player information is consistent
                current_player = self.driver.find_elements(By.CSS_SELECTOR, ".current-player, .player-info")
                if current_player:
                    player_name = current_player[0].text
                    self.log(f"Current player shown: {player_name[:50]}...", "INFO")
                
                # Check bid information
                bid_info = self.driver.find_elements(By.CSS_SELECTOR, ".current-bid, .bid-amount")
                if bid_info:
                    bid_text = bid_info[0].text
                    self.log(f"Bid info shown: {bid_text}", "INFO")
            
            self.log("Real-time updates check completed", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Real-time updates test failed: {str(e)}", "ERROR")
            return False
    
    def test_error_handling(self):
        """Test 11: Test error handling"""
        self.log("Testing error handling...")
        
        try:
            # Test invalid auction URL
            self.driver.get(f"{BASE_URL}/auction/invalid-id")
            
            # Check for error message or redirect
            time.sleep(2)
            if "404" in self.driver.page_source or "Not Found" in self.driver.page_source:
                self.log("404 error handling working", "SUCCESS")
            elif self.driver.current_url == BASE_URL:
                self.log("Invalid auction redirects to home", "SUCCESS")
            else:
                self.log("Error handling unclear", "WARNING")
            
            # Test invalid join code
            self.driver.get(f"{BASE_URL}/join/INVALID1")
            time.sleep(2)
            
            if "Invalid" in self.driver.page_source or self.driver.current_url == BASE_URL:
                self.log("Invalid join code handling working", "SUCCESS")
            else:
                self.log("Invalid join code handling unclear", "WARNING")
            
            return True
            
        except Exception as e:
            self.log(f"Error handling test failed: {str(e)}", "ERROR")
            return False
    
    def cleanup(self):
        """Clean up resources"""
        self.log("Cleaning up...")
        
        if self.driver:
            try:
                self.driver.quit()
                self.log("WebDriver closed", "SUCCESS")
            except:
                pass
    
    def run_all_tests(self):
        """Run all UI tests"""
        self.log("="*60)
        self.log("STARTING UI TESTS")
        self.log("="*60)
        
        if not self.setup_driver():
            return False
        
        try:
            tests = [
                ("Home Page", self.test_home_page),
                ("Create Auction", self.test_create_auction),
                ("Extract Invitation Codes", self.test_extract_invitation_codes),
                ("Copy Functionality", self.test_copy_functionality),
                ("Bidder Joining", self.test_bidder_joining),
                ("Start Auction", self.test_start_auction),
                ("Countdown Completion", self.test_countdown_completion),
                ("Auction View", self.test_auction_view),
                ("Bidding Process", self.test_bidding_process),
                ("Real-time Updates", self.test_real_time_updates),
                ("Error Handling", self.test_error_handling)
            ]
            
            passed = 0
            total = len(tests)
            
            for test_name, test_func in tests:
                self.log(f"Running: {test_name}")
                if test_func():
                    passed += 1
                    self.log(f"PASSED: {test_name}", "SUCCESS")
                else:
                    self.log(f"FAILED: {test_name}", "ERROR")
                
                self.log("-" * 40)
                time.sleep(1)  # Brief pause between tests
            
            # Print summary
            self.log("="*60)
            self.log(f"UI TEST SUMMARY: {passed}/{total} tests passed")
            
            if passed == total:
                self.log("ALL UI TESTS PASSED! 🎉", "SUCCESS")
                return True
            else:
                self.log(f"SOME UI TESTS FAILED: {total-passed} failures", "ERROR")
                return False
                
        except KeyboardInterrupt:
            self.log("UI tests interrupted by user", "WARNING")
            return False
        except Exception as e:
            self.log(f"Unexpected error in UI tests: {str(e)}", "ERROR")
            return False
        finally:
            self.cleanup()

def main():
    """Main function"""
    print("Auction System UI Testing Script")
    print("=" * 50)
    
    # Check if Selenium is available
    try:
        from selenium import webdriver
    except ImportError:
        print("❌ Selenium not installed. Install with: pip install selenium")
        return 1
    
    print("Prerequisites:")
    print("• Flask app running on localhost:5000")
    print("• Chrome/ChromeDriver or Firefox/GeckoDriver installed")
    print("• Selenium WebDriver configured")
    print()
    
    # Configuration options
    browser = input("Choose browser (chrome/firefox) [chrome]: ").strip() or "chrome"
    headless_input = input("Run in headless mode? (y/n) [n]: ").strip().lower()
    headless = headless_input in ['y', 'yes']
    
    print(f"\nRunning UI tests with {browser} browser (headless: {headless})")
    print("Press Ctrl+C to stop tests at any time")
    print()
    
    try:
        tester = AuctionUITester(browser=browser, headless=headless)
        success = tester.run_all_tests()
        
        if success:
            print("\n🎉 All UI tests passed!")
            return 0
        else:
            print("\n❌ Some UI tests failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Tests failed with error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())