import html
import json
import re
from pathlib import Path
from typing import Union

import scrapy
from decouple import Config, RepositoryEnv
from markdownify import markdownify
from scrapy.core.engine import CloseSpider
from scrapy.crawler import CrawlerProcess


class AlxSpider(scrapy.Spider):
    name = "alx_spider"
    allowed_domain = "intranet.alxswe.com"
    handle_httpstatus_list = [404, 410, 301, 500]

    def __init__(
        self, url, email, password, callback=None, *args, **kwargs
    ) -> None:
        super(AlxSpider).__init__(*args, **kwargs)
        self.url = url
        self.email = email
        self.password = password
        self.callback = callback

    def start_requests(self):
        yield scrapy.Request(self.url, callback=self.parse, dont_filter=True)

    def parse(self, response):
        if "auth/sign_in" in response.url:
            yield from self.parse_login(response)

        else:
            project_item = AlxProjectItem()

            # -- Project
            project_item["title"] = response.css("h1.gap::text").get()
            # project_item["compilation"] = response.css(
            #     'h3:contains("Compilation") + * + pre code::text'
            # ).get()

            # -- Tags
            react_props = response.css(
                'div[data-react-class="tags/Tags"]::attr(data-react-props)'
            ).get()
            tags_data = json.loads(react_props) if react_props else {}
            project_item["tags"] = [
                tag["value"] for tag in tags_data.get("tags", [])
            ]

            # -- ProjectMetadata
            react_props = response.css(
                'div[data-react-class="projects/ProjectMetadata"]\
                ::attr(data-react-props)'
            ).get()
            metadata_data = json.loads(react_props) if react_props else {}
            project_item["members"] = (
                metadata_data.get("metadata", {})
                .get("team", {})
                .get("members", [])
            )

            project_item["requirements"] = response.css(
                'h2:contains("Requirements") + * + ul'
            ).extract()

            # -- Tasks
            tasks = []
            for _, task in enumerate(response.css("div[id^=task-num-]")):
                task_item = AlxTaskItem()

                # -- Heading
                task_item["type"] = task.css(
                    ".label-info::text"
                ).extract_first()
                task_item["title"] = task.css(
                    ".panel-title::text"
                ).extract_first()

                # -- Body
                task_item["prototype"] = task.css(
                    ".panel-body ul li:contains('Prototype:') code::text"
                ).extract()
                task_item["body"] = (
                    task.css(
                        ".panel-body > .task_progress_score_bar ~ *"
                    ).extract()
                    if task.css(
                        ".panel-body > .task_progress_score_bar ~ *"
                    ).extract()
                    != []
                    else task.css(".panel-body > #user_id ~ *").extract()
                )

                # -- Group
                task_item["github_repository"] = task.css(
                    ".list-group-item > ul > li:contains('GitHub repository:')\
                    code::text"
                ).get()
                task_item["directory"] = task.css(
                    ".list-group-item > ul > li:contains('Directory:')\
                    code::text"
                ).get()
                task_item["file"] = task.css(
                    ".list-group-item > ul > li:contains('File:') code::text"
                ).extract_first()

                tasks.append(dict(task_item))

            project_item["tasks"] = tasks

            project_dict = dict(project_item)
            yield project_dict

            if self.callback is not None:
                self.callback(project_dict)

    def parse_login(self, response):
        authenticity_token = response.css(
            "form input[name=authenticity_token]::attr(value)"
        ).extract_first()

        login_payload = {
            "user[email]": self.email,
            "user[password]": self.password,
            "authenticity_token": authenticity_token,
        }

        yield scrapy.FormRequest.from_response(
            response, formdata=login_payload, callback=self.after_login
        )

    def after_login(self, response):
        if "signed_in" in response.text:
            yield scrapy.Request(
                url=self.url, callback=self.parse, dont_filter=True
            )

        else:
            alert = response.css(".alert.alert-danger::text").get()

            if alert is not None:
                raise CloseSpider(alert)

            status_errors = {
                404: "Page not found (404)",
                410: "Gone (410)",
                301: "Moved Permanently (301)",
                500: "Internal Server Error (500)",
            }

            if response.status in status_errors:
                error_message = (
                    f"{status_errors[response.status]} for URL: {response.url}"
                )

            else:
                error_message = f"Unexpected error (HTTP {response.status})\
                for URL: {response.url}"

            raise CloseSpider(error_message)


