#!/usr/bin/python3
import os
import json
import logging
import argparse
from jsonschema import validate, ValidationError

LOG_LEVEL = os.getenv("LOG_LEVEL", "CRITICAL").upper()
logger = logging.getLogger(__name__)
logging.basicConfig(level=LOG_LEVEL)

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--draw", action="store_true")
parser.add_argument("-r", "--reverse", action="store_true", help="Reverse the outputted list of stacks")
args = parser.parse_args()
DRAW_GRAPH = args.draw
REVERSE_OUTPUT = args.reverse
DEFAULT_RUNNER_LABEL = "ubuntu-latest"

JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Dependencies Schema",
    "type": "object",
    "properties": {
        "dependencies": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                }
            },
            "required": ["paths"],
        },
        "runner-label": {
            "type": "string",
            "default": DEFAULT_RUNNER_LABEL
        },
        "planned-changes": {
            "type": "boolean",
            "default": True
        },
        "order": {
            "type": "integer",
            "default": 1
        },
        "skip_when_destroying": {
            "type": "boolean",
            "default": False
        }
    },
    "required": ["dependencies"],
}

try:
    from gvgen import GvGen
except ImportError:
    logger.warning("Unable to import Gvgen. DOT files cannot be created")
else:
    g = GvGen()


class Node:
    def __init__(self, name: str, base_dir: str, runner_label=DEFAULT_RUNNER_LABEL, planned_changes=True, skip_when_destroying=False):
        self.name = name
        self.runner_label = runner_label
        self.planned_changes = planned_changes
        self.skip_when_destroying = skip_when_destroying
        self.edges = []
        self.valid_dir = self._verify_dir_exists(base_dir)
        logger.debug(f"{name} was created as a Node object!")

        if DRAW_GRAPH:
            try:
                self.graph_item = g.newItem(name)
                logger.debug(f"Added {name} as gvgen item")
            except NameError:
                logger.debug(f"Unable to add as gvgen item")
                pass

    def _verify_dir_exists(self, base_dir):
        return os.path.isdir(os.path.join(base_dir, self.name))

    def add_edge(self, edge):
        """
        Add an edge (dependency) to the node.

        Args:
            edge (Node): The node to add as a dependency.
        """
        self.edges.append(edge)
        if DRAW_GRAPH:
            try:
                g.newLink(self.graph_item, edge.graph_item)
            except NameError:
                pass
        logger.debug(f"Added {edge.name} as edge to node {self.name}")

    def dep_resolve(self, resolved, seen=[]):
        """
        Resolve dependencies recursively starting from this node using a DFS algorithm.

        Args:
            resolved (list): List to store resolved nodes in topological order.
            seen (list, optional): List to track nodes that have been visited to detect cycles. Defaults to [].

        Raises:
            Exception: If a circular reference is detected.
        """
        seen.append(self)
        for edge in self.edges:
            if edge not in resolved:
                if edge in seen:
                    raise Exception(
                        f"Circular reference detected: {self.name} -> {edge.name}"
                    )
                edge.dep_resolve(resolved, seen)
        resolved.append(self)


class Graph:
    def __init__(self, base_dir: str):
        self.nodes = {}
        self.base_dir = base_dir

    def add_node(self, stack_dir: str, dependencies: list, runner_label=DEFAULT_RUNNER_LABEL, planned_changes=True, skip_when_destroying=False):
        """
        Add a node to the graph.

        Args:
            stack_dir (str): Path to the directory which the Node represents.
            dependencies (list): A list of dependencies extracted from the dependencies.json file
            runner_label (str): The runner label associated with this stack.
            planned_changes (bool): Boolean value to determine if terraform changes are required, or not.

        Raises:
            Exception: Raises an exception if a dependency is referenced in the dependencies.json but has no physical directory
        """
        if stack_dir not in self.nodes:
            self.nodes[stack_dir] = Node(stack_dir, 
                                         self.base_dir, 
                                         runner_label=runner_label, 
                                         planned_changes=planned_changes)
            logger.debug(f"Node '{stack_dir}' added with runner_label '{runner_label}'")
        else:
            # Node already exists through previous stack dependency adding the node, which would use the default values.
            # Now update the runner_label when processing stack's own dependencies.json file.
            node = self.nodes[stack_dir]
            if node.runner_label != runner_label:
                logger.warning(
                    f"Runner label mismatch for '{stack_dir}'. "
                    f"Existing: '{node.runner_label}', New: '{runner_label}'. Updating to new value."
                )
                node.runner_label = runner_label
            
            if node.planned_changes != planned_changes:
                logger.warning(
                    f"Runner label mismatch for '{stack_dir}'. "
                    f"Existing: '{node.planned_changes}', New: '{planned_changes}'. Updating to new value."
                )
                node.planned_changes = planned_changes

            if node.skip_when_destroying != skip_when_destroying:
                logger.warning(
                    f"skip_when_destroying mismatch for '{stack_dir}'. "
                    f"Existing: '{node.skip_when_destroying}', New: '{skip_when_destroying}'. Updating to new value."
                )
                node.skip_when_destroying = skip_when_destroying  
        
        node = self.nodes[stack_dir]
        for dep in dependencies:
            if dep not in self.nodes:
                self.nodes[dep] = Node(dep, self.base_dir)
            if not self.nodes[dep].valid_dir:
                raise Exception(
                    f"Unknown dependency detected: non-existent {dep} found in {stack_dir}/dependencies.json"
                )
            node.add_edge(self.nodes[dep])

    def resolve_dependencies(self):
        """
        Resolve dependencies recursively starting from the first node in the nodes attribute.

        Returns:
            list: List of resolved dependencies
        """
        resolved = []
        for node in self.nodes.values():
            node.dep_resolve(resolved)
        return resolved

    def generate_dot_file(self):
        """
        Generate DOT file for creating a visual representation of the graph

        Returns:
            str: DOT-representation of the graph
        """
        try:
            return g.dot()
        except NameError:
            logger.critical(
                "Install gvgen via pip to generate a DOT file of this graph"
            )

    def topological_sort(self, reverse=False):
        """
        Perform topological sorting of nodes in required order of deploy.

        Args:
            reverse (bool): Whether to reverse the sorted order.

        Returns:
            list: List of Node objects in topologically sorted order.
        """
        sorted_nodes = []
        visited = set()

        def visit(node):
            if node in visited:
                return
            visited.add(node)
            for edge in node.edges:
                visit(edge)
            sorted_nodes.append(node)

        for node in self.nodes.values():
            visit(node)

        if reverse:
            return list(reversed(sorted_nodes))
        else:
            return sorted_nodes


