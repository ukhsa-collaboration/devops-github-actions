# Parse Terraform Version

This GitHub action parses a `terraform.tf` file to extract the required Terraform version and returns the highest version that satisfies the [Terraform constraints](https://developer.hashicorp.com/terraform/language/expressions/version-constraints) specified in the file.

## Usage

To use this action in your GitHub workflows, add the following step to your workflow YAML file:

```yaml
- name: Find Terraform version
  uses: UKHSA-Internal/devops-github-actions/.github/actions/parse-terraform-version@main
  id: terraform_version
  with:
    tf_file: "${{ matrix.directory }}/terraform.tf"
```

## Inputs

    tf_file: The path to the terraform.tf file. This input is required.

## Outputs

    tf_version: The highest Terraform version that satisfies the constraints specified in the terraform.tf file.

## Example Workflow

```yaml
name: Extract Terraform Version

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main

jobs:
  extract-version:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Find Terraform version
        id: terraform_version
        uses: UKHSA-Internal/devops-github-actions/.github/actions/parse-terraform-version@main

      - name: Output Terraform version
        run: echo "Terraform version: ${{ steps.terraform_version.outputs.tf_version }}"
```