class AlxPipeline:
    """Scrapy pipeline to process and export scraped data."""

    def process_item(self, item, spider):
        """Process a scraped item."""

        # Determine project's main directory
        item["directory"] = self.get_main_directory(item)
        item["members"] = [name.title() for name in item.get("members", [])]

        # Filter and clean scraped tasks
        filtered_tasks = []
        for task in item.get("tasks", []):
            task["file"] = self.split_files(task)
            task["test"] = self.extract_test_files(task)
            task["compilation"] = self.extract_compilation_command(task)
            task["body"] = self.clean_markdown_body(task)

            cleaned_task = self.strip_strings(task)
            filtered_task = self.filter_null_values(cleaned_task)
            filtered_tasks.append(filtered_task)

        item["tasks"] = filtered_tasks
        item["requirements"] = self.extract_requirements(item)

        # item = {
        #     key: (value.strip() if isinstance(value, str) else value)
        #     for key, value in item.items()
        # }

        cleaned_item = self.strip_strings(item)
        filtered_item = self.filter_null_values(cleaned_item)
        return filtered_item

    def get_main_directory(self, item) -> str:
        """Get the main directory for the scraped item."""

        tasks = item.get("tasks", [])
        if tasks:
            first_task = tasks[0]
            github_repo_count = sum(
                1 for task in tasks if task.get("github_repository", "")
            )
            directory_count = sum(
                1 for task in tasks if task.get("directory", "")
            )

            tags = item.get("tags", [])
            if github_repo_count > directory_count or "Group project" in tags:
                return first_task.get("github_repository", "")

            return first_task.get("directory", "")

        return ""

    def extract_requirements(self, item) -> dict:
        """Extract requirements from the item."""

        requirements = {}
        for paragraph in item.get("requirements", []):
            paragraph = markdownify(paragraph)

            header_match = re.search(r"(\d*-?[A-Za-z0-9_]+\.h)", paragraph)
            if header_match:
                requirements["header"] = header_match.group(1)

            readme_match = re.search(r"(\d*-?README\.md)", paragraph)
            if readme_match:
                requirements["readme.md"] = readme_match.group(1)

        return requirements

    def split_files(self, task) -> list:
        """Split files if comma-separated."""

        files = task.get("file", "")
        return files.split(", ") if files else []

    def clean_markdown_body(self, task: dict) -> list:
        """Clean the markdown body of a given task."""

        cleaned_body = []

        for paragraph in task.get("body", []):
            paragraph = markdownify(
                paragraph, code_language="console", bullets="*"
            )
            paragraph = re.sub(r"\t", "  ", paragraph)
            paragraph = re.sub(r"\n{2,}", "\n", paragraph)
            paragraph = re.sub(r"\n```console", "```console", paragraph)
            paragraph = re.sub(r"```\n", "```", paragraph)
            cleaned_body.extend(paragraph.split("\n"))

        return cleaned_body

    def extract_test_files(self, task: dict) -> list:
        """Extract test files based on the task's content."""

        test_files = []

        for paragraph in task.get("body", []):
            match = re.search(r"cat (?!-)([^ \n]+)", paragraph)

            if match:
                test_file = match.group(1)
                lines = paragraph.split("\n")
                start_index, end_index = 0, len(lines)

                for index, line in enumerate(lines):

                    if match.group(0) in line:
                        start_index = index + 1
                        break

                for index in range(start_index, end_index):
                    lines[index] = html.unescape(lines[index])

                    if "$" in lines[index] or "</code>" in lines[index]:
                        end_index = index
                        break

                test_file_content = lines[start_index:end_index]
                test_files.append(
                    {
                        "file": test_file,
                        "content": test_file_content,
                    }
                )

        return test_files

    def extract_compilation_command(self, task: dict) -> str:
        """Extract compilation command based on the task's content."""

        compilation_command = ""

        for paragraph in task.get("body", []):
            paragraph = markdownify(
                paragraph, code_language="console", bullets="*"
            )
            paragraph = re.sub(r"\t", "  ", paragraph)

            gcc_commands = re.findall(r"gcc .+", paragraph)
            if gcc_commands:
                gcc_commands = [
                    html.unescape(command) for command in gcc_commands
                ]
                compilation_command = (
                    " && ".join(gcc_commands)
                    if len(gcc_commands) > 1
                    else "".join(gcc_commands)
                )

        return compilation_command

    def strip_strings(self, obj) -> Union[str, list, dict]:
        """
        Recursively iterate through a dictionary, list, or string and apply
        the `strip()` method to string values.
        """

        def _strip_dict(d: dict) -> dict:
            """
            Recursively strip string values in a dictionary.
            """

            return {
                key: (
                    self.strip_strings(value)
                    # Don't strip keys that contain test code
                    if key != "content" and isinstance(value, str)
                    else value
                )
                for key, value in d.items()
            }

        def _strip_list(lst) -> list:
            """
            Recursively strip string values in a list.
            """

            return [
                self.strip_strings(item) if isinstance(item, str) else item
                for item in lst
            ]

        if isinstance(obj, str):
            return obj.strip()

        elif isinstance(obj, list):
            return _strip_list(obj)

        elif isinstance(obj, dict):
            return _strip_dict(obj)

        else:
            return obj

    def filter_null_values(self, obj) -> Union[dict, list]:
        """
        Recursively iterate through a dictionary and filter out keys with null
        values (None or empty string).
        """

        def _filter_dict(d: dict) -> dict:
            """
            Filter out keys with null values (None or empty string) from a
            dictionary.
            """

            return {
                key: value
                for key, value in d.items()
                if value is not None and value != [] and value != ""
            }

        def _filter_list(lst: list) -> list:
            """
            Recursively filter out keys with null values (None or empty string)
            from a list of dictionaries.
            """

            return [
                _filter_dict(item) if isinstance(item, dict) else item
                for item in lst
            ]

        if isinstance(obj, dict):
            return _filter_dict(obj)

        elif isinstance(obj, list):
            return _filter_list(obj)

        else:
            return obj


