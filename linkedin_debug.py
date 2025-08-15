#!/usr/bin/env python3
"""
LinkedIn API Debug Script

This script helps diagnose and fix LinkedIn API connection issues.
Run this script to test your LinkedIn API configuration and get helpful debugging information.

Usage:
    python linkedin_debug.py

Make sure you have set the following environment variables:
- LINKEDIN_ACCESS_TOKEN: Your LinkedIn access token
- LINKEDIN_PERSON_URN: Your LinkedIn person or organization URN
"""

import os
import asyncio
import aiohttp
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LinkedInDebugger:
    def __init__(self):
        self.token = os.getenv('LINKEDIN_ACCESS_TOKEN')
        self.urn = os.getenv('LINKEDIN_PERSON_URN')
        
    def format_urn(self, urn: str) -> str:
        """Format and validate LinkedIn URN"""
        if not urn:
            raise ValueError("LinkedIn URN cannot be empty")
        
        urn = urn.strip()
        
        # Handle current v2 API formats
        if urn.startswith('urn:li:member:') or urn.startswith('urn:li:company:'):
            return urn
        
        # Convert legacy person format to member format
        if urn.startswith('urn:li:person:'):
            print("💡 Converting legacy 'urn:li:person:' to 'urn:li:member:' format")
            return urn.replace('urn:li:person:', 'urn:li:member:')
        
        # Convert legacy organization format to company format  
        if urn.startswith('urn:li:organization:'):
            print("💡 Converting legacy 'urn:li:organization:' to 'urn:li:company:' format")
            return urn.replace('urn:li:organization:', 'urn:li:company:')
        
        # Handle common typos
        if 'urn:li:organisation:' in urn:
            print("💡 Found 'urn:li:organisation:' - correcting to 'urn:li:company:'")
            return urn.replace('urn:li:organisation:', 'urn:li:company:')
        
        if not urn.startswith('urn:li:'):
            logger.warning(f"URN '{urn}' doesn't start with 'urn:li:', assuming it's a member ID")
            return f"urn:li:member:{urn}"
        
        return urn

    async def test_token_validity(self):
        """Test if the LinkedIn token is valid"""
        print("\n🔍 Testing LinkedIn Token Validity...")
        
        if not self.token:
            print("❌ LINKEDIN_ACCESS_TOKEN not found in environment variables")
            return False
            
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get('https://api.linkedin.com/v2/people/(id~)', headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        name = data.get('firstName', {}).get('localized', {}).get('en_US', 'Unknown')
                        print(f"✅ Token is valid! Connected as: {name}")
                        return True
                    elif response.status == 401:
                        print("❌ Token is invalid or expired")
                        return False
                    elif response.status == 403:
                        text = await response.text()
                        print(f"❌ Access denied (403): {text}")
                        return False
                    else:
                        text = await response.text()
                        print(f"❌ Unexpected error ({response.status}): {text}")
                        return False
            except Exception as e:
                print(f"❌ Connection error: {e}")
                return False

    async def test_urn_format(self):
        """Test and validate URN format"""
        print("\n🔍 Testing LinkedIn URN Format...")
        
        if not self.urn:
            print("❌ LINKEDIN_PERSON_URN not found in environment variables")
            print("💡 Set LINKEDIN_PERSON_URN to your member URN (e.g., 'urn:li:member:XXXXXXXXX')")
            print("💡 Or company URN (e.g., 'urn:li:company:XXXXXXX')")
            print("💡 Legacy formats (urn:li:person:, urn:li:organization:) are automatically converted")
            return None
            
        try:
            formatted_urn = self.format_urn(self.urn)
            print(f"✅ URN format looks good: {formatted_urn}")
            
            if formatted_urn != self.urn:
                print(f"💡 Recommended: Update your LINKEDIN_PERSON_URN to: {formatted_urn}")
                
            return formatted_urn
        except ValueError as e:
            print(f"❌ URN format error: {e}")
            return None

    async def test_posting_permissions(self):
        """Test if the token has posting permissions"""
        print("\n🔍 Testing LinkedIn Posting Permissions...")
        
        if not self.token:
            return False
            
        # Try to create a minimal test post (we'll delete it if successful)
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }
        
        formatted_urn = self.format_urn(self.urn) if self.urn else None
        if not formatted_urn:
            print("❌ Cannot test posting without valid URN")
            return False
            
                 test_content = "🤖 LinkedIn API connection test - this post can be deleted"
         payload = {
             "author": formatted_urn,
             "lifecycleState": "PUBLISHED",
             "specificContent": {
                 "com.linkedin.ugc.ShareContent": {
                     "shareCommentary": {"text": test_content},
                     "shareMediaCategory": "NONE"
                 }
             },
             "visibility": {
                 "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
             }
         }
         
         print(f"Test content length: {len(test_content)} characters")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post('https://api.linkedin.com/v2/ugcPosts', 
                                       headers=headers, json=payload) as response:
                    response_text = await response.text()
                    
                    if response.status == 201:
                        result = await response.json()
                        post_id = result.get('id')
                        print(f"✅ Posting permissions work! Test post created: {post_id}")
                        print("💡 You can delete this test post from LinkedIn if needed")
                        return True
                    elif response.status == 403:
                        print(f"❌ Posting permission denied (403): {response_text}")
                        try:
                            error_data = json.loads(response_text)
                            service_code = error_data.get('serviceErrorCode', 'Unknown')
                            message = error_data.get('message', 'Unknown error')
                            print(f"   Service Error Code: {service_code}")
                            print(f"   Message: {message}")
                            
                            if 'author' in message.lower():
                                print("💡 The issue is with the author field (URN format)")
                            elif 'access_denied' in message.lower():
                                print("💡 Check that your LinkedIn app has 'w_member_social' or 'w_organization_social' permissions")
                        except:
                            pass
                        return False
                    else:
                        print(f"❌ Posting failed ({response.status}): {response_text}")
                        return False
            except Exception as e:
                print(f"❌ Connection error during posting test: {e}")
                return False

    def print_setup_instructions(self):
        """Print setup instructions"""
        print("\n📋 LinkedIn API Setup Instructions:")
        print("1. Go to https://www.linkedin.com/developers/")
        print("2. Create a LinkedIn app or use an existing one")
        print("3. Add the following products to your app:")
        print("   - Sign In with LinkedIn")
        print("   - Share on LinkedIn")
        print("4. In your app settings, note down:")
        print("   - Client ID")
        print("   - Client Secret")
        print("5. Generate an access token with the following scopes:")
        print("   - r_liteprofile (or r_basicprofile)")
        print("   - w_member_social (for personal posts)")
        print("   - OR w_organization_social (for organization posts)")
        print("6. Get your person URN by calling: https://api.linkedin.com/v2/people/(id~)")
        print("   - The 'id' field will contain your person URN")
        print("7. Set environment variables:")
        print("   - LINKEDIN_ACCESS_TOKEN=your_access_token")
        print("   - LINKEDIN_PERSON_URN=urn:li:member:XXXXXXXXX")
        print("   - (Legacy urn:li:person: format is automatically converted)")
        
    async def run_all_tests(self):
        """Run all diagnostic tests"""
        print("🚀 LinkedIn API Diagnostic Tool")
        print("=" * 40)
        
        # Test 1: Token validity
        token_valid = await self.test_token_validity()
        
        # Test 2: URN format
        urn_valid = await self.test_urn_format()
        
        # Test 3: Posting permissions (only if token and URN are valid)
        posting_works = False
        if token_valid and urn_valid:
            posting_works = await self.test_posting_permissions()
        
        # Summary
        print("\n📊 Diagnostic Summary:")
        print(f"Token Valid: {'✅' if token_valid else '❌'}")
        print(f"URN Valid: {'✅' if urn_valid else '❌'}")
        print(f"Posting Works: {'✅' if posting_works else '❌'}")
        
        if not (token_valid and urn_valid and posting_works):
            self.print_setup_instructions()
        else:
            print("\n🎉 All tests passed! Your LinkedIn API is configured correctly.")

async def main():
    debugger = LinkedInDebugger()
    await debugger.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())