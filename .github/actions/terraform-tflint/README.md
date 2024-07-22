# TFLint GitHub Action

This GitHub Action runs TFLint to lint your Terraform code, ensuring it adheres to best practices and standards. It also initializes TFLint to download and install necessary plugins based on the provider specified in `provider.tf`.

## Inputs

- `scan_directory`: The directory to run the TFLint scan in. Default is `"."`.

## Outputs

This action does not produce any direct outputs, but it will provide linting feedback through the GitHub Actions interface.

## Usage

To use this action in your GitHub workflow, add the following steps to your workflow file:

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run TFLint
        uses: UKHSA-Internal/devops-github-actions/.github/actions/terraform-tflint@main
        with:
          scan_directory: "./terraform" #Optional
