import unittest
from unittest.mock import patch, mock_open
from main import (
    version_compare,
    pessimistic_match,
    satisfies_constraint,
    fetch_all_versions,
    extract_version_constraints,
    parse_terraform_version,
)


class TestParseTerraformVersion(unittest.TestCase):

    def test_version_compare(self):
        self.assertTrue(version_compare("0.12.0", "0.12.1"))
        self.assertFalse(version_compare("0.12.1", "0.12.0"))
        self.assertTrue(version_compare("0.12.1", "0.12.1"))

    def test_pessimistic_match(self):
        self.assertTrue(pessimistic_match("~> 1.2", "1.2.3"))
        self.assertTrue(pessimistic_match("~> 1.2", "1.3.0"))

    def test_satisfies_constraint(self):
        self.assertTrue(satisfies_constraint(">= 0.12.0", "0.12.1"))
        self.assertFalse(satisfies_constraint(">= 0.12.1", "0.12.0"))
        self.assertTrue(satisfies_constraint("!= 0.12.1", "0.12.0"))
        self.assertFalse(satisfies_constraint("!= 0.12.0", "0.12.0"))
        self.assertTrue(satisfies_constraint("~> 1.2", "1.2.3"))
        self.assertTrue(satisfies_constraint("~> 1.2", "1.3.0"))

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='terraform { required_version = ">= 0.12.0" }',
    )
    def test_extract_version_constraints(self, mock_file):
        constraints = extract_version_constraints("terraform.tf")
        self.assertEqual(constraints, [">= 0.12.0"])

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='''terraform {
                        required_providers {
                            azurerm = {
                                source  = "hashicorp/azurerm"
                                version = "~> 4.0"
                            }
                        }
                        required_version = ">= 1.9"
                    }''',
    )
    def test_extract_version_constraints_with_providers(self, mock_file):
        constraints = extract_version_constraints("terraform.tf")
        self.assertIn(">= 1.9", constraints)

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='terraform { required_version = ">= 0.12.0" }',
    )
    @patch("requests.get")
    def test_parse_terraform_version(self, mock_get, mock_file):
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"tag_name": "v0.12.1"},
            {"tag_name": "v0.12.0"},
        ]

        version = parse_terraform_version("terraform.tf")
        self.assertEqual(version, "0.12.1")


if __name__ == "__main__":
    unittest.main()
