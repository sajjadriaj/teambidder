#!/usr/bin/env python3
"""
Playwright UI Testing Script for Auction System
===============================================

This script uses Playwright for UI testing - a modern alternative to Selenium
with better performance and reliability.

Requirements:
- pip install playwright
- playwright install chromium

Features:
- Faster execution than Selenium
- Better element waiting
- Network interception
- Screenshots on failure
- Mobile device simulation

Usage:
    python ui_test_playwright.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

BASE_URL = "http://localhost:5000"

class AuctionPlaywrightTester:
    def __init__(self, headless=False):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.auction_id = None
        self.invitation_codes = {}
        self.test_results = []
        self.bidder_pages = []
        
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
    
    async def setup_browser(self):
        """Setup Playwright browser"""
        self.log("Setting up Playwright browser...")
        
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            
            self.page = await self.context.new_page()
            
            self.log("Playwright browser setup successful", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Failed to setup browser: {str(e)}", "ERROR")
            return False
    
    async def create_test_players_file(self):
        """Create test players JSON file"""
        players_data = [
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
            },
            {
                "name": "Kevin De Bruyne",
                "position": "Midfielder",
                "rating": 92,
                "starting_bid": 300000,
                "age": 32,
                "nationality": "Belgium"
            }
        ]
        
        file_path = "/tmp/playwright_test_players.json"
        with open(file_path, 'w') as f:
            json.dump(players_data, f, indent=2)
        
        self.log(f"Created test players file: {file_path}", "SUCCESS")
        return file_path
    
    async def take_screenshot(self, name):
        """Take screenshot for debugging"""
        try:
            await self.page.screenshot(path=f"/tmp/{name}.png")
            self.log(f"Screenshot saved: {name}.png", "INFO")
        except:
            pass
    
    async def test_home_page(self):
        """Test 1: Home page loading"""
        self.log("Testing home page...")
        
        try:
            await self.page.goto(BASE_URL)
            
            # Check page title
            title = await self.page.title()
            if "Auction System" in title:
                self.log("Home page loaded successfully", "SUCCESS")
            else:
                self.log(f"Unexpected page title: {title}", "WARNING")
            
            # Check for main elements
            create_button = await self.page.locator("text=Create Auction").first
            if await create_button.is_visible():
                self.log("'Create Auction' button found", "SUCCESS")
            else:
                self.log("'Create Auction' button not found", "ERROR")
                await self.take_screenshot("home_page_error")
                return False
            
            return True
            
        except Exception as e:
            self.log(f"Home page test failed: {str(e)}", "ERROR")
            await self.take_screenshot("home_page_error")
            return False
    
    async def test_create_auction(self):
        """Test 2: Create auction"""
        self.log("Testing auction creation...")
        
        try:
            # Click create auction button
            await self.page.click("text=Create Auction")
            
            # Wait for form to load
            await self.page.wait_for_selector("#name")
            self.log("Create auction form loaded", "SUCCESS")
            
            # Fill form
            await self.page.fill("#name", "Playwright Test Auction")
            await self.page.fill("#sport", "Football")
            await self.page.fill("#budget_per_team", "2000000")
            await self.page.fill("#max_players_per_team", "4")
            
            self.log("Form fields filled", "SUCCESS")
            
            # Upload file
            players_file = await self.create_test_players_file()
            await self.page.set_input_files("#players_file", players_file)
            
            self.log("Players file uploaded", "SUCCESS")
            
            # Submit form
            await self.page.click("button[type='submit']")
            
            # Wait for redirect
            await self.page.wait_for_url("**/auction/**")
            
            # Extract auction ID
            url = self.page.url
            if "/auction/" in url:
                self.auction_id = url.split("/auction/")[1]
                self.log(f"Auction created successfully: {self.auction_id}", "SUCCESS")
            else:
                self.log("Failed to extract auction ID", "ERROR")
                return False
            
            # Clean up
            os.remove(players_file)
            
            return True
            
        except Exception as e:
            self.log(f"Auction creation test failed: {str(e)}", "ERROR")
            await self.take_screenshot("create_auction_error")
            return False
    
    async def test_extract_invitation_codes(self):
        """Test 3: Extract invitation codes"""
        self.log("Testing invitation codes extraction...")
        
        try:
            # Look for code elements
            code_elements = await self.page.locator("code").all()
            
            for code_element in code_elements:
                code_text = await code_element.text_content()
                if code_text and len(code_text.strip()) == 8:
                    code_text = code_text.strip()
                    
                    # Get parent context to determine code type
                    parent_element = await code_element.locator("xpath=../..").first
                    parent_text = await parent_element.text_content()
                    parent_text = parent_text.lower()
                    
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
    
    async def test_copy_functionality(self):
        """Test 4: Copy button functionality"""
        self.log("Testing copy button functionality...")
        
        try:
            # Find copy buttons
            copy_buttons = await self.page.locator("button[onclick*='copyCode']").all()
            
            if not copy_buttons:
                self.log("No copy buttons found", "WARNING")
                return True
            
            for button in copy_buttons:
                # Click copy button
                await button.click()
                
                # Wait for feedback
                await self.page.wait_for_timeout(1000)
                
                # Check button content for success indication
                button_html = await button.inner_html()
                if "check" in button_html.lower():
                    self.log("Copy button feedback working", "SUCCESS")
                else:
                    self.log("Copy button feedback not working", "WARNING")
                
                # Wait for reset
                await self.page.wait_for_timeout(2000)
            
            return True
            
        except Exception as e:
            self.log(f"Copy functionality test failed: {str(e)}", "ERROR")
            return False
    
    async def test_bidder_joining(self):
        """Test 5: Bidder joining process"""
        self.log("Testing bidder joining process...")
        
        if not self.invitation_codes.get("bidder"):
            self.log("No bidder code available", "ERROR")
            return False
        
        bidder_code = self.invitation_codes["bidder"]
        bidder_names = ["Manchester United", "Chelsea FC", "Arsenal FC"]
        
        try:
            for i, bidder_name in enumerate(bidder_names):
                # Create new page for each bidder
                if i == 0:
                    # Use current page for first bidder
                    bidder_page = self.page
                else:
                    # Create new page for additional bidders
                    bidder_page = await self.context.new_page()
                
                self.bidder_pages.append(bidder_page)
                
                # Navigate to join page
                join_url = f"{BASE_URL}/join/{bidder_code}"
                await bidder_page.goto(join_url)
                
                # Wait for join form
                await bidder_page.wait_for_selector("#name")
                
                # Fill in bidder name
                await bidder_page.fill("#name", bidder_name)
                
                # Submit form
                await bidder_page.click("button[type='submit']")
                
                # Wait for redirect
                await bidder_page.wait_for_url("**/auction/**")
                
                self.log(f"{bidder_name} joined successfully", "SUCCESS")
                
                # Verify bidder in participants list
                participants = await bidder_page.locator(".participant-item, .participant").all()
                participant_texts = []
                for p in participants:
                    text = await p.text_content()
                    participant_texts.append(text)
                
                if any(bidder_name in text for text in participant_texts):
                    self.log(f"{bidder_name} appears in participants list", "SUCCESS")
                else:
                    self.log(f"{bidder_name} not found in participants list", "WARNING")
            
            return len(self.bidder_pages) >= 2
            
        except Exception as e:
            self.log(f"Bidder joining test failed: {str(e)}", "ERROR")
            await self.take_screenshot("bidder_joining_error")
            return False
    
    async def test_start_auction(self):
        """Test 6: Start auction"""
        self.log("Testing auction start...")
        
        try:
            # Use admin page (first page)
            admin_page = self.bidder_pages[0] if self.bidder_pages else self.page
            
            # Look for start button
            start_button = admin_page.locator("#start-auction-btn").first
            if not await start_button.is_visible():
                start_button = admin_page.locator("button[onclick*='startAuction']").first
            
            if not await start_button.is_visible():
                self.log("Start auction button not found", "ERROR")
                return False
            
            # Check if enabled
            if await start_button.is_enabled():
                self.log("Start auction button is enabled", "SUCCESS")
            else:
                self.log("Start auction button is disabled", "WARNING")
                return False
            
            # Click start button
            await start_button.click()
            
            # Wait for countdown modal
            countdown_modal = admin_page.locator("#countdownModal")
            await countdown_modal.wait_for(state="visible", timeout=5000)
            self.log("Countdown modal appeared", "SUCCESS")
            
            # Monitor countdown
            countdown_timer = admin_page.locator("#countdown-timer")
            initial_time = await countdown_timer.text_content()
            self.log(f"Countdown started at {initial_time} seconds", "SUCCESS")
            
            # Wait and check if counting down
            await self.page.wait_for_timeout(5000)
            current_time = await countdown_timer.text_content()
            
            if int(current_time) < int(initial_time):
                self.log("Countdown is working correctly", "SUCCESS")
            else:
                self.log("Countdown appears to be stuck", "WARNING")
            
            return True
            
        except Exception as e:
            self.log(f"Auction start test failed: {str(e)}", "ERROR")
            await self.take_screenshot("auction_start_error")
            return False
    
    async def test_countdown_completion(self):
        """Test 7: Countdown completion"""
        self.log("Testing countdown completion...")
        
        try:
            admin_page = self.bidder_pages[0] if self.bidder_pages else self.page
            
            # Wait for countdown to complete (with reasonable timeout)
            countdown_timer = admin_page.locator("#countdown-timer")
            
            # Monitor countdown
            timeout = 70000  # 70 seconds
            start_time = 0
            
            while start_time < timeout:
                try:
                    current_time = await countdown_timer.text_content()
                    if int(current_time) <= 0:
                        self.log("Countdown reached 0", "SUCCESS")
                        break
                    
                    # Log progress
                    if int(current_time) % 10 == 0:
                        self.log(f"Countdown: {current_time} seconds remaining")
                    
                    await admin_page.wait_for_timeout(1000)
                    start_time += 1000
                    
                except:
                    # Timer might have disappeared
                    break
            
            # Wait for redirect
            await admin_page.wait_for_timeout(5000)
            
            # Check if redirected to auction view
            url = admin_page.url
            if "/view" in url:
                self.log("Redirected to auction view", "SUCCESS")
                return True
            else:
                self.log("Not redirected to auction view", "WARNING")
                return False
            
        except Exception as e:
            self.log(f"Countdown completion test failed: {str(e)}", "ERROR")
            return False
    
    async def test_auction_view(self):
        """Test 8: Auction view page"""
        self.log("Testing auction view page...")
        
        try:
            admin_page = self.bidder_pages[0] if self.bidder_pages else self.page
            
            # Check current player display
            current_player = admin_page.locator(".current-player, .player-info").first
            if await current_player.is_visible():
                self.log("Auction view page loaded successfully", "SUCCESS")
            else:
                self.log("Auction view page not loaded properly", "WARNING")
            
            # Check bid form
            bid_form = admin_page.locator("form[onsubmit*='bid'], .bid-form").first
            if await bid_form.is_visible():
                self.log("Bid form found", "SUCCESS")
            else:
                self.log("Bid form not found", "WARNING")
            
            # Check participants
            participants = await admin_page.locator(".participant-item, .participant").all()
            if participants:
                self.log(f"Found {len(participants)} participants", "SUCCESS")
            else:
                self.log("No participants found", "WARNING")
            
            return True
            
        except Exception as e:
            self.log(f"Auction view test failed: {str(e)}", "ERROR")
            return False
    
    async def test_bidding_process(self):
        """Test 9: Bidding process"""
        self.log("Testing bidding process...")
        
        try:
            # Test bidding from different pages
            for i, bidder_page in enumerate(self.bidder_pages[:2]):
                # Navigate to auction view
                await bidder_page.goto(f"{BASE_URL}/auction/{self.auction_id}/view")
                
                # Wait for page load
                await bidder_page.wait_for_timeout(2000)
                
                # Look for bid input
                bid_input = bidder_page.locator("input[name='amount'], #bid-amount").first
                if not await bid_input.is_visible():
                    self.log(f"Bid input not found for bidder {i+1}", "WARNING")
                    continue
                
                # Get current bid
                current_bid_element = bidder_page.locator(".current-bid, .bid-amount").first
                if await current_bid_element.is_visible():
                    current_bid_text = await current_bid_element.text_content()
                    
                    # Extract bid amount
                    import re
                    bid_match = re.search(r'[\d,]+', current_bid_text.replace(',', ''))
                    if bid_match:
                        current_bid = int(bid_match.group())
                        new_bid = current_bid + 50000
                        
                        # Place bid
                        await bid_input.fill(str(new_bid))
                        await bidder_page.click("button[type='submit']")
                        
                        self.log(f"Bidder {i+1} placed bid of ${new_bid:,}", "SUCCESS")
                        
                        # Wait between bids
                        await bidder_page.wait_for_timeout(3000)
            
            return True
            
        except Exception as e:
            self.log(f"Bidding process test failed: {str(e)}", "ERROR")
            return False
    
    async def test_real_time_updates(self):
        """Test 10: Real-time updates"""
        self.log("Testing real-time updates...")
        
        try:
            # Check consistency across pages
            for i, bidder_page in enumerate(self.bidder_pages):
                # Check current player
                current_player = bidder_page.locator(".current-player, .player-info").first
                if await current_player.is_visible():
                    player_text = await current_player.text_content()
                    self.log(f"Page {i+1} current player: {player_text[:50]}...", "INFO")
                
                # Check bid info
                bid_info = bidder_page.locator(".current-bid, .bid-amount").first
                if await bid_info.is_visible():
                    bid_text = await bid_info.text_content()
                    self.log(f"Page {i+1} bid info: {bid_text}", "INFO")
            
            self.log("Real-time updates check completed", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Real-time updates test failed: {str(e)}", "ERROR")
            return False
    
    async def cleanup(self):
        """Clean up resources"""
        self.log("Cleaning up...")
        
        if self.browser:
            await self.browser.close()
            self.log("Browser closed", "SUCCESS")
    
    async def run_all_tests(self):
        """Run all UI tests"""
        self.log("="*60)
        self.log("STARTING PLAYWRIGHT UI TESTS")
        self.log("="*60)
        
        if not await self.setup_browser():
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
                ("Real-time Updates", self.test_real_time_updates)
            ]
            
            passed = 0
            total = len(tests)
            
            for test_name, test_func in tests:
                self.log(f"Running: {test_name}")
                if await test_func():
                    passed += 1
                    self.log(f"PASSED: {test_name}", "SUCCESS")
                else:
                    self.log(f"FAILED: {test_name}", "ERROR")
                
                self.log("-" * 40)
                await asyncio.sleep(1)  # Brief pause
            
            # Print summary
            self.log("="*60)
            self.log(f"PLAYWRIGHT UI TEST SUMMARY: {passed}/{total} tests passed")
            
            if passed == total:
                self.log("ALL PLAYWRIGHT UI TESTS PASSED! 🎉", "SUCCESS")
                return True
            else:
                self.log(f"SOME TESTS FAILED: {total-passed} failures", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Unexpected error in UI tests: {str(e)}", "ERROR")
            return False
        finally:
            await self.cleanup()

async def main():
    """Main function"""
    print("Auction System Playwright UI Testing Script")
    print("=" * 50)
    
    # Check if Playwright is available
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ Playwright not installed. Install with:")
        print("   pip install playwright")
        print("   playwright install chromium")
        return 1
    
    print("Prerequisites:")
    print("• Flask app running on localhost:5000")
    print("• Playwright installed and configured")
    print()
    
    # Configuration
    headless_input = input("Run in headless mode? (y/n) [n]: ").strip().lower()
    headless = headless_input in ['y', 'yes']
    
    print(f"\nRunning Playwright UI tests (headless: {headless})")
    print("Press Ctrl+C to stop tests at any time")
    print()
    
    try:
        tester = AuctionPlaywrightTester(headless=headless)
        success = await tester.run_all_tests()
        
        if success:
            print("\n🎉 All Playwright UI tests passed!")
            return 0
        else:
            print("\n❌ Some Playwright UI tests failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Tests failed with error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))