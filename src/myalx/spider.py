import html
import json
import re
from urllib.parse import urlparse

import scrapy
from markdownify import markdownify
from scrapy.crawler import CrawlerProcess
from scrapy.exceptions import CloseSpider


class AlxSpider(scrapy.Spider):
    name = "alx"
    allowed_domains = ["intranet.alxswe.com"]
    handle_httpstatus_list = [404, 410, 301, 500]

    def __init__(self, email: str, password: str, url: str, callback=None) -> None:
        """Initialize the AlxSpider instance."""

        self.email = email
        self.password = password
        self.url = url
        self.callback = callback

    def start_requests(self):
        """Generate initial requests to start the spider."""

        if re.match(r"^\d+$", self.url):
            self.url = f"https://intranet.alxswe.com/projects/{self.url}"

        parsed_url = urlparse(self.url)
        if not (
            parsed_url.scheme == "https"
            and parsed_url.netloc == "intranet.alxswe.com"
            and re.match(r"/projects/\d+", parsed_url.path)
        ):
            raise CloseSpider("Invalid URL.")

        yield scrapy.Request(self.url, callback=self.check_login, dont_filter=True)

    def check_login(self, response):
        """Check if the spider is logged in based on the response."""

        if "sign_in" in response.url:
            yield scrapy.FormRequest.from_response(
                response,
                formdata={
                    "authenticity_token": response.css(
                        "form input[name=authenticity_token]::attr(value)"
                    ).extract_first(),
                    "user[email]": self.email,
                    "user[password]": self.password,
                },
                callback=self.parse,
            )

        else:
            yield self.parse(response)

    def parse(self, response):
        """Parse the response and extract information"""

        alert: str = response.css(".alert.alert-danger::text").get()

        if alert is not None:
            self.logger.error(f"\033[91m{alert}\033[0m")
            raise CloseSpider(reason=alert)

        elif response.status == 404:
            error_message = f"Page not found (404) for URL: {response.url}"
            self.logger.error(f"\033[91m{error_message}\033[0m")
            raise CloseSpider(reason=error_message)

        elif response.status == 410:
            error_message = f"Gone (410) for URL: {response.url}"
            self.logger.error(f"\033[91m{error_message}\033[0m")
            raise CloseSpider(reason=error_message)

        elif response.status == 301:
            error_message = f"Moved Permanently (301) for URL: {response.url}"
            self.logger.error(f"\033[91m{error_message}\033[0m")
            raise CloseSpider(reason=error_message)

        elif response.status == 500:
            error_message = f"Internal Server Error (500) for URL: {response.url}"
            self.logger.error(f"\033[91m{error_message}\033[0m")
            raise CloseSpider(reason=error_message)

        # else:
        # 	error_message = f"Unexpected error (HTTP {response.status}) for URL: {response.url}"
        # 	self.logger.error(f"\033[91m{error_message}\033[0m")
        # 	raise CloseSpider(reason=error_message)

        project_item = AlxProjectItem()
        project_item["url"] = response.url
        project_item["title"] = response.css("h1.gap::text").get()
        project_item["requirements"] = response.css(
            "#project-description.panel.panel-default > .panel-body > h2:contains('Requirements') ~ *"
        ).extract()

        tasks = []
        for index, task in enumerate(response.css("div[id^=task-num-]")):
            task_item = AlxTaskItem()
            task_item["no"] = index
            task_item["title"] = task.css(".panel-title::text").extract_first()
            task_item["type"] = task.css(".label-info::text").extract_first()
            task_item["body"] = (
                task.css(".panel-body > .task_progress_score_bar ~ *").extract()
                if task.css(".panel-body > .task_progress_score_bar ~ *").extract()
                != []
                else task.css(".panel-body > #user_id ~ *").extract()
            )
            task_item["github_repository"] = task.css(
                ".list-group-item > ul > li:contains('GitHub repository:') code::text"
            ).get()
            task_item["directory"] = task.css(
                ".list-group-item > ul > li:contains('Directory:') code::text"
            ).get()
            task_item["files"] = task.css(
                ".list-group-item > ul > li:contains('File:') code::text"
            ).extract_first()
            task_item["prototypes"] = task.css(
                ".panel-body ul li:contains('Prototype:') code::text"
            ).extract()
            tasks.append(dict(task_item))

        project_item["tasks"] = tasks

        react_props = response.css(
            'div[data-react-class="tags/Tags"]::attr(data-react-props)'
        ).get()
        tags_data = json.loads(react_props) if react_props else {}
        project_item["tags"] = [tag["value"] for tag in tags_data.get("tags", [])]

        react_props = response.css(
            'div[data-react-class="projects/ProjectMetadata"]::attr(data-react-props)'
        ).get()
        tags_data = json.loads(react_props) if react_props else {}
        project_item["metadata"] = tags_data.get("metadata", {})

        project_dict = dict(project_item)
        yield project_dict

        if self.callback is not None:
            self.callback(project_dict)


