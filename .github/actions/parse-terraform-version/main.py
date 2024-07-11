import re
from packaging import version
import requests
from os import environ, path
import argparse
import logging

LOG_LEVEL = environ.get("LOG_LEVEL", "CRITICAL").upper()
logger = logging.getLogger(__name__)
logging.basicConfig(level=LOG_LEVEL)


def version_compare(v1, v2):
    """
    Compare two versions.

    Args:
        v1 (str): The first version to compare.
        v2 (str): The second version to compare.

    Returns:
        bool: True if v1 is less than or equal to v2, False otherwise.
    """
    return version.parse(v1) <= version.parse(v2)


def pessimistic_match(constraint, ver):
    """
    Check if a version is within a pessimistic constraint.

    Args:
        constraint (str): The pessimistic constraint.
        ver (str): The version to check.

    Returns:
        bool: True if the version matches the pessimistic constraint, False otherwise.
    """
    base_version = re.findall(r"\d+\.\d+", constraint)[-1]
    prefix = ".".join(base_version.split(".")[:-1])
    if ver.startswith(prefix):
        return version_compare(base_version, ver)
    return False


def satisfies_constraint(constraint, ver):
    """
    Check if a version satisfies a constraint.

    Args:
        constraint (str): The version constraint.
        ver (str): The version to check.

    Returns:
        bool: True if the version satisfies the constraint, False otherwise.
    """
    constraint = constraint.strip()
    if constraint.startswith("!="):
        return ver != constraint[2:].strip()
    if constraint.startswith(">="):
        return version_compare(constraint[2:].strip(), ver)
    if constraint.startswith(">"):
        return (
            version_compare(constraint[1:].strip(), ver)
            and ver != constraint[1:].strip()
        )
    if constraint.startswith("<="):
        return version_compare(ver, constraint[2:].strip())
    if constraint.startswith("<"):
        return (
            version_compare(ver, constraint[1:].strip())
            and ver != constraint[1:].strip()
        )
    if constraint.startswith("~>"):
        return pessimistic_match(constraint, ver)
    return ver == constraint.strip() or ver == constraint[1:].strip()


def fetch_all_versions():
    """
    Fetch all Terraform versions from the GitHub API and versions.txt.

    Returns:
        list: A list of all fetched versions.

    Raises:
        requests.RequestException: If there is an error fetching the GitHub releases.
    """
    api_headers = {
        "User-Agent": "TF-VERSION-FETCHER",
        "Accept": "application/vnd.github+json",
    }
    auth_headers = {}
    if environ.get("GITHUB_TOKEN"):
        auth_headers = {
            "Authorization": f"Bearer {environ.get('GITHUB_TOKEN')}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    headers = {**api_headers, **auth_headers}
    url = "https://api.github.com/repos/hashicorp/terraform/releases"

    versions = set()

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        releases = response.json()

        for release in releases:
            if "tag_name" in release:
                version_tag = release["tag_name"].lstrip("v")
                if re.match(r"^\d+\.\d+\.\d+$", version_tag):
                    versions.add(version_tag)
    except requests.RequestException as e:
        logger.error(f"Failed to fetch releases from GitHub: {e}")

    try:
        file_path = path.join(path.dirname(__file__), "terraform_versions.txt")
        with open(file_path, "r") as file:
            for line in file:
                file_version = line.strip()
                if re.match(r"^\d+\.\d+\.\d+$", file_version):
                    versions.add(file_version)
    except FileNotFoundError:
        logger.warning(
            "terraform_versions.txt not found. Proceeding with only the fetched versions."
        )
    except Exception as e:
        logger.error(f"An error occurred while reading 'terraform_versions.txt': {e}")

    return sorted(versions, key=version.parse)


def extract_version_constraints(filename):
    """
    Extract version constraints from a terraform.tf file.

    Args:
        filename (str): The file path of the terraform.tf file to be parsed.

    Returns:
        list: A list of version constraints found in the file.

    Raises:
        FileNotFoundError: If the specified file does not exist.
    """
    version_constraints = []

    try:
        with open(filename, "r") as file:
            content = file.read()
            match = re.search(
                r'terraform\s*{\s*required_version\s*=\s*"([^"]+)"\s*}',
                content,
                re.DOTALL,
            )
            if match:
                version_constraints.append(match.group(1))
    except FileNotFoundError:
        logger.error(f"File '{filename}' not found.")
    except Exception as e:
        logger.error(f"An error occurred while reading '{filename}': {e}")

    return version_constraints


def parse_terraform_version(file_path):
    """
    Parse the terraform.tf file, fetch all Terraform versions, and return the highest version that satisfies the constraints.

    Args:
        file_path (str): The file path of the terraform.tf file to be parsed.

    Returns:
        str: The highest Terraform version that satisfies the constraints.
    """
    version_constraints = extract_version_constraints(file_path)

    if not version_constraints:
        logger.info("No version constraints found.")
        return None

    try:
        exact_version = version_constraints[0].strip("=")
        version.parse(exact_version)
        return exact_version
    except version.InvalidVersion:
        pass

    all_versions = fetch_all_versions()

    filtered_versions = [
        ver
        for ver in all_versions
        if all(satisfies_constraint(c, ver) for c in version_constraints)
    ]

    if not filtered_versions:
        logger.info("No versions found that satisfy the constraints.")
        return None

    highest_version = max(filtered_versions, key=version.parse)
    return highest_version


def main():
    """
    Main function to parse the terraform.tf file, fetch all Terraform versions, and print the highest version that satisfies the constraints.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        required=False,
        help="The file path of the terraform.tf file to be parsed",
        default="./terraform.tf",
    )
    args = parser.parse_args()

    highest_version = parse_terraform_version(args.file)
    if highest_version:
        print(highest_version)


if __name__ == "__main__":
    main()
