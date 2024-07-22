# [Data] Create or Update a GitHub Status Check

GitHub Action to create a new GitHub Status check or update an existing one with specified details.

## Inputs

### `check-run-id`

- **Description**: The ID of the check to update. Will create a new check and return the ID if blank.
- **Required**: No

### `name`

- **Description**: The name of the check.
- **Required**: Yes

### `status`

- **Description**: The status of the check (`queued`, `in_progress`, or `completed`).
- **Required**: No
- **Default**: `in_progress`

### `title`

- **Description**: The title to put on the check panel.
- **Required**: Yes

### `summary`

- **Description**: The summary of the check runs current result.
- **Required**: Yes

### `details`

- **Description**: The details for the check.
- **Required**: No

### `conclusion`

- **Description**: The conclusion of the check.
- **Required**: No

## Outputs

### `check-run-id`

- **Description**: The check run ID of the updated or created check.
- **Value**: `${{ steps.create-check.outputs.result || steps.update-check.outputs.result }}`

## Usage

```yaml
name: Example Workflow

on: [push]

jobs:
  create-or-update-check:
    runs-on: ubuntu-latest
    steps:
      - name: Create or Update Check
        id: status-check
        uses: UKHSA-Internal/devops-github-actions/.github/actions/github-status-check@main
        with:
          name: 'Example Check'
          status: 'in_progress'
          title: 'Example Title'
          summary: 'Example summary of the check runs current result'
          details: |
            Example detailed information about the check
          conclusion: ''
      - name: Update Check
        uses: UKHSA-Internal/devops-github-actions/.github/actions/github-status-check@main
        with:
          check-run-id: ${{ steps.status-check.outputs.check-run-id }}
          name: 'Example Check'
          status: 'completed'
          title: 'Example Title'
          summary: 'Example summary of the check runs current result'
          details: |
            Example detailed information about the check
          conclusion: 'success'
