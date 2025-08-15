# services/social_media_service.py
import os
import tweepy
import requests
import aiohttp
import logging
from typing import Dict, Optional, Union
from datetime import datetime
import json
import re
from config.settings import Config

logger = logging.getLogger(__name__)

class SocialMediaService:
    def __init__(self):
        self.setup_apis()
    
    def setup_apis(self):
        """Setup API clients for different platforms"""
        # Twitter API v2 setup
        try:
            self.twitter_client = tweepy.Client(
                consumer_key=os.getenv('TWITTER_API_KEY'),
                consumer_secret=os.getenv('TWITTER_API_SECRET'),
                access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
                access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET'),
                wait_on_rate_limit=True
            )
            logger.info("Twitter API client initialized")
        except Exception as e:
            logger.error(f"Error setting up Twitter API: {e}")
            self.twitter_client = None
        
        # Facebook/Instagram/LinkedIn tokens and IDs
        self.facebook_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
        self.facebook_page_id = os.getenv('FACEBOOK_PAGE_ID')
        self.facebook_page_token = os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN')  # Optional: specific page token
        self.instagram_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
        self.linkedin_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
        self.linkedin_person_urn = os.getenv('LINKEDIN_PERSON_URN')
    
    async def post_content(self, content: Dict) -> Dict:
        """Post content to specified platform"""
        try:
            platform_raw = content.get('platform', '').lower()
            platform = 'twitter' if platform_raw in ('x', 'twitter') else platform_raw
            content_text = self._format_for_platform(platform, content.get('content', ''), content)
            
            logger.info(f"Posting to platform: {platform}")
            logger.info(f"Content text length: {len(content_text)} characters")
            
            if platform == 'twitter':
                return await self._post_to_twitter(content_text, content)
            elif platform == 'facebook':
                return await self._post_to_facebook(content_text, content)
            elif platform == 'instagram':
                return await self._post_to_instagram(content_text, content)
            elif platform == 'linkedin':
                return await self._post_to_linkedin(content_text, content)
            else:
                logger.error(f"Unsupported platform: {platform}")
                raise ValueError(f"Unsupported platform: {platform}")
                
        except Exception as e:
            logger.error(f"Error posting to {content.get('platform')}: {e}")
            return {
                'success': False,
                'error': str(e),
                'platform': content.get('platform')
            }
    
    async def _post_to_twitter(self, content: str, content_data: Dict) -> Dict:
        """Post to Twitter"""
        try:
            if not self.twitter_client:
                raise Exception("Twitter client not initialized")
            
            # Handle Twitter threads
            if content_data.get('content_type') == 'thread':
                return await self._post_twitter_thread(content, content_data)
            
            # Regular tweet
            formatted = self._format_for_twitter(content, is_thread=False)
            tweet = self.twitter_client.create_tweet(text=formatted)
            tweet_id = tweet.data['id'] if hasattr(tweet, 'data') else None

            return {
                'success': True,
                'platform': 'twitter',
                'post_id': tweet_id,
                'url': f"https://twitter.com/i/web/status/{tweet_id}" if tweet_id else None,
                'posted_at': datetime.utcnow().isoformat()
            }
            
        except tweepy.TweepyException as e:
            logger.error(f"Twitter posting error (API): {self._extract_error(e)}")
            raise
        except Exception as e:
            logger.error(f"Twitter posting error: {e}")
            raise
    
    async def _post_twitter_thread(self, content: str, content_data: Dict) -> Dict:
        """Post a Twitter thread"""
        try:
            # Split content into thread parts (assuming content is formatted with separators)
            thread_parts = content.split('\n---\n') if '\n---\n' in content else [content]
            
            tweet_ids = []
            reply_to = None
            
            for i, part in enumerate(thread_parts):
                # Apply twitter formatting for each part
                part_formatted = self._format_for_twitter(part.strip(), is_thread=True, index=i+1, total=len(thread_parts))
                if len(part_formatted) > 280:
                    # Split long parts conservatively with numbering
                    chunks = self._split_tweet_content(part_formatted, 280)
                    for chunk in chunks:
                        tweet = self.twitter_client.create_tweet(
                            text=chunk,
                            in_reply_to_tweet_id=reply_to
                        )
                        tweet_ids.append(tweet.data['id'])
                        reply_to = tweet.data['id']
                else:
                    tweet = self.twitter_client.create_tweet(
                        text=part_formatted,
                        in_reply_to_tweet_id=reply_to
                    )
                    tweet_ids.append(tweet.data['id'])
                    reply_to = tweet.data['id']
            
            return {
                'success': True,
                'platform': 'twitter',
                'post_ids': tweet_ids,
                'thread_url': f"https://twitter.com/i/web/status/{tweet_ids[0]}",
                'posted_at': datetime.utcnow().isoformat(),
                'thread_length': len(tweet_ids)
            }
            
        except Exception as e:
            logger.error(f"Twitter thread posting error: {e}")
            raise
    
    def _split_tweet_content(self, content: str, max_length: int) -> list:
        """Split content into tweet-sized chunks and preserve hashtags/links."""
        words = content.split()
        chunks = []
        current_chunk = ""

        for word in words:
            if current_chunk:
                candidate = current_chunk + " " + word
            else:
                candidate = word
            candidate = candidate.strip()
            
            if len(candidate) <= max_length:
                current_chunk = candidate
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # If a single word is longer than max_length, hard cut
                if len(word) > max_length:
                    chunks.append(word[:max_length])
                    remainder = word[max_length:]
                    current_chunk = remainder
                else:
                    current_chunk = word

        if current_chunk:
            chunks.append(current_chunk)

        return chunks
    
    async def test_facebook_connection(self) -> Dict:
        """Test Facebook API connection and permissions"""
        try:
            token_to_use = self.facebook_page_token if self.facebook_page_token else self.facebook_token
            if not token_to_use:
                return {'success': False, 'error': 'Facebook token not configured'}
            if not self.facebook_page_id:
                return {'success': False, 'error': 'Facebook page ID not configured'}

            # Test 1: Validate token
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # Check token validity
                token_url = "https://graph.facebook.com/me"
                params = {'access_token': token_to_use}
                
                async with session.get(token_url, params=params) as response:
                    if response.status != 200:
                        text = await response.text()
                        return {'success': False, 'error': f'Invalid token: {text}'}
                    
                    user_data = await response.json()
                    logger.info(f"Token valid for user: {user_data.get('name', 'Unknown')}")

                # Test 2: Check page access
                page_url = f"https://graph.facebook.com/{self.facebook_page_id}"
                async with session.get(page_url, params=params) as response:
                    if response.status != 200:
                        text = await response.text()
                        return {'success': False, 'error': f'Cannot access page: {text}'}
                    
                    page_data = await response.json()
                    logger.info(f"Page access OK: {page_data.get('name', 'Unknown page')}")

                # Test 3: Check permissions
                perms_url = f"https://graph.facebook.com/{self.facebook_page_id}/permissions"
                async with session.get(perms_url, params=params) as response:
                    if response.status == 200:
                        perms_data = await response.json()
                        permissions = [p['permission'] for p in perms_data.get('data', [])]
                        logger.info(f"Page permissions: {permissions}")

            return {'success': True, 'message': 'Facebook connection validated'}
            
        except Exception as e:
            logger.error(f"Facebook connection test failed: {e}")
            return {'success': False, 'error': str(e)}

    async def _post_to_facebook(self, content: str, content_data: Dict) -> Dict:
        """Post to Facebook Page feed (Graph API)."""
        try:
            # Check for any valid token
            token_to_use = self.facebook_page_token if self.facebook_page_token else self.facebook_token
            if not token_to_use:
                raise Exception("Facebook token not configured (set FACEBOOK_ACCESS_TOKEN or FACEBOOK_PAGE_ACCESS_TOKEN)")
            if not self.facebook_page_id:
                raise Exception("Facebook page ID not configured (FACEBOOK_PAGE_ID)")

            logger.info(f"Facebook Page ID: {self.facebook_page_id}")
            logger.info(f"Facebook Token exists: {bool(self.facebook_token)}")
            logger.info(f"Content length: {len(content)} characters")

            url = f"https://graph.facebook.com/v18.0/{self.facebook_page_id}/feed"

            # Use page-specific token if available, otherwise use general token
            token_to_use = self.facebook_page_token if self.facebook_page_token else self.facebook_token

            payload = {
                'message': content,
                'access_token': token_to_use
            }
            
            logger.info(f"Posting to URL: {url}")
            logger.info(f"Payload keys: {list(payload.keys())}")

            # Use async HTTP request
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=payload) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        logger.error(f"Facebook API Error {response.status}: {response_text}")
                        # Try to parse error details from the text
                        try:
                            import json
                            error_data = json.loads(response_text)
                            error_msg = error_data.get('error', {}).get('message', response_text)
                            error_code = error_data.get('error', {}).get('code', response.status)
                            logger.error(f"Facebook Error Code {error_code}: {error_msg}")
                        except:
                            logger.error(f"Could not parse Facebook error response: {response_text}")
                        response.raise_for_status()

                    result = await response.json()

                    return {
                        'success': True,
                        'platform': 'facebook',
                        'post_id': result.get('id'),
                        'posted_at': datetime.utcnow().isoformat()
                    }

        except aiohttp.ClientResponseError as e:
            logger.error(f"Facebook HTTP error: {e.status} {e.message}")
            raise
        except Exception as e:
            logger.error(f"Facebook posting error: {e}")
            raise
    
    async def _post_to_instagram(self, content: str, content_data: Dict) -> Dict:
        """Post to Instagram"""
        try:
            if not self.instagram_token:
                raise Exception("Instagram token not configured")
            
            # Instagram requires image/video content
            if not content_data.get('image_path'):
                raise Exception("Instagram posts require media content")
            
            # This is a simplified version - real implementation needs media upload
            return {
                'success': True,
                'platform': 'instagram',
                'post_id': f"ig_{datetime.utcnow().timestamp()}",
                'posted_at': datetime.utcnow().isoformat(),
                'note': 'Instagram posting requires media upload implementation'
            }
            
        except Exception as e:
            logger.error(f"Instagram posting error: {e}")
            raise
    
    async def _post_to_linkedin(self, content: str, content_data: Dict) -> Dict:
        """Post to LinkedIn"""
        try:
            if not self.linkedin_token:
                raise Exception("LinkedIn token not configured")
            if not self.linkedin_person_urn:
                raise Exception("LinkedIn person URN not configured (LINKEDIN_PERSON_URN)")
            
            url = "https://api.linkedin.com/v2/ugcPosts"
            
            headers = {
                'Authorization': f'Bearer {self.linkedin_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "author": self.linkedin_person_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": content},
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            # Use async HTTP request
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 403:
                        response_text = await response.text()
                        logger.error(f"LinkedIn 403: {response_text}")
                    response.raise_for_status()
                    
                    result = await response.json()
                    
                    return {
                        'success': True,
                        'platform': 'linkedin',
                        'post_id': result.get('id'),
                        'posted_at': datetime.utcnow().isoformat()
                    }
            
        except aiohttp.ClientResponseError as e:
            logger.error(f"LinkedIn HTTP error: {e.status} {e.message}")
            raise
        except Exception as e:
            logger.error(f"LinkedIn posting error: {e}")
            raise
    
    async def get_post_analytics(self, platform: str, post_id: str) -> Dict:
        """Get analytics for a posted content"""
        try:
            if platform == 'twitter':
                return await self._get_twitter_analytics(post_id)
            elif platform == 'facebook':
                return await self._get_facebook_analytics(post_id)
            elif platform == 'instagram':
                return await self._get_instagram_analytics(post_id)
            elif platform == 'linkedin':
                return await self._get_linkedin_analytics(post_id)
            else:
                return {'error': f'Analytics not supported for {platform}'}
                
        except Exception as e:
            logger.error(f"Error getting analytics for {platform}: {e}")
            return {'error': str(e)}
    
    async def _get_twitter_analytics(self, tweet_id: str) -> Dict:
        """Get Twitter/X tweet analytics (public metrics)."""
        try:
            tweet = self.twitter_client.get_tweet(
                tweet_id,
                tweet_fields=['public_metrics', 'created_at']
            )

            if hasattr(tweet, 'data') and tweet.data:
                metrics = tweet.data.get('public_metrics', {}) if isinstance(tweet.data, dict) else tweet.data.public_metrics
                created_at = tweet.data.get('created_at') if isinstance(tweet.data, dict) else getattr(tweet.data, 'created_at', None)
                return {
                    'platform': 'twitter',
                    'retweet_count': metrics.get('retweet_count', 0),
                    'like_count': metrics.get('like_count', 0),
                    'reply_count': metrics.get('reply_count', 0),
                    'quote_count': metrics.get('quote_count', 0),
                    'created_at': created_at.isoformat() if hasattr(created_at, 'isoformat') else created_at
                }
            else:
                return {'error': 'Tweet not found'}

        except tweepy.TweepyException as e:
            logger.error(f"Twitter analytics error (API): {self._extract_error(e)}")
            return {'error': self._extract_error(e)}
        except Exception as e:
            logger.error(f"Error getting Twitter analytics: {e}")
            return {'error': str(e)}
    
    async def _get_facebook_analytics(self, post_id: str) -> Dict:
        """Get Facebook post analytics"""
        try:
            url = f"https://graph.facebook.com/v18.0/{post_id}/insights"
            params = {
                'metric': 'post_impressions,post_clicks,post_reactions_by_type_total',
                'access_token': self.facebook_token
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 403:
                logger.error(f"Facebook analytics 403: {response.text}")
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'platform': 'facebook',
                'insights': data.get('data', []),
                'retrieved_at': datetime.utcnow().isoformat()
            }
            
        except requests.HTTPError as e:
            logger.error(f"Facebook analytics HTTP error: {self._extract_http_error(e)}")
            return {'error': self._extract_http_error(e)}
        except Exception as e:
            logger.error(f"Error getting Facebook analytics: {e}")
            return {'error': str(e)}
    
    async def _get_instagram_analytics(self, post_id: str) -> Dict:
        """Get Instagram post analytics"""
        try:
            # Instagram Basic Display API doesn't provide insights
            # You'd need Instagram Business API for analytics
            return {
                'platform': 'instagram',
                'note': 'Instagram analytics requires Business API',
                'retrieved_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting Instagram analytics: {e}")
            return {'error': str(e)}
    
    async def _get_linkedin_analytics(self, post_id: str) -> Dict:
        """Get LinkedIn post analytics"""
        try:
            # LinkedIn analytics require additional permissions
            return {
                'platform': 'linkedin',
                'note': 'LinkedIn analytics require additional API permissions',
                'retrieved_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting LinkedIn analytics: {e}")
            return {'error': str(e)}

    # --------------------------
    # Formatting & Error Helpers
    # --------------------------
    def _format_for_platform(self, platform: str, text: str, content: Dict) -> str:
        """Format content text per platform rules before posting."""
        if platform == 'twitter':
            return self._format_for_twitter(text, is_thread=content.get('content_type') == 'thread')
        if platform == 'linkedin':
            # LinkedIn: remove markdown, cap length
            text = self._strip_markdown(text)
            return text[:Config.PLATFORM_CONFIGS['linkedin']['max_length']]
        if platform == 'facebook':
            return text[:Config.PLATFORM_CONFIGS['facebook']['max_length']]
        if platform == 'instagram':
            return text[:Config.PLATFORM_CONFIGS['instagram']['max_length']]
        return text

    def _format_for_twitter(self, text: str, is_thread: bool = False, index: Optional[int] = None, total: Optional[int] = None) -> str:
        """Apply X/Twitter-specific formatting: trim, limit hashtags, enforce length."""
        max_len = Config.PLATFORM_CONFIGS['twitter']['max_length']
        text = self._strip_markdown(text)
        text = re.sub(r"\s+", " ", text).strip()
        # Limit hashtags to platform max
        max_tags = Config.PLATFORM_CONFIGS['twitter']['max_hashtags']
        words = text.split()
        hashtags = [w for w in words if w.startswith('#')]
        if len(hashtags) > max_tags:
            kept = set(hashtags[:max_tags])
            words = [w for w in words if not (w.startswith('#') and w not in kept)]
            text = " ".join(words)
        if is_thread and index and total:
            suffix = f" ({index}/{total})"
            if len(text) > max_len - len(suffix):
                text = text[:max_len - len(suffix)] + suffix
            else:
                text = text + suffix
        else:
            text = text[:max_len]
        return text

    def _strip_markdown(self, text: str) -> str:
        """Remove basic markdown like **bold**, _italic_, [links](url)."""
        # Convert markdown links to: [text](url) -> text url
        text = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r"\1 \2", text)
        # Remove bold/italic markers
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        text = re.sub(r"_([^_]+)_", r"\1", text)
        return text

    def _extract_http_error(self, e: requests.HTTPError) -> str:
        try:
            resp = e.response
            return f"{resp.status_code} {resp.reason}: {resp.text}" if resp is not None else str(e)
        except Exception:
            return str(e)

    def _extract_error(self, e: Exception) -> str:
        return str(e)


