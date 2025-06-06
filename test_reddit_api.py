import os
import praw

# Load credentials from environment
client_id = os.getenv("REDDIT_CLIENT_ID")
client_secret = os.getenv("REDDIT_CLIENT_SECRET")
user_agent = "MyTrendingFetcher/0.1 by YOUR_REDDIT_USERNAME"  # <-- customize this

# Initialize Reddit client
reddit = praw.Reddit(
    client_id=client_id,
    client_secret=client_secret,
    user_agent=user_agent
)

# Try to fetch top posts from r/AskReddit
try:
    subreddit = reddit.subreddit("AskReddit")
    print("🔍 Top posts from r/AskReddit (today):")
    for post in subreddit.top(limit=5, time_filter="day"):
        print(f"- {post.title}")
except Exception as e:
    print(f"❌ Reddit API error: {e}")
