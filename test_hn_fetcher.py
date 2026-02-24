"""Test script for hn_fetcher module"""
from hn_fetcher import HNFetcher


def test_get_top_stories():
    """Test fetching top stories from Hacker News"""
    print("=" * 50)
    print("Testing: get_top_stories()")
    print("=" * 50)

    fetcher = HNFetcher()
    stories = fetcher.get_top_stories(n=5)

    print(f"\n✓ Fetched {len(stories)} stories:")
    for i, story in enumerate(stories, 1):
        print(f"\n{i}. {story['title']}")
        print(f"   URL: {story['url']}")
        print(f"   Score: {story['score']}")
    return stories


def test_fetch_content(url: str):
    """Test fetching content using Jina Reader"""
    print("\n" + "=" * 50)
    print(f"Testing: fetch_content()")
    print("=" * 50)

    fetcher = HNFetcher()
    content = fetcher.fetch_content(url)

    print(f"\n✓ Content length: {len(content)} characters")
    print("\n--- First 500 characters of content ---")
    print(content[:500])
    print("...")
    return content


if __name__ == "__main__":
    # Test 1: Get top stories
    stories = test_get_top_stories()

    # Test 2: Fetch content of first story (if available)
    if stories:
        first_url = stories[0]['url']
        print(f"\nTesting content fetch with first story URL...")
        test_fetch_content(first_url)

    print("\n" + "=" * 50)
    print("✓ All tests completed!")
    print("=" * 50)