class AlxProjectItem(scrapy.Item):
    """Scrapy Item class to represent information about an ALX project."""

    title = scrapy.Field()
    tags = scrapy.Field()
    members = scrapy.Field()
    tasks = scrapy.Field()
    directory = scrapy.Field()
    requirements = scrapy.Field()
    # compilation = scrapy.Field()


class AlxTaskItem(scrapy.Item):
    """Scrapy Item class to represent information about an ALX task."""

    type = scrapy.Field()
    title = scrapy.Field()
    body = scrapy.Field()
    prototype = scrapy.Field()
    github_repository = scrapy.Field()
    directory = scrapy.Field()
    file = scrapy.Field()
    test = scrapy.Field()
    compilation = scrapy.Field()


if __name__ == "__main__":
    try:
        config_file_path = Path("~/.alxconfig").expanduser()
        alx_config = Config(RepositoryEnv(config_file_path))

        user_email = alx_config("EMAIL")
        user_password = alx_config("PASSWORD")

        project_id = str(input("Project ID: "))
        project_url = f"https://intranet.alxswe.com/projects/{project_id}"

        process = CrawlerProcess(
            {
                "FEEDS": {
                    "alx_project.json": {
                        "format": "json",
                        "encoding": "utf-8",
                        "store_empty": False,
                        "fields": None,
                        "indent": 4,
                        "item_export_kwargs": {"export_empty_fields": True},
                        "overwrite": True,
                    }
                },
                "ITEM_PIPELINES": {
                    "myalx.spider.AlxPipeline": 100,
                },
                "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
                "LOG_LEVEL": "INFO",
            }
        )
        process.crawl(
            AlxSpider,
            url=project_url,
            email=user_email,
            password=user_password,
        )
        process.start()

    except Exception as e:
        print(f"Error occurred: {e}")
        raise e
