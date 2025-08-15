#!/usr/bin/env python3
"""
LinkedIn Personal URN Retrieval Script

This script helps you get your LinkedIn personal URN using your access token.
You have the right scopes (w_member_social, profile, openid, email) to retrieve this information.

Usage:
    python get_linkedin_urn.py

Required environment variables:
- LINKEDIN_ACCESS_TOKEN: Your LinkedIn access token
"""

import os
import asyncio
import aiohttp
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def get_personal_urn():
    """Get your LinkedIn personal URN using your access token"""
    
    access_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
    if not access_token:
        print("❌ LINKEDIN_ACCESS_TOKEN not found in environment variables")
        print("💡 Make sure to set your LinkedIn access token in .env file or environment")
        return None
    
    print("🔍 Retrieving your LinkedIn personal URN...")
    print(f"✅ Found access token: {access_token[:10]}...")
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            # Method 1: Get profile info using /v2/people/(id~)
            print("\n📋 Method 1: Using /v2/people/(id~) endpoint...")
            async with session.get('https://api.linkedin.com/v2/people/(id~)', headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    personal_urn = data.get('id')
                    
                    # Extract name info
                    first_name = data.get('firstName', {}).get('localized', {}).get('en_US', 'Unknown')
                    last_name = data.get('lastName', {}).get('localized', {}).get('en_US', 'Unknown')
                    
                    print(f"✅ Success! Found your profile:")
                    print(f"   Name: {first_name} {last_name}")
                    print(f"   Personal URN: {personal_urn}")
                    
                    # Convert to new format if needed
                    if personal_urn and personal_urn.startswith('urn:li:person:'):
                        new_urn = personal_urn.replace('urn:li:person:', 'urn:li:member:')
                        print(f"   Updated URN format: {new_urn}")
                        print(f"\n🎯 Set this in your environment:")
                        print(f"   LINKEDIN_PERSON_URN={new_urn}")
                        return new_urn
                    elif personal_urn and personal_urn.startswith('urn:li:member:'):
                        print(f"\n🎯 Set this in your environment:")
                        print(f"   LINKEDIN_PERSON_URN={personal_urn}")
                        return personal_urn
                    else:
                        print(f"⚠️  Unexpected URN format: {personal_urn}")
                        return personal_urn
                        
                elif response.status == 401:
                    print("❌ Access token is invalid or expired")
                    print("💡 Generate a new access token from your LinkedIn app")
                    return None
                elif response.status == 403:
                    text = await response.text()
                    print(f"❌ Access denied (403): {text}")
                    print("💡 Check that your LinkedIn app has the 'profile' or 'r_liteprofile' permission")
                    return None
                else:
                    text = await response.text()
                    print(f"❌ Error {response.status}: {text}")
                    return None
                    
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return None
    
    # Method 2: Alternative using userinfo endpoint (if available with openid scope)
    print("\n📋 Method 2: Using /v2/userinfo endpoint (alternative)...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('https://api.linkedin.com/v2/userinfo', headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ UserInfo data: {json.dumps(data, indent=2)}")
                    # This endpoint might not have the URN, but provides additional info
                else:
                    text = await response.text()
                    print(f"ℹ️  UserInfo endpoint returned {response.status}: {text}")
        except Exception as e:
            print(f"ℹ️  UserInfo endpoint error (this is optional): {e}")

def print_setup_guide():
    """Print a guide for setting up the URN"""
    print("\n" + "="*60)
    print("📖 SETUP GUIDE")
    print("="*60)
    print("\n1. 🎯 Copy the URN from above")
    print("2. 📝 Add it to your .env file:")
    print("   LINKEDIN_PERSON_URN=urn:li:member:XXXXXXXXX")
    print("\n3. 🔄 Or set it as an environment variable:")
    print("   export LINKEDIN_PERSON_URN=urn:li:member:XXXXXXXXX")
    print("\n4. ✅ Test your setup:")
    print("   python linkedin_debug.py")
    print("   # OR")
    print("   curl http://localhost:5000/test_linkedin_connection")
    print("\n5. 🚀 Try posting to LinkedIn again!")
    
    print("\n" + "="*60)
    print("📋 YOUR CURRENT SCOPES (✅ = Good for posting)")
    print("="*60)
    print("✅ openid - Use your name and photo")
    print("✅ profile - Use your name and photo") 
    print("✅ w_member_social - Create, modify, delete posts/comments/reactions")
    print("✅ email - Access email address")
    print("\n🎉 You have all the right permissions for LinkedIn posting!")

async def main():
    print("🚀 LinkedIn Personal URN Retrieval Tool")
    print("="*50)
    
    urn = await get_personal_urn()
    
    if urn:
        print_setup_guide()
    else:
        print("\n❌ Could not retrieve your LinkedIn URN")
        print("\n🔧 Troubleshooting steps:")
        print("1. Check that LINKEDIN_ACCESS_TOKEN is set correctly")
        print("2. Verify your access token hasn't expired")
        print("3. Ensure your LinkedIn app has the required permissions")
        print("4. Try generating a new access token if needed")

if __name__ == "__main__":
    asyncio.run(main())