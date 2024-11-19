import unittest
import tempfile
import shutil
import json
import os
from main import (
    find_stack_directories,
    extract_dependencies_from_file,
    process_stack_files,
)

class TestDependencyResolver(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_dir(self, dir_name):
        path = os.path.join(self.test_dir, dir_name)
        os.makedirs(path, exist_ok=True)
        return path

    def write_json(self, dir_name, paths_content, runner_label=None, planned_changes=None, valid_json=True):
        """
        Writes JSON to dependencies.json in dir_name.
        If valid_json is False, writes arbitrary content to simulate malformed JSON.
        """
        path = os.path.join(self.test_dir, dir_name, "dependencies.json")
        self.create_dir(os.path.dirname(path))
        if valid_json:
            json_content = {"dependencies": {"paths": paths_content}}
            if runner_label is not None:
                json_content["runner-label"] = runner_label
            if planned_changes is not None:
                json_content["planned-changes"] = planned_changes
        else:
            json_content = paths_content  # Malformed content
        with open(path, "w") as f:
            json.dump(json_content, f)

    def test_circular_dependency(self):
        """Test that circular dependencies raise an exception."""
        self.write_json("stack1", ["./stack2"])
        self.write_json("stack2", ["./stack3"])
        self.write_json("stack3", ["./stack1"])

        graph = process_stack_files(self.test_dir)

        with self.assertRaises(Exception) as context:
            graph.resolve_dependencies()
        self.assertIn("Circular reference detected", str(context.exception))

    def test_missing_dependencies_json(self):
        """Test that situations with no stacks are handled gracefully."""
        graph = process_stack_files(self.test_dir)
        resolved = graph.resolve_dependencies()
        self.assertEqual(len(resolved), 0)

    def test_sorting_order(self):
        """Ensure stacks are returned in expected order with correct runner labels and planned changes."""
        self.write_json("stack1", ["./stack3"], runner_label="ubuntu-latest", planned_changes=True)
        self.write_json("stack2", ["./stack1"], runner_label="self-hosted", planned_changes=False)
        self.write_json("stack3", ["./stack4"])
        self.write_json("stack4", [], planned_changes=True)

        graph = process_stack_files(self.test_dir)
        graph.resolve_dependencies()
        sorted_nodes = graph.topological_sort()

        expected_order = ["./stack4", "./stack3", "./stack1", "./stack2"]
        expected_runner_labels = ["ubuntu-latest", "ubuntu-latest", "ubuntu-latest", "self-hosted"]
        expected_planned_changes = [True, True, True, False]

        self.assertEqual(
            [node.name for node in sorted_nodes],
            expected_order,
        )
        self.assertEqual(
            [node.runner_label for node in sorted_nodes],
            expected_runner_labels,
        )
        self.assertEqual(
            [node.planned_changes for node in sorted_nodes],
            expected_planned_changes,
        )

    def test_sorting_order_reverse_output(self):
        """Ensure stacks are returned in expected reverse order with correct runner labels and planned changes."""
        self.write_json("stack1", ["./stack3"], runner_label="ubuntu-latest", planned_changes=True)
        self.write_json("stack2", ["./stack1"], runner_label="self-hosted", planned_changes=False)
        self.write_json("stack3", ["./stack4"], planned_changes=True)
        self.write_json("stack4", [], planned_changes=False)

        graph = process_stack_files(self.test_dir)
        graph.resolve_dependencies()
        sorted_nodes = graph.topological_sort(reverse=True)

        expected_order = ["./stack2", "./stack1", "./stack3", "./stack4"]
        expected_runner_labels = ["self-hosted", "ubuntu-latest", "ubuntu-latest", "ubuntu-latest"]
        expected_planned_changes = [False, True, True, False]

        self.assertEqual(
            [node.name for node in sorted_nodes],
            expected_order,
        )
        self.assertEqual(
            [node.runner_label for node in sorted_nodes],
            expected_runner_labels,
        )
        self.assertEqual(
            [node.planned_changes for node in sorted_nodes],
            expected_planned_changes,
        )

    def test_multiple_stacks_no_dependencies(self):
        """Ensure multiple stacks with no dependencies don't cause errors and default values are assigned."""
        self.write_json("stack1", [], runner_label="self-hosted", planned_changes=False)
        self.write_json("stack2", [])
        self.write_json("stack3", ["./stack1"], planned_changes=True)

        graph = process_stack_files(self.test_dir)
        graph.resolve_dependencies()
        sorted_nodes = graph.topological_sort()

        self.assertEqual(len(sorted_nodes), 3)
        self.assertIn("./stack1", [node.name for node in sorted_nodes])
        self.assertIn("./stack2", [node.name for node in sorted_nodes])
        self.assertIn("./stack3", [node.name for node in sorted_nodes])

        # Check runner labels and planned changes
        node_dict = {node.name: (node.runner_label, node.planned_changes) for node in sorted_nodes}
        self.assertEqual(node_dict["./stack1"], ("self-hosted", False))
        self.assertEqual(node_dict["./stack2"], ("ubuntu-latest", True))
        self.assertEqual(node_dict["./stack3"], ("ubuntu-latest", True))

    def test_dependency_not_exist(self):
        """Ensure exception is raised when a stack references a dependency with a non-existent directory."""
        self.write_json("stack1", ["./stack2"])

        with self.assertRaises(Exception) as context:
            process_stack_files(self.test_dir)
        self.assertIn("Unknown dependency detected", str(context.exception))

    def test_non_schema_dependencies_file(self):
        """Ensure exception is raised when dependencies.json doesn't meet the JSON schema."""
        self.write_json("stack1", {"foo": {"bar": "hello"}}, valid_json=False)

        json_files = find_stack_directories(self.test_dir, max_depth=2)
        for file_path in json_files:
            with self.assertRaises(Exception) as context:
                extract_dependencies_from_file(file_path)
            self.assertIn(
                "failed to validate against the JSON schema", str(context.exception)
            )

    def test_malformed_dependencies_file(self):
        """Ensure exception is raised when dependencies.json is malformed (invalid JSON)."""
        self.write_json("stack1", "invalid_json_content", valid_json=False)

        json_files = find_stack_directories(self.test_dir, max_depth=2)
        for file_path in json_files:
            with self.assertRaises(Exception) as context:
                extract_dependencies_from_file(file_path)
            self.assertIn("failed to validate against the JSON schema", str(context.exception))

    def test_standalone_stack_ignored(self):
        """Ensure that standalone stacks without dependencies.json are ignored."""
        self.write_json("stack1", ["./stack3"])
        self.write_json("stack2", ["./stack1"])
        self.write_json("stack3", ["./stack4"])
        self.write_json("stack4", [])
        stack_99_path = self.create_dir("stack99")

        with open(f"{stack_99_path}/main.tf", "w"):
            pass  # Create an empty main.tf

        graph = process_stack_files(self.test_dir)
        graph.resolve_dependencies()
        sorted_nodes = graph.topological_sort()

        self.assertEqual(len(sorted_nodes), 4)
        self.assertIn("./stack1", [node.name for node in sorted_nodes])
        self.assertIn("./stack2", [node.name for node in sorted_nodes])
        self.assertIn("./stack3", [node.name for node in sorted_nodes])
        self.assertIn("./stack4", [node.name for node in sorted_nodes])
        self.assertNotIn("./stack99", [node.name for node in sorted_nodes])

    def test_file_name_in_validation_exception(self):
        """Ensure the problematic file name is displayed when raising a JSON data validation exception."""
        self.write_json("stack1", "invalid_content", valid_json=False)

        json_files = find_stack_directories(self.test_dir, max_depth=2)
        for file_path in json_files:
            with self.assertRaises(Exception) as context:
                extract_dependencies_from_file(file_path)
            self.assertIn(f"stack1", str(context.exception))
            self.assertIn(f"dependencies.json", str(context.exception))

    def test_runner_label_default_value(self):
        """Test that when 'runner-label' is missing, it defaults to 'ubuntu-latest'."""
        self.write_json("stack1", ["./stack2"])  # No 'runner-label' specified
        self.write_json("stack2", [], runner_label="self-hosted")

        graph = process_stack_files(self.test_dir)
        graph.resolve_dependencies()
        sorted_nodes = graph.topological_sort()

        node_dict = {node.name: node.runner_label for node in sorted_nodes}
        self.assertEqual(node_dict["./stack1"], "ubuntu-latest")  # Default value
        self.assertEqual(node_dict["./stack2"], "self-hosted")

    def test_runner_label_invalid_value(self):
        """Test that invalid 'runner-label' values raise a ValidationError."""
        self.write_json("stack1", [], runner_label="invalid-runner")

        json_files = find_stack_directories(self.test_dir, max_depth=2)
        for file_path in json_files:
            with self.assertRaises(Exception) as context:
                extract_dependencies_from_file(file_path)
            self.assertIn(
                "Invalid runner-label 'invalid-runner'", str(context.exception)
            )

    def test_runner_label_in_output(self):
        """Test that the final output includes the correct 'runner-label's."""
        self.write_json("stack1", ["./stack2"], runner_label="ubuntu-latest")
        self.write_json("stack2", [], runner_label="self-hosted")

        graph = process_stack_files(self.test_dir)
        graph.resolve_dependencies()
        sorted_nodes = graph.topological_sort()

        # Simulate the final output
        matrix = [
            {"directory": node.name, "runner_label": node.runner_label}
            for node in sorted_nodes
        ]

        expected_matrix = [
            {"directory": "./stack2", "runner_label": "self-hosted"},
            {"directory": "./stack1", "runner_label": "ubuntu-latest"},
        ]

        self.assertEqual(matrix, expected_matrix)

    def test_runner_label_enum_validation(self):
        """Test that 'runner-label's are validated against the allowed enum values."""
        self.write_json("stack1", [], runner_label="ubuntu-latest")
        self.write_json("stack2", [], runner_label="self-hosted")
        self.write_json("stack3", [], runner_label="windows-latest")  # Invalid runner-label

        json_files = find_stack_directories(self.test_dir, max_depth=2)
        for file_path in json_files:
            if "stack3" in file_path:
                with self.assertRaises(Exception) as context:
                    extract_dependencies_from_file(file_path)
                self.assertIn(
                    "Invalid runner-label 'windows-latest'", str(context.exception)
                )
            else:
                # Should not raise an exception
                extract_dependencies_from_file(file_path)

    def test_planned_changes_default_value(self):
        """Test that when 'planned-changes' is missing, it defaults to True."""
        self.write_json("stack1", ["./stack2"])
        self.write_json("stack2", [], planned_changes=False)

        graph = process_stack_files(self.test_dir)
        graph.resolve_dependencies()
        sorted_nodes = graph.topological_sort()

        node_dict = {node.name: node.planned_changes for node in sorted_nodes}
        self.assertEqual(node_dict["./stack1"], True)
        self.assertEqual(node_dict["./stack2"], False)

    def test_planned_changes_invalid_value(self):
        """Test that invalid 'planned-changes' values raise a ValidationError."""
        self.write_json("stack1", [], planned_changes="true")

        json_files = find_stack_directories(self.test_dir, max_depth=2)
        for file_path in json_files:
            with self.assertRaises(Exception) as context:
                extract_dependencies_from_file(file_path)
            self.assertIn(
                "failed to validate against the JSON schema", str(context.exception)
            )

    def test_planned_changes_in_output(self):
        """Test that the final output includes the correct 'planned-changes' values."""
        self.write_json("stack1", ["./stack2"], planned_changes=True)
        self.write_json("stack2", [], planned_changes=False)

        graph = process_stack_files(self.test_dir)
        graph.resolve_dependencies()
        sorted_nodes = graph.topological_sort()

        # Simulate the final output
        matrix = [
            {
                "directory": node.name,
                "runner_label": node.runner_label,
                "planned_changes": node.planned_changes
            }
            for node in sorted_nodes
        ]

        expected_matrix = [
            {"directory": "./stack2", "runner_label": "ubuntu-latest", "planned_changes": False},
            {"directory": "./stack1", "runner_label": "ubuntu-latest", "planned_changes": True},
        ]

        self.assertEqual(matrix, expected_matrix)

if __name__ == '__main__':
    unittest.main()
