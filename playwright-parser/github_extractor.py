import re
from dataclasses import dataclass
from playwright.async_api import ElementHandle
from base_extractor import AbstractEntity, AbstractExtractor


@dataclass
class IRepositoryFields:
    title: str
    url: str
    description: str
    language: str
    count_all_stars: int
    count_stars_today: int
    count_forks: int


class RepositoryEntity(AbstractEntity[IRepositoryFields]):
    fields: IRepositoryFields

    def __init__(self, fields: IRepositoryFields):
        super().__init__(fields)


class GithubExtractor(AbstractExtractor[RepositoryEntity]):
    domain = "github.com"
    wait_selector = ".Box-row"

    async def parse_entity(self, element: ElementHandle) -> RepositoryEntity:
        async def get_text(selector: str) -> str:
            el = await element.query_selector(selector)
            if el:
                raw = await el.text_content() or ""
                cleaned = re.sub(r"\s+", " ", raw.strip())
                return cleaned
            return ""

        async def get_href(selector: str) -> str:
            el = await element.query_selector(selector)
            href = await el.get_attribute("href") if el else ""
            return f"https://{self.domain}{href}" if href else ""

        async def get_int(selector: str) -> int:
            text = await get_text(selector)

            match = re.search(r"[\d,]+", text)
            if match:
                num_str = match.group().replace(",", "")
                return int(num_str)
            return 0

        repo_data = IRepositoryFields(
            title=await get_text(".h3"),
            url=await get_href(".h3 > a"),
            description=await get_text(".col-9"),
            language=await get_text("[itemprop=\"programmingLanguage\"]"),
            count_all_stars=await get_int("a.Link[href$=\"/stargazers\"]"),
            count_stars_today=await get_int("span.d-inline-block.float-sm-right"),
            count_forks=await get_int("a.Link[href$=\"/forks\"]")
        )

        return RepositoryEntity(repo_data)