def find_stack_directories(start_dir, max_depth=2):
    """
    Find all Terraform stacks within specified depth in the directory tree.

    Args:
        start_dir (str): The starting directory to search from.
        max_depth (int, optional): Maximum depth to search in the directory tree. Defaults to 2.

    Returns:
        list: List of file paths to Terraform stack directories found.
    """
    results = []
    for root, _, files in os.walk(start_dir):
        depth = root[len(start_dir) :].count(os.sep)
        if depth > max_depth:
            continue
        if "dependencies.json" in files:
            results.append(os.path.join(root, "dependencies.json"))
    return results


def extract_dependencies_from_file(file_path):
    """
    Extract configuration from a 'dependencies.json' file.

    Args:
        file_path (str): Path to the 'dependencies.json' file.

    Returns:
        dict: A dictionary containing:
            - 'paths': List of dependency paths.
            - 'runner-label': The dependent GitHub runner label the stack should run from.
            - 'planned-changes': Used to store dynamic value on whether Terraform changes are planned, or not.
    """
    with open(file_path, "r") as file:
        try:
            data = json.load(file)
            validate(data, JSON_SCHEMA)
        except ValidationError as e:
            raise ValidationError(f"{file_path} failed to validate against the JSON schema: {e.message}") from e
        except json.decoder.JSONDecodeError as e:
            raise ValidationError(f"{file_path} contains invalid JSON: {e.msg}") from e
        
        planned_changes = data.get("planned-changes", True)
        skip_when_destroying = data.get("skip_when_destroying", False)
        runner_label = data.get("runner-label", DEFAULT_RUNNER_LABEL)
        
        if runner_label not in [DEFAULT_RUNNER_LABEL, "self-hosted"]:
            raise ValidationError(
                f"Invalid runner-label '{runner_label}' in {file_path}. "
                "Must be {DEFAULT_RUNNER_LABEL} or 'self-hosted'."
            )

        data["planned-changes"] = planned_changes
        data["runner-label"] = runner_label
        data["skip_when_destroying"] = skip_when_destroying
        dependencies = data["dependencies"]["paths"]
        
        return {
            "paths": dependencies,
            "runner-label": runner_label,
            "planned-changes": planned_changes,
            "skip_when_destroying": skip_when_destroying
        }


def process_stack_files(base_dir):
    """
    Processes stack directories and adds nodes to a graph

    Args:
        base_dir (str): The base directory containing all of the Terraform stacks.

    Returns:
        Graph: A graph object representing all of the stacks found
    """
    graph = Graph(base_dir)
    stack_files = find_stack_directories(base_dir, max_depth=2)
    for file_path in stack_files:
        if file_path.endswith("dependencies.json"):
            stack_dir = f"./{os.path.relpath(os.path.dirname(file_path), base_dir)}"
            dependencies_info = extract_dependencies_from_file(file_path)
            dependencies = dependencies_info["paths"]
            runner_label = dependencies_info["runner-label"]
            planned_changes = dependencies_info["planned-changes"]
            skip_when_destroying = dependencies_info["skip_when_destroying"]
            graph.add_node(stack_dir, dependencies, runner_label=runner_label, planned_changes=planned_changes, skip_when_destroying=skip_when_destroying)

    return graph


if __name__ == "__main__":
    start_dir = os.getcwd()

    graph = process_stack_files(start_dir)
    resolved = graph.resolve_dependencies()
    sorted_nodes = graph.topological_sort(reverse=REVERSE_OUTPUT)

    if DRAW_GRAPH:
        graph.generate_dot_file()

    # Output the matrix with 'directory', 'runner_label' and 'planned_changes'.
    matrix = [
        {
            "directory": node.name, 
            "runner_label": node.runner_label, 
            "planned_changes": node.planned_changes,
            "order": index + 1,
            "skip_when_destroying": node.skip_when_destroying
        }
        for index, node in enumerate(sorted_nodes)
    ]

    print(json.dumps(matrix))