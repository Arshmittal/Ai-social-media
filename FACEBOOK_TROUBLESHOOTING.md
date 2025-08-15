# Facebook API Troubleshooting Guide

## Current Error: 400 Bad Request

The error you're seeing indicates a Facebook API authentication or permission issue. Here's how to fix it:

## Required Environment Variables

Add these to your `.env` file:

```bash
# Facebook Configuration
FACEBOOK_PAGE_ID=your_page_id_here
FACEBOOK_ACCESS_TOKEN=your_user_access_token
# OR (preferred for posting)
FACEBOOK_PAGE_ACCESS_TOKEN=your_page_access_token
```

## Step-by-Step Setup

### 1. Get Your Facebook Page ID
- Go to your Facebook Page
- Click "About" in the left sidebar
- Scroll down to find your Page ID
- Copy the numeric ID (e.g., `505829139223693`)

### 2. Generate Access Tokens

#### Option A: User Access Token (Basic)
1. Go to [Facebook Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app from the dropdown
3. Click "Generate Access Token"
4. Grant permissions: `pages_manage_posts`, `pages_read_engagement`
5. Copy the token and set as `FACEBOOK_ACCESS_TOKEN`

#### Option B: Page Access Token (Recommended)
1. In Graph API Explorer, after generating user token
2. Make a GET request to: `/me/accounts`
3. Find your page in the response
4. Copy the `access_token` for your page
5. Set as `FACEBOOK_PAGE_ACCESS_TOKEN`

### 3. Required Permissions
Your token must have these permissions:
- `pages_manage_posts` - To post content
- `pages_read_engagement` - To read post metrics
- `pages_show_list` - To access page info

### 4. Test Your Configuration

Visit: `http://localhost:5000/test_facebook`

This will validate your token and permissions.

## Common Issues & Solutions

### 1. "Invalid OAuth access token"
- **Solution**: Regenerate your access token
- **Cause**: Token expired or was revoked

### 2. "Insufficient permissions"
- **Solution**: Add required permissions when generating token
- **Required**: `pages_manage_posts`, `pages_read_engagement`

### 3. "Page not found"
- **Solution**: Check your FACEBOOK_PAGE_ID is correct
- **How to find**: Facebook Page → About → Page ID

### 4. "Token belongs to different app"
- **Solution**: Make sure you're using the correct Facebook App
- **Check**: Graph API Explorer app selection

### 5. "Content violates policies"
- **Solution**: Review Facebook's content policies
- **Check**: No spam, inappropriate content, or policy violations

## Testing Commands

```bash
# Test Facebook connection
curl http://localhost:5000/test_facebook

# Check if your page ID is accessible
curl "https://graph.facebook.com/YOUR_PAGE_ID?access_token=YOUR_TOKEN"

# Test posting permissions
curl -X POST "https://graph.facebook.com/YOUR_PAGE_ID/feed" \
  -d "message=Test post&access_token=YOUR_TOKEN"
```

## Debug Information

The application now logs detailed Facebook API responses. Check your logs for:
- Token validation results
- Page access confirmation
- Detailed error messages from Facebook API

## Next Steps

1. ✅ Set correct environment variables
2. ✅ Test connection: `/test_facebook`
3. ✅ Verify permissions
4. ✅ Try posting again

If issues persist, check the application logs for detailed Facebook API error messages.