# Checkov Scan GitHub Action

This GitHub Action runs Checkov scans on your Terraform configurations. It supports two types of scans: `deep` and `light`. The `deep` scan requires a Terraform plan file, while the `light` scan runs directly against your Terraform configuration files. If Checkov and/or Python are not already installed, it will install them.

## Inputs

- **scan_type**:

  - **Description**: The type of scan to run against Terraform. Either `deep` or `light`. `Deep` requires a Terraform plan file.
  - **Default**: `light`
  - **Required**: `false`

- **tfplan_file**:

  - **Description**: The filename of the Terraform plan. Required if using `deep` scan_type.
  - **Default**: `tfplan`
  - **Required**: `false`

- **upload_sarif**:

  - **Description**: Upload resulting Sarif file to the GitHub Security tab. *Note*: Regardless of this setting, we this will not currently upload the Sarif file to the Github API until Github Advanced Security is enabled by the UKHSA-Internal organisation. 
  - **Default**: `true`
  - **Required**: `false`

- **scan_directory**:
  - **Description**: The directory to run the scan in or to use as the `REPO_ROOT_FOR_PLAN_ENRICHMENT`.
  - **Default**: `.`
  - **Required**: `false`

## Usage

### Example Workflow

```yaml
name: Checkov Scan

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main

jobs:
  checkov-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Run Checkov scan
        uses: UKHSA-Internal/devops-github-actions/.github/actions/checkov-scan@main
        with:
          scan_type: "light"
          upload_sarif: true
```
