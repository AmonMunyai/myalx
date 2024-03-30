import re
from pathlib import Path


class FileHandler:
    def __init__(
        self, json_data: dict, handler_name: str, file_extension: str
    ) -> None:
        self._json_data = json_data
        self._handler_name = handler_name
        self.file_extension = file_extension

    def create_and_populate_files(self) -> None:
        """Create and populate files for the project."""

        tasks = self._json_data.get("tasks", [])
        for task in tasks:
            directory = self.get_task_directory(task)

            for task_file in task.get("file", []):
                task_file_path = directory / task_file
                task_file_content = self.get_file_content(task_file_path, task)
                self.write_to_file(directory, task_file, task_file_content)

            tests_directory = directory / "tests"
            for test in task.get("test", []):
                test_file = test.get("file", "")
                test_file_content = test.get("content", "")
                self.write_to_file(
                    tests_directory, test_file, test_file_content
                )

    def get_root_directory(self) -> Path:

        root_directory = self._json_data.get("directory", "")

        if not root_directory:
            return Path.cwd()

        return Path(root_directory)

    def get_task_directory(self, task: dict) -> Path:

        directory = task.get("directory", "")
        root_directory = self.get_root_directory()

        if root_directory.name != directory:
            return root_directory / directory

        return Path(directory)

    def get_file_content(self, path: Path, task) -> list:

        if path.suffix == self.file_extension:
            return self.get_file_content_specific(task)

        return []

    def get_file_content_specific(self, task: dict) -> list:

        raise NotImplementedError(
            "Subclasses must implement get_file_content_specific method"
        )

    def write_to_file(self, directory: Path, name: str, content: list) -> None:

        file_path = directory / name

        if file_path.exists():
            return

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

        if content:
            with file_path.open("w", encoding="utf-8") as f:
                f.write("\n".join(content))

            self.modify_script_file_permissions(file_path)

    def modify_script_file_permissions(self, path: Path) -> None:

        if path.is_file() and self.is_script_file(path):
            with path.open("r") as file:
                line = file.readline()

                if line.strip().startswith("#!"):
                    path.chmod(path.stat().st_mode | 0o111)

    def is_script_file(self, path: Path) -> bool:

        script_extensions = [
            ".py",
            ".sh",
            ".rb",
            ".pl",
            ".php",
            ".js",
            ".java",
            ".cpp",
            ".c",
            ".cs",
        ]

        return path.suffix.lower() in script_extensions or not path.suffix


class BashFileHandler(FileHandler):
    def __init__(self, json_data: dict) -> None:
        super().__init__(json_data, "Bash", ".sh")

    def get_file_content_specific(self, task: dict) -> list:
        return ["#!/bin/bash", ""]


class CFileHandler(FileHandler):
    def __init__(self, json_data: dict) -> None:
        super().__init__(json_data, "C", ".c")

    def create_and_populate_files(self) -> None:
        super().create_and_populate_files()

        root_directory = self.get_root_directory()
        self.create_and_populate_makefile_file(root_directory)
        self.create_and_populate_header_file(root_directory)

    def get_file_content_specific(self, task: dict) -> list:

        c_file_content = []

        requirements = self._json_data.get("requirements", {})
        header_file_name = requirements.get("header", "")

        c_file_content.append(
            f'#include "{header_file_name}"'
            if header_file_name
            else "#include <stdio.h>"
        )

        prototypes = task.get("prototype", [])
        if prototypes:
            for prototype in prototypes:
                match = re.search(r"\w+\s+\**(\w+)\s*\([^)]*\)", prototype)
                if match:
                    function_name = match.group(1)
                    parameters = re.findall(
                        r"\b\w+\s+\**(\w+)\s*(?:,|\))", prototype
                    )

                else:
                    function_name = "function_name"
                    parameters = ["parameterx"]

                c_file_content.extend(
                    [
                        "",
                        "/**",
                        f" * {function_name} - Short description, single line.",
                        *[
                            f" * @{parameter}: Description of parameter {parameter}."
                            for parameter in parameters
                        ],
                        " * ",
                        " * Return: Description of the returned value.",
                        " */",
                        "",
                        f"{re.sub(r';', '', prototype)}",
                        "{",
                        "\t/* your code goes here */",
                        "}",
                        "",
                    ]
                )

        else:
            c_file_content.extend(
                [
                    "",
                    "/**",
                    " * main - Entry point",
                    " * ",
                    " * Return: Always 0 (Success)",
                    " */",
                    "",
                    "int main(void)",
                    "{",
                    "\t/* your code goes here */",
                    "\treturn (0);",
                    "}",
                    "",
                ]
            )

        return c_file_content

    def create_and_populate_makefile_file(self, directory: Path) -> None:
        """Create and populate the Makefile for the project."""

        tags = self._json_data.get("tags", [])
        if self._handler_name not in tags:
            return

        makefile_is_required = False
        makefile_content = [
            "# Makefile for Your Project",
            "",
        ]

        output_filenames = set()

        tasks = self._json_data.get("tasks", [])
        for task in tasks:
            compilation_command = task.get("compilation", "")

            if not compilation_command:
                continue

            makefile_is_required = True

            # Replace file paths in makefile gcc_command
            for test_file in (
                test_file.get("file", "") for test_file in task.get("test", [])
            ):
                if test_file and test_file in compilation_command.strip():
                    pattern = rf"\b{re.escape(test_file)}\b"
                    compilation_command = re.sub(
                        pattern, f"tests/{test_file}", compilation_command
                    )

            # Extract output filenames for cleaning
            matches = re.findall(r"-o\s+(\S+)", compilation_command)
            output_filenames.update(matches)

            for task_file in task.get("file", []):
                task_file_path = directory / task_file

                if task_file_path.suffix == ".c":
                    makefile_content.extend(
                        [
                            f"{task_file_path.stem}:",
                            f"\t{compilation_command}\n",
                        ]
                    )

        if "Group project" in tags:
            makefile_is_required = True
            makefile_content.extend(
                [
                    "all:",
                    "\tgcc -Wall -Werror -Wextra -pedantic -std=gnu89 *.c",
                    "",
                ]
            )

        if output_filenames:
            makefile_content.extend(
                [
                    "clean:",
                    f"\t@rm -rf {' '.join(output_filenames)}",
                    '\t@printf "\e[34mAll clear!\e[0m\\n"',
                    "",
                ]
            )

        if makefile_is_required:
            self.write_to_file(directory, "Makefile", makefile_content)

    def create_and_populate_header_file(self, directory: Path) -> None:

        requirements = self._json_data.get("requirements", {})
        header_file_name = requirements.get("header", "")
        if not header_file_name:
            return

        header_file_name_upper = header_file_name.upper().replace(".", "_")

        header_file_content = [
            f"#ifndef {header_file_name_upper}",
            f"#define {header_file_name_upper}",
            "",
            "/*",
            f" * File: {header_file_name}",
            " * Desc: Header file containing declarations for all functions",
            f" *       used in the {directory.name} directory",
            " */",
            "",
        ]

        putchar_is_required = any(
            "_putchar.c" in task.get("compilation", "").split()
            for task in self._json_data.get("tasks", [])
        )
        if putchar_is_required:
            header_file_content.append("int _putchar(char c);")
            self.create_and_populate_putchar_file(directory)

        for task in self._json_data.get("tasks", []):
            prototypes = task.get("prototype", [])
            for prototype in prototypes:
                header_file_content.append(prototype)

        header_file_content.extend(
            [
                "",
                f"#endif /* {header_file_name_upper} */",
                "",
            ]
        )

        self.write_to_file(directory, header_file_name, header_file_content)

    def create_and_populate_putchar_file(self, directory: Path) -> None:

        putchar_file_content = [
            "#include <unistd.h>",
            "",
            "/**",
            " * _putchar - writes the character c to stdout",
            " * @c: The character to print",
            " *",
            " * Return: On success 1.",
            " * On error, -1 is returned, and errno is set appropriately",
            " */",
            "",
            "int _putchar(char c)",
            "{",
            "\treturn (write(1, &c, 1));",
            "}",
            "",
        ]

        self.write_to_file(directory, "_putchar.c", putchar_file_content)