# Scrapy items ================================================================
class AlxProjectItem(scrapy.Item):
    """Scrapy Item class to represent information about an ALX project."""

    tags = scrapy.Field()
    url = scrapy.Field()
    title = scrapy.Field()
    no_of_tasks = scrapy.Field()
    tasks = scrapy.Field()
    directory = scrapy.Field()
    requirements = scrapy.Field()
    header = scrapy.Field()
    metadata = scrapy.Field()


class AlxTaskItem(scrapy.Item):
    """Scrapy Item class to represent information about an ALX task."""

    no = scrapy.Field()
    title = scrapy.Field()
    type = scrapy.Field()
    body = scrapy.Field()
    github_repository = scrapy.Field()
    directory = scrapy.Field()
    description = scrapy.Field()
    files = scrapy.Field()
    prototypes = scrapy.Field()


# Scrapy pipelines ============================================================
class AlxPipeline:
    """Scrapy pipeline to process and export scraped data."""

    def process_item(self, item, spider) -> dict:
        """Process a scraped item."""
        filtered_tasks = []
        tasks = item.get("tasks", [])

        item["no_of_tasks"] = len(tasks)
        item["url"] = item.get("url", "").strip()
        item["title"] = item.get("title", "").strip()

        for paragraph in item.get("requirements", []):
            paragraph = markdownify(paragraph)

            match = re.search(r"(\d*-?[A-Za-z0-9_]+\.h)", paragraph)
            if match:
                item["header"] = match.group(1)

        item.pop("requirements", None)

        directories = []
        for task in tasks:
            directory = task.get("directory", "") or task.get("github_repository", "")
            if directory:
                directories.append(directory)

            if task["files"]:
                task["files"] = task.get("files", []).split(", ")
                task["files"] = [
                    re.sub(r"\s+", " ", file.strip()) for file in task.get("files", [])
                ]
            task["prototypes"] = [
                re.sub(r"\s+", " ", prototype.strip())
                for prototype in task.get("prototypes", "")
            ]

            for field in ["title", "type", "github_repository", "directory"]:
                if task[field]:
                    task[field] = task.get(field, "").strip()

            gcc_command = None
            test_files, description = [], []

            for paragraph in task.get("body", []):
                paragraph = markdownify(paragraph, code_language="console", bullets="*")
                paragraph = re.sub(r"\t", "  ", paragraph)
                paragraph_description = re.sub(r"\n{2,}", "\n", paragraph)
                paragraph_description = re.sub(
                    r"\n```console", "```console", paragraph_description
                )
                paragraph_description = re.sub(r"```\n", "```", paragraph_description)
                description.extend(paragraph_description.split("\n"))

                gcc_commands = re.findall(r"gcc .+", paragraph)
                if gcc_commands:
                    gcc_commands = [html.unescape(command) for command in gcc_commands]
                    gcc_command = (
                        " && ".join(gcc_commands)
                        if len(gcc_commands) > 1
                        else "".join(gcc_commands)
                    )

                match = re.search(r"cat (?!-)(\d*-?[A-Za-z0-9_.]+)", paragraph)
                if match:
                    test_filename = match.group(1)
                    lines = paragraph.split("\n")
                    start_index, end_index = None, None

                    for index, line in enumerate(lines):
                        lines[index] = html.unescape(line)
                        match = re.search(r"cat (?!-)(\d*-?[A-Za-z0-9_.]+)", paragraph)

                        if match.group(0) in line:
                            start_index = index + 1
                            break

                    for index in range(start_index + 1, len(lines)):

                        if "$" in lines[index]:
                            end_index = index
                            break
                        lines[index] = html.unescape(lines[index])

                    test_file_content = lines[start_index:end_index]

                    test_files.append(
                        {
                            "filename": test_filename,
                            "content": test_file_content,
                        }
                    )

            task["description"] = description
            task["gcc_command"] = gcc_command
            task["test_files"] = test_files

            task = {
                key: value
                for key, value in task.items()
                if value is not None and value != []
            }
            filtered_tasks.append(task)

            # Remove the 'body' field from the task item
            task.pop("body", None)

        item["tasks"] = filtered_tasks
        item["directory"] = (
            directories[0]
            if all(item == directories[0] for item in directories)
            else None
        )

        return item


# Utility function to run the Scrapy Spider ===================================
def run_spider(url: str, email: str, password: str) -> dict:
    """Run the AlxSpider to scrape data from a specified URL after logging in."""

    scraped_data = {}

    def item_scraped(data):
        scraped_data.update(data)

    process = CrawlerProcess(
        {
            "FEEDS": {
                "project_data.json": {
                    "format": "json",
                    "encoding": "utf8",
                    "store_empty": False,
                    "fields": None,
                    "indent": 4,
                    "item_export_kwargs": {
                        "export_empty_fields": True,
                    },
                    "overwrite": True,
                },
            },
            "ITEM_PIPELINES": {
                "myalx.spider.AlxPipeline": 300,
            },
            "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
            "LOG_LEVEL": "INFO",
        }
    )
    process.crawl(
        crawler_or_spidercls=AlxSpider,
        email=email,
        password=password,
        url=url,
        callback=item_scraped,
    )
    process.start()

    return scraped_data
