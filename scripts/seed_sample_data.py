"""
Seed script: Populate the database with sample data for both accounts.
Uses TikTok public data scraped from host + synthetic Instagram data.
Run from the host machine: python3 scripts/seed_sample_data.py
"""
import httpx
import json
import random
import re
import uuid
from datetime import datetime, timedelta, timezone

API = "http://localhost:8001"
H = {"X-App-Password": "admin123", "Content-Type": "application/json"}


def get_accounts():
    r = httpx.get(f"{API}/api/accounts", headers=H)
    return r.json()


def seed_tiktok_profile():
    """Update TikTok account with real scraped data from host."""
    print("Scraping TikTok profile from host...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    r = httpx.get("https://www.tiktok.com/@fabimoure", headers=headers, follow_redirects=True, timeout=20)
    match = re.search(
        r'<script\s+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.+?)</script>',
        r.text, re.DOTALL,
    )
    if match:
        data = json.loads(match.group(1))
        scope = data.get("__DEFAULT_SCOPE__", {})
        user_info = scope.get("webapp.user-detail", {}).get("userInfo", {})
        stats = user_info.get("stats", {})
        return {
            "follower_count": stats.get("followerCount", 2517),
            "video_count": stats.get("videoCount", 236),
            "hearts": stats.get("heartCount", 40800),
        }
    return {"follower_count": 2517, "video_count": 236, "hearts": 40800}


def generate_tiktok_posts(account_id: str, count: int = 30):
    """Generate realistic TikTok video data."""
    captions = [
        "Morning routine in our cozy home 🏡",
        "Kitchen organization hack you need to try!",
        "DIY wall art project under $20",
        "My evening self-care routine 🧖‍♀️",
        "Thrift flip: old table → aesthetic nightstand",
        "Pantry restock & organization ASMR",
        "Our living room makeover reveal ✨",
        "Budget-friendly bathroom upgrade",
        "Day in my life: working from home",
        "3 ways to style a small balcony",
        "Cozy fall home decor haul 🍂",
        "Rearranging my bedroom for better energy",
        "Homemade candle tutorial",
        "Minimalist closet organization",
        "Sunday reset routine: cleaning & prepping",
        "How I style my bookshelves",
        "Quick dinner recipe for busy weeknights 🍝",
        "Apartment tour: 600 sq ft",
        "My favorite Amazon home finds",
        "Laundry room makeover on a budget",
        "Plant care routine for beginners 🌿",
        "Aesthetic desk setup for productivity",
        "Bedroom makeover: before & after",
        "5 organizing products that changed my life",
        "Flea market finds & how I style them",
        "My morning coffee routine ☕",
        "Bathroom deep clean with me",
        "Styling tips for rental apartments",
        "How I meal prep for the week",
        "Cozy reading nook transformation",
    ]

    posts = []
    now = datetime.now(timezone.utc)

    for i in range(count):
        days_ago = i * random.randint(1, 4)
        posted_at = now - timedelta(days=days_ago, hours=random.randint(0, 23))
        vid_id = str(random.randint(7300000000000000000, 7399999999999999999))

        # Simulate varying engagement (some posts go viral)
        base_views = random.randint(500, 8000)
        if random.random() < 0.15:  # 15% chance of viral
            base_views *= random.randint(5, 20)

        views = base_views
        likes = int(views * random.uniform(0.05, 0.15))
        comments = int(likes * random.uniform(0.02, 0.08))
        shares = int(likes * random.uniform(0.01, 0.05))
        saves = int(likes * random.uniform(0.03, 0.10))

        posts.append({
            "platform_post_id": vid_id,
            "platform": "tiktok",
            "post_type": "video",
            "caption": captions[i % len(captions)],
            "media_url": "",
            "permalink": f"https://www.tiktok.com/@fabimoure/video/{vid_id}",
            "posted_at": posted_at.isoformat(),
            "metrics": {
                "views": views,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "saves": saves,
                "reach": int(views * 0.8),
            },
        })

    return posts


def generate_instagram_posts(account_id: str, count: int = 25):
    """Generate realistic Instagram post data."""
    captions = [
        "New home vibes ✨ Finally got the living room exactly how I wanted it",
        "Sunday mornings at their finest ☕️",
        "Bedroom refresh complete! Swipe for the before →",
        "Found this beauty at the flea market 🪞",
        "Kitchen corner that makes me happy every morning",
        "Balcony garden update: everything is blooming! 🌸",
        "Cozy reading spot for rainy afternoons 📚",
        "DIY project complete! Made this shelf from scratch",
        "Morning light in our apartment hits different",
        "Pantry goals 🫙 spent the weekend organizing",
        "New plant baby! Any name suggestions? 🌿",
        "Bathroom makeover reveal — total cost: $150",
        "Our dinner table setup for date night 🕯",
        "Before & after: guest room transformation",
        "Home office tour — link in bio for all products",
        "Fall decor is up! 🍂 What do you think?",
        "Thrifted these frames for $5 each 🖼",
        "Cleaning day ASMR in my stories!",
        "Sunset from our balcony never gets old 🌅",
        "Minimalist living room — less is more",
        "Coffee table styling ideas 💡",
        "Weekend project: painted the accent wall",
        "Organized my closet — it only took 6 hours 😅",
        "Morning routine reset for the new week",
        "Home tour is live on my channel! Link in bio",
    ]

    post_types = ["image", "carousel", "reel", "image", "carousel", "reel", "image"]
    posts = []
    now = datetime.now(timezone.utc)

    for i in range(count):
        days_ago = i * random.randint(2, 5)
        posted_at = now - timedelta(days=days_ago, hours=random.randint(0, 23))
        shortcode = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-", k=11))
        post_type = post_types[i % len(post_types)]

        # Engagement varies by post type
        if post_type == "reel":
            base_views = random.randint(2000, 15000)
            likes = int(base_views * random.uniform(0.08, 0.20))
        else:
            base_views = random.randint(300, 3000)
            likes = int(base_views * random.uniform(0.15, 0.35))

        if random.random() < 0.1:
            likes *= random.randint(3, 8)
            base_views *= random.randint(3, 8)

        comments = int(likes * random.uniform(0.02, 0.06))
        saves = int(likes * random.uniform(0.05, 0.15))

        posts.append({
            "platform_post_id": str(random.randint(3300000000000000000, 3399999999999999999)),
            "platform": "instagram",
            "post_type": post_type,
            "caption": captions[i % len(captions)],
            "media_url": "",
            "permalink": f"https://www.instagram.com/p/{shortcode}/",
            "posted_at": posted_at.isoformat(),
            "metrics": {
                "views": base_views if post_type == "reel" else 0,
                "likes": likes,
                "comments": comments,
                "shares": 0,
                "saves": saves,
                "reach": int(base_views * 0.7) if post_type == "reel" else int(likes * 3),
            },
        })

    return posts


def seed_posts(account_id: str, posts: list[dict]):
    """Insert posts via sync service by writing directly to DB through API."""
    for post in posts:
        r = httpx.post(
            f"{API}/api/accounts/{account_id}/posts/seed",
            headers=H,
            json=post,
            timeout=10,
        )
        if r.status_code not in (200, 201, 404):
            print(f"  Post seed response: {r.status_code}")


def main():
    accounts = get_accounts()
    print(f"Found {len(accounts)} accounts")

    tiktok_profile = seed_tiktok_profile()
    print(f"TikTok profile: {tiktok_profile}")

    for account in accounts:
        aid = account["id"]
        platform = account["platform"]
        username = account["username"]
        print(f"\nSeeding {platform} @{username} ({aid})...")

        if platform == "tiktok":
            posts = generate_tiktok_posts(aid, count=30)
        else:
            posts = generate_instagram_posts(aid, count=25)

        seed_posts(aid, posts)
        print(f"  Seeded {len(posts)} posts")


if __name__ == "__main__":
    main()
