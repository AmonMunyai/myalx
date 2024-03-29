import json
import re
from pathlib import Path


class AlxProject:
    def __init__(self, project_data: dict = {}) -> None:
        """Initialize an AlxProject instance."""
        self.project_data = project_data

    def start(self) -> None:
        """Start a new Alx project."""
        project_dir = Path.cwd() / self.project_data.get("directory", "")
        alx_directory = project_dir / ".alx"
        alx_directory.mkdir(parents=True, exist_ok=True)

        self.create_and_populate_readme_file(project_dir)
        self.create_and_populate_files(project_dir)
        self.create_and_populate_test_files(project_dir)

        tags = self.project_data.get("tags", [])
        metadata = self.project_data.get("metadata", {})

        if "C" in tags:
            self.create_and_populate_makefile(project_dir)
            self.create_and_populate_header_file(project_dir)

        if "Group project" in tags:
            team_members = metadata["team"]["members"]

            with (project_dir / "AUTHORS").open("w", encoding="utf-8") as authors_file:
                authors_file.write(
                    "# This file lists all contributors to the repository.\n\n"
                )
                authors_file.write("\n".join(team_members))

        with (alx_directory / "project.json").open(
            "w", encoding="utf-8"
        ) as project_file:
            json.dump(self.project_data, project_file, ensure_ascii=False, indent=4)

    def create_and_populate_readme_file(self, directory):
        readme_file_path = directory / "README.md"

        readme_content = [
            f"# {self.project_data.get('title', '')}",
        ]

        for task in self.project_data.get("tasks", []):
            readme_content.append(f"\n## {task.get('title')}\n")
            readme_content.extend(task.get("description", []))

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

        with readme_file_path.open("w", encoding="utf-8") as readme_file:
            readme_file.write("\n".join(readme_content))

    def create_and_populate_test_files(self, directory):
        directory = directory / "tests"

        tasks = self.project_data.get("tasks", [])
        for task in tasks:
            test_files = task.get("test_files", [])
            if len(test_files) <= 0:
                continue

            for test_file in test_files:
                test_file_name = test_file.get("filename", "")
                test_file_content = test_file.get("content", "")

                if not test_file_name or not test_file_content:
                    continue

                directory.mkdir(parents=True, exist_ok=True)
                file_path = directory / test_file_name

                for index, line in enumerate(test_file_content):
                    test_file_content[index] = re.sub(
                        r'^#include\s+"(.*)"', r'#include "../\1"', line
                    )

                with file_path.open("w", encoding="utf-8") as file:
                    file.write("\n".join(test_file_content))

    def create_and_populate_files(self, directory):
        tasks = self.project_data.get("tasks", [])

        for task in tasks:
            task_files = task.get("files", [])

            for task_file_name in task_files:
                task_file_content = None
                task_file_path = directory / task_file_name

                if "/" in task_file_name:
                    task_file_path.parent.mkdir(parents=True, exist_ok=True)

                task_file_path.touch()
                if task_file_path.suffix == "":
                    task_file_content = ["#!/bin/bash"]
                    task_file_path.chmod(task_file_path.stat().st_mode | 0o111)

                elif task_file_path.suffix == ".c":
                    task_file_content = self.get_c_file_content(task)

                elif task_file_path.suffix == ".py":
                    task_file_content = ["#!/usr/bin/python3"]
                    # task_file_content = self.get_py_file_content(task)

                if not task_file_content:
                    continue

                with task_file_path.open("w", encoding="utf-8") as task_file:
                    task_file.write("\n".join(task_file_content))

    def get_c_file_content(self, task):
        c_file_content = []

        header_file_name = self.project_data.get("header", "")
        if header_file_name:
            c_file_content.append(f'#include "{header_file_name}"')
        else:
            c_file_content.append("#include <stdio.h>")

        prototypes = task.get("prototypes", [])
        if prototypes:
            for prototype in prototypes:
                match = re.search(r"\w+\s+\**(\w+)\s*\([^)]*\)", prototype)
                if match:
                    function_name = match.group(1)
                    parameters = re.findall(r"\b\w+\s+\**(\w+)\s*(?:,|\))", prototype)
                    c_file_content.extend(
                        [
                            "",
                            "/**",
                            f" * {function_name} - Short description, single line.",
                        ]
                    )

                    for parameter in parameters:
                        c_file_content.extend(
                            [
                                f" * @{parameter}: Description of parameter {parameter}.",
                            ]
                        )

                    c_file_content.extend(
                        [
                            " * ",
                            " * Return: Description of the returned value.",
                            " */",
                            "",
                        ]
                    )
                else:
                    c_file_content.extend(
                        [
                            "",
                            "/**",
                            " * function_name - Short description, single line",
                            " * @parameterx: Description of parameter x",
                            " * ",
                            " * Return: Description of the returned value",
                            " */",
                            "",
                        ]
                    )

                c_file_content.extend(
                    [
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
                ]
            )

        return c_file_content

    def create_and_populate_makefile(self, directory):
        makefile_path = directory / "Makefile"

        makefile_content = [
            "# Makefile for Your Project",
            "",
        ]

        tasks = self.project_data.get("tasks", [])
        output_filenames = set()

        for task in tasks:
            gcc_command = task.get("gcc_command", "")

            if not gcc_command:
                continue

            # Replace file paths in makefile gcc_command
            test_file_names = [
                file.get("filename", "")
                for file in task.get("test_files", [])
                if file.get("filename", "") in gcc_command.strip()
            ]

            if test_file_names:
                for test_file_name in test_file_names:
                    pattern = r"\b" + re.escape(test_file_name) + r"\b"
                    gcc_command = re.sub(
                        pattern, f"tests/{test_file_name}", gcc_command
                    )

            # Extract output filenames for cleaning
            matches = re.findall(r"-o\s+(\S+)", gcc_command)
            output_filenames.update(matches)

            files = task.get("files", [""])
            for file in files:
                file_path = directory / file

                if file_path.suffix == ".c":
                    makefile_content.extend(
                        [
                            f"{file_path.stem}:",
                            f"\t{gcc_command}\n",
                        ]
                    )

        tags = self.project_data.get("tags", [])
        if "Group project" in tags:
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
                ]
            )

        with makefile_path.open("w", encoding="utf-8") as makefile:
            makefile.write("\n".join(makefile_content))

    def create_and_populate_header_file(self, directory):
        header_file_name = self.project_data.get("header", "")

        if not header_file_name:
            return

        header_file_path = directory / header_file_name
        header_file_name_upper = header_file_name.upper().replace(".", "_")
        directory_name = self.project_data.get("directory", "")

        header_file_content = [
            f"#ifndef {header_file_name_upper}",
            f"#define {header_file_name_upper}",
            "",
            "/*",
            f" * File: {header_file_name}",
            " * Desc: Header file containing declarations for all functions",
            f" *       used in the {directory_name} directory",
            " */",
            "",
        ]

        putchar_is_required = any(
            "_putchar.c" in task.get("gcc_command", "").split()
            for task in self.project_data.get("tasks", [])
        )
        if putchar_is_required:
            header_file_content.append("int _putchar(char c);")
            self.create_and_populate_putchar(directory)

        for task in self.project_data.get("tasks", []):
            prototypes = task.get("prototypes", [])
            for prototype in prototypes:
                header_file_content.append(prototype)

        header_file_content.extend(
            [
                "",
                f"#endif /* {header_file_name_upper} */",
            ]
        )

        with header_file_path.open("w", encoding="utf-8") as header_file:
            header_file.write("\n".join(header_file_content))

    def create_and_populate_putchar(self, directory):
        putchar_file_path = directory / "_putchar.c"

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
        ]

        with putchar_file_path.open("w", encoding="utf-8") as putchar_file:
            putchar_file.write("\n".join(putchar_file_content))
