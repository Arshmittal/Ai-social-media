#!/usr/bin/env python3
"""
Simple LinkedIn URN Retrieval Script

This script uses the most reliable LinkedIn API endpoint to get your personal URN.

Usage:
    python get_linkedin_urn_simple.py

Required environment variables:
- LINKEDIN_ACCESS_TOKEN: Your LinkedIn access token
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_linkedin_urn():
    """Get LinkedIn URN using the most reliable method"""
    
    access_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
    if not access_token:
        print("❌ LINKEDIN_ACCESS_TOKEN not found in environment variables")
        return None
    
    print("🔍 Getting your LinkedIn URN...")
    print(f"✅ Using access token: {access_token[:10]}...")
    
    # Try multiple endpoint formats
    endpoints = [
        'https://api.linkedin.com/v2/me',
        'https://api.linkedin.com/v2/people/~',
        'https://api.linkedin.com/v2/userinfo'
    ]
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    for i, endpoint in enumerate(endpoints, 1):
        print(f"\n📋 Method {i}: Trying {endpoint}")
        
        try:
            response = requests.get(endpoint, headers=headers)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success! Response: {json.dumps(data, indent=2)}")
                
                # Look for URN in different fields
                personal_urn = None
                
                # Check 'id' field (most common)
                if 'id' in data:
                    personal_urn = data['id']
                    print(f"Found URN in 'id' field: {personal_urn}")
                
                # Check 'sub' field (userinfo endpoint)
                elif 'sub' in data:
                    sub_value = data['sub']
                    if sub_value.startswith('urn:li:'):
                        personal_urn = sub_value
                    else:
                        personal_urn = f"urn:li:member:{sub_value}"
                    print(f"Found URN in 'sub' field: {personal_urn}")
                
                if personal_urn:
                    # Convert to new format if needed
                    if personal_urn.startswith('urn:li:person:'):
                        new_urn = personal_urn.replace('urn:li:person:', 'urn:li:member:')
                        print(f"🔄 Converting to new format: {new_urn}")
                        personal_urn = new_urn
                    
                    print(f"\n🎯 Your LinkedIn URN: {personal_urn}")
                    print(f"\n📝 Add this to your .env file:")
                    print(f"LINKEDIN_PERSON_URN={personal_urn}")
                    
                    return personal_urn
                else:
                    print("⚠️  No URN found in response")
                    
            elif response.status_code == 401:
                print("❌ Token is invalid or expired")
                break
            elif response.status_code == 403:
                print(f"❌ Access denied: {response.text}")
            else:
                print(f"❌ Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n🔧 Manual method:")
    print("If the automated methods don't work, try this curl command:")
    print(f"curl -H 'Authorization: Bearer {access_token}' https://api.linkedin.com/v2/me")
    print("\nOr visit: https://developer.linkedin.com/product-catalog/consumer")
    print("And use their API explorer to call /v2/me endpoint")
    
    return None

def main():
    print("🚀 Simple LinkedIn URN Retrieval Tool")
    print("="*50)
    
    urn = get_linkedin_urn()
    
    if urn:
        print("\n" + "="*50)
        print("🎉 SUCCESS!")
        print("="*50)
        print(f"Your URN: {urn}")
        print("\nNext steps:")
        print("1. Copy the URN above")
        print("2. Set LINKEDIN_PERSON_URN in your environment")
        print("3. Test with: python linkedin_debug.py")
        print("4. Try posting to LinkedIn again!")
    else:
        print("\n" + "="*50)
        print("❌ Could not retrieve URN automatically")
        print("="*50)
        print("Try the manual curl command shown above, or:")
        print("1. Check your access token is valid")
        print("2. Verify your LinkedIn app permissions")
        print("3. Try generating a new access token")

if __name__ == "__main__":
    main()