import os
import praw
from pytrends.request import TrendReq
import argparse
import requests
import feedparser

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = "TrendAggregator-FreeOnly/0.1"

def fetch_hackernews_topics(limit=10):
    try:
        top_ids_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        top_ids = requests.get(top_ids_url).json()[:limit]
        titles = []
        for story_id in top_ids:
            item_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
            item = requests.get(item_url).json()
            if item and "title" in item:
                titles.append(f"{item['title']} [Hacker News]")
        return titles
    except Exception as e:
        print(f"Hacker News API error: {e}")
        return []

def fetch_news_topics(limit=10):
    topics = fetch_mediastack_news(limit)
    if topics:
        return topics
    print("⚠️ Falling back to Reddit news subs...")
    topics = fetch_reddit_news_fallback(limit)
    if topics:
        return topics
    print("⚠️ Falling back to RSS headlines...")
    return fetch_rss_headlines(limit)

def fetch_reddit_topics(subreddits, limit_per_sub=5):
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT
        )
        titles = []
        for sub in subreddits:
            posts = reddit.subreddit(sub).top(time_filter="day", limit=limit_per_sub)
            titles.extend([f"{post.title} [Reddit: r/{sub}]" for post in posts])
        return titles
    except Exception as e:
        print(f"Reddit API error: {e}")
        return []

def fetch_mediastack_news(limit=10):
    try:
        api_key = os.getenv("MEDIASTACK_API_KEY")
        if not api_key:
            raise ValueError("MEDIASTACK_API_KEY not set")
        url = (
            f"http://api.mediastack.com/v1/news"
            f"?access_key={api_key}&languages=en&sort=published_desc&limit={limit}"
        )
        response = requests.get(url)
        data = response.json()
        return [f"{item['title']} [News: Mediastack]" for item in data.get("data", []) if "title" in item]
    except Exception as e:
        print(f"Mediastack error: {e}")
        return []

def fetch_reddit_news_fallback(limit=10):
    try:
        reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent="NewsFallback/0.1 by your_reddit_username"
        )
        subreddit = reddit.subreddit("news")
        return [f"{post.title} [News: Reddit r/news]" for post in subreddit.hot(limit=limit)]
    except Exception as e:
        print(f"Reddit news fallback error: {e}")
        return []

def fetch_rss_headlines(limit=10):
    try:
        feed = feedparser.parse("http://feeds.bbci.co.uk/news/rss.xml")
        entries = feed.entries[:limit]
        return [f"{entry.title} [News: BBC RSS]" for entry in entries]
    except Exception as e:
        print(f"RSS fallback error: {e}")
        return []

def get_combined_trending_topics(max_total=50, sources=None):
    if sources is None:
        sources = ["news", "reddit", "hn"]

    all_topics = []

    if "news" in sources:
        all_topics += fetch_news_topics(limit=15)
    if "reddit" in sources:
        reddit_subs = ["interestingasfuck", "todayilearned", "Futurology", "Art", "AskReddit"]
        all_topics += fetch_reddit_topics(reddit_subs, limit_per_sub=4)
    if "hn" in sources:
        all_topics += fetch_hackernews_topics(limit=15)

    # Deduplicate (ignore source tag when checking)
    seen = set()
    final = []
    for topic in all_topics:
        base_topic = topic.split(" [")[0].strip().lower()
        if base_topic not in seen:
            seen.add(base_topic)
            final.append(topic)
        if len(final) >= max_total:
            break

    return final

# Run test directly
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch trending topics from free sources.")
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=["news", "reddit", "hn"],
        default=["news", "reddit", "hn"],
        help="Sources to use: 'news', 'reddit', 'hn' (default: all)"
    )
    args = parser.parse_args()

    topics = get_combined_trending_topics(sources=args.sources)

    print(f"\n📰 Trending Topics from: {', '.join(args.sources).upper()}\n")
    for i, topic in enumerate(topics, 1):
        print(f"{i}. {topic}")