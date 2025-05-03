import asyncio
import json
from github_extractor import GithubExtractor


async def main():
    extractor = GithubExtractor()
    url = "https://github.com/trending"

    print("Parsing page...")
    results = await extractor.parse_page(url)

    repo_data = []
    for repo in results:
        repo_data.append({
            "Title"         : repo.fields.title,
            "URL"           : repo.fields.url,
            "Description"   : repo.fields.description,
            "Language"      : repo.fields.language,
            "Stars (All)"   : repo.fields.count_all_stars,
            "Stars (Today)" : repo.fields.count_stars_today,
            "Forks"         : repo.fields.count_forks,
            "Collected Date": repo.collected["date"]
        })

    with open("github_trending.json", "w", encoding="utf-8") as f:
        json.dump(repo_data, f, ensure_ascii=False, indent=4)

    print("Data saved to github_trending.json")


if __name__ == "__main__":
    asyncio.run(main())
