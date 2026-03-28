# PRD-03: Platform Integrations (Instagram & TikTok)

## Domain
OAuth flows, API clients, token management for Instagram and TikTok.

## Dependencies
- PRD-01 (database, accounts table)
- PRD-02 (authenticated user context)

## Goal
Allow users to connect their Instagram and TikTok accounts via OAuth, and provide a reliable client layer to fetch posts and metrics from each platform.

---

## 1. OAuth Connection Flow

### General Flow
1. User clicks "Connect Instagram" / "Connect TikTok"
2. Frontend redirects to platform's OAuth authorization URL
3. User authorizes on platform
4. Platform redirects back to our callback URL with auth code
5. Backend exchanges code for access/refresh tokens
6. Backend stores encrypted tokens in `accounts` table
7. Backend triggers initial data fetch (last 20 posts)

### API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/integrations/instagram/connect` | Get Instagram OAuth URL | Token |
| GET | `/api/integrations/instagram/callback` | Handle OAuth callback | Public (state param) |
| GET | `/api/integrations/tiktok/connect` | Get TikTok OAuth URL | Token |
| GET | `/api/integrations/tiktok/callback` | Handle OAuth callback | Public (state param) |
| GET | `/api/accounts` | List connected accounts | Token |
| DELETE | `/api/accounts/{account_id}` | Disconnect account | Token |
| POST | `/api/accounts/{account_id}/refresh` | Force token refresh | Token |

## 2. Instagram Integration

### API: Instagram Graph API (Business/Creator accounts)

### Required Permissions
- `instagram_basic`
- `instagram_manage_insights`
- `pages_show_list`
- `pages_read_engagement`

### OAuth URLs
- Auth: `https://www.facebook.com/v19.0/dialog/oauth`
- Token: `https://graph.facebook.com/v19.0/oauth/access_token`

### Data We Fetch

**User Profile:**
- username, name, profile_picture_url, followers_count, media_count

**Media (Posts):**
- id, caption, media_type, media_url, permalink, timestamp
- Supports: IMAGE, VIDEO, CAROUSEL_ALBUM, REELS

**Media Insights (per post):**
- impressions, reach, engagement
- For Reels: plays, total_interactions, likes, comments, shares, saves
- For Stories: impressions, reach, replies, exits

### Client Interface
```python
class InstagramClient:
    async def get_user_profile(self, access_token: str) -> dict
    async def get_recent_media(self, access_token: str, limit: int = 20) -> list[dict]
    async def get_media_insights(self, access_token: str, media_id: str) -> dict
    async def refresh_token(self, refresh_token: str) -> dict
```

### Token Management
- Short-lived token (1h) → exchange for long-lived (60 days)
- Auto-refresh before expiry (cron checks daily)
- If refresh fails → mark account status as 'expired', notify user

## 3. TikTok Integration

### API: TikTok API for Developers (Content Posting API + Research API)

### Required Scopes
- `user.info.basic`
- `video.list`
- `video.insights` (if available)

### OAuth URLs
- Auth: `https://www.tiktok.com/v2/auth/authorize/`
- Token: `https://open.tiktokapis.com/v2/oauth/token/`

### Data We Fetch

**User Profile:**
- open_id, display_name, avatar_url, follower_count, video_count

**Videos:**
- id, title, description, create_time, share_url, duration
- cover_image_url, embed_link

**Video Metrics (where available):**
- view_count, like_count, comment_count, share_count

### Client Interface
```python
class TikTokClient:
    async def get_user_info(self, access_token: str) -> dict
    async def get_user_videos(self, access_token: str, max_count: int = 20) -> list[dict]
    async def get_video_insights(self, access_token: str, video_ids: list[str]) -> list[dict]
    async def refresh_token(self, refresh_token: str) -> dict
```

### Token Management
- Access token valid for 24h
- Refresh token valid for 365 days
- Auto-refresh via cron before expiry

## 4. CSV Upload Fallback

If API access is delayed or rate-limited, users can upload data manually.

### Endpoint
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/accounts/{account_id}/import` | Upload CSV of post data | Token |

### Supported CSV Format
```csv
post_url,caption,posted_at,views,likes,comments,shares,saves
https://instagram.com/p/xxx,My caption,2026-03-20T12:00:00Z,15000,1200,45,30,200
```

### Processing
1. Validate CSV structure
2. Create/update posts and post_metrics
3. Return import summary (created, updated, errors)

## 5. Token Encryption

All platform tokens stored encrypted in the database:
- Use **Fernet symmetric encryption** (from `cryptography` library)
- Key stored in `ENCRYPTION_KEY` env var
- Encrypt before DB write, decrypt on read
- Never log tokens

```python
# app/services/encryption.py
from cryptography.fernet import Fernet

class TokenEncryption:
    def encrypt(self, plaintext: str) -> str: ...
    def decrypt(self, ciphertext: str) -> str: ...
```

## 6. Rate Limiting & Error Handling

### Instagram
- 200 calls per user per hour
- Implement exponential backoff on 429 responses
- Cache responses for 5 minutes

### TikTok
- Rate limits vary by endpoint
- Implement retry with backoff
- Cache responses for 5 minutes

### Error States
| Error | Action |
|-------|--------|
| Token expired | Auto-refresh, retry once |
| Token revoked | Mark account 'revoked', notify user |
| Rate limited | Queue retry with backoff |
| API unavailable | Log, skip, retry next cycle |

## 7. Acceptance Criteria

- [ ] User can connect Instagram via OAuth
- [ ] User can connect TikTok via OAuth
- [ ] Tokens are encrypted in the database
- [ ] Token auto-refresh works before expiry
- [ ] Initial fetch retrieves last 20 posts with metrics
- [ ] CSV upload fallback works
- [ ] User can disconnect an account
- [ ] Expired/revoked tokens are handled gracefully
- [ ] Connected accounts listed in user profile
- [ ] Platform API errors don't crash the system

## 8. Out of Scope (MVP)
- Posting content to platforms
- Story/live data from TikTok
- Multi-page Instagram accounts
- Webhooks for real-time updates (polling only for MVP)