class PythonFileHandler(FileHandler):
    def __init__(self, json_data: dict) -> None:
        super().__init__(json_data, "Python", ".py")

    def get_file_content_specific(self, task: dict) -> list:

        py_file_content = ["#!/usr/bin/python3"]

        prototypes = task.get("prototype", [])
        for prototype in prototypes:
            py_file_content.extend(
                [
                    "",
                    "",
                    prototype,
                    "    pass",
                ]
            )

        py_file_content.append("")

        return py_file_content


class JavaScriptFileHandler(FileHandler):
    def __init__(self, json_data: dict) -> None:
        super().__init__(json_data, "JavaScript", ".js")

    def get_file_content_specific(self, task: dict) -> list:

        js_file_content = [""]

        return js_file_content


class ProjectCreator:
    def __init__(self, json_data: dict) -> None:
        self._json_data = json_data
        self._handlers = [
            BashFileHandler(json_data),
            PythonFileHandler(json_data),
            CFileHandler(json_data),
            JavaScriptFileHandler(json_data),
        ]

    def start_project(self) -> None:
        """Starts the project creation process."""

        if not self._json_data:
            raise ValueError("No data provided. Project creation aborted.")

        try:
            for handler in self._handlers:
                handler.create_and_populate_files()

            self.create_and_populate_readme_file()
            self.create_and_populate_authors_file()

        except Exception as e:
            print(f"Error occurred during project creation: {e}")
            raise e

    def create_and_populate_readme_file(self) -> None:
        """Create README.md file for the project."""

        requirements = self._json_data.get("requirements", {})
        readme_is_required = requirements.get("readme.md", "")
        if not readme_is_required:
            return

        readme_content = [
            f"# {self._json_data.get('title', '')}",
        ]

        tasks = self._json_data.get("tasks", [])
        for task in tasks:
            readme_content.append(f"\n## {task.get('title')}\n")
            readme_content.extend(task.get("body", []))

        readme_content.extend(
            [
                "",
                "---",
                "",
                "*Please note that this README is dynamically generated and may not always reflect the most up-to-date information about the project.*",
                "",
                "---",
                "",
            ]
        )

        readme_file_handler = FileHandler(self._json_data, "README", ".md")
        directory = readme_file_handler.get_root_directory()
        readme_file_handler.write_to_file(
            directory, "README.md", readme_content
        )

    def create_and_populate_authors_file(self) -> None:
        """Create AUTHORS file for the project."""

        members = self._json_data.get("members", [])
        if members:
            authors_content = [
                "# This file lists all contributors to the repository.",
                "",
                "",
            ]
            authors_content.extend(members)

            authors_file_handler = FileHandler(self._json_data, "AUTHORS", "")
            directory = authors_file_handler.get_root_directory()
            authors_file_handler.write_to_file(
                directory, "AUTHORS", authors_content
            )


if __name__ == "__main__":
    try:
        json_data = {
            "title": "Project Title",
            "tags": ["C"],
            "tasks": [
                {
                    "type": "mandatory",
                    "title": "0. Task 0",
                    "body": [
                        "Task 1 description.",
                        "```console",
                        "command 1",
                        "command 2",
                        "```",
                    ],
                    "github_repository": "repository_name",
                    "directory": "project_directory",
                    "file": ["0-file_name.c"],
                    "test": [
                        {
                            "file": "0-test_file_name.c",
                            "content": ["test_content"],
                        }
                    ],
                },
                {
                    "type": "mandatory",
                    "title": "1. Task 1",
                    "body": [
                        "Task 2 description.",
                        "```console",
                        "command 1",
                        "command 2",
                        "```",
                    ],
                    "github_repository": "repository_name",
                    "directory": "project_directory",
                    "file": ["1-file_name.c"],
                    "test": [
                        {
                            "file": "1-test_file_name.c",
                            "content": ["test_content"],
                        }
                    ],
                },
            ],
            "directory": "project_directory",
        }

        project = ProjectCreator(json_data)
        project.start_project()

    except Exception as e:
        print(f"Error occurred: {e}")
        raise e
