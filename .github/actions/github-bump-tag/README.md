# github-tag-action

A GitHub Action to automatically bump and tag main, on merge, with the latest SemVer formatted version. Based on anothrNick/github-tag-action.

## Usage

```yaml
name: Bump version
on:
  pull_request:
    types:
      - closed
    branches:
      - main

jobs:
  build:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-22.04
    permissions:
      contents: write
    steps:
    - uses: actions/checkout@v4
      with:
        ref: ${{ github.event.pull_request.merge_commit_sha }}
        fetch-depth: '0'

    - name: Bump version and push tag
      uses: UKHSA-Internal/devops-github-actions/.github/actions/github-bump-tag@v1
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        WITH_V: true
```

Is recommended to use on `pull_request` instead of on commit to main.

_NOTE: set the fetch-depth for `actions/checkout@v2` or newer to be sure you retrieve all commits to look for the semver commit message._

### Options

**Environment Variables**

- **GITHUB_TOKEN** **_(required)_** - Required for permission to tag the repo.
- **DEFAULT_BUMP** _(optional)_ - Which type of bump to use when none explicitly provided (default: `minor`).
- **DEFAULT_BRANCH** _(optional)_ - Overwrite the default branch its read from GitHub Runner env var but can be overwritten (default: `$GITHUB_BASE_REF`). Strongly recommended to set this var if using anything else than master or main as default branch otherwise in combination with history full will error.
- **WITH_V** _(optional)_ - Tag version with `v` character.
- **RELEASE_BRANCHES** _(optional)_ - Comma separated list of branches (bash reg exp accepted) that will generate the release tags. Other branches and pull-requests generate versions postfixed with the commit hash and do not generate any tag. Examples: `master` or `.*` or `release.*,hotfix.*,master` ...
- **CUSTOM_TAG** _(optional)_ - Set a custom tag, useful when generating tag based on f.ex FROM image in a docker image. **Setting this tag will invalidate any other settings set!**
- **SOURCE** _(optional)_ - Operate on a relative path under $GITHUB_WORKSPACE.
- **DRY_RUN** _(optional)_ - Determine the next version without tagging the branch. The workflow can use the outputs `new_tag` and `tag` in subsequent steps. Possible values are `true` and `false` (default).
- **GIT_API_TAGGING** _(optional)_ - Set if using git cli or git api calls for tag push operations. Possible values are `false` and `true` (default).
- **INITIAL_VERSION** _(optional)_ - Set initial version before bump. Default `0.0.0`. MAKE SURE NOT TO USE vX.X.X here if combined WITH_V
- **TAG_CONTEXT** _(optional)_ - Set the context of the previous tag. Possible values are `repo` (default) or `branch`.
- **PRERELEASE** _(optional)_ - Define if workflow runs in prerelease mode, `false` by default. Note this will be overwritten if using complex suffix release branches. Use it with checkout `ref: ${{ github.sha }}` for consistency see [issue 266](https://github.com/anothrNick/github-tag-action/issues/266).
- **PRERELEASE_SUFFIX** _(optional)_ - Suffix for your prerelease versions, `beta` by default. Note this will only be used if a prerelease branch.
- **VERBOSE** _(optional)_ - Print git logs. For some projects these logs may be very large. Possible values are `true` (default) and `false`.
- **MAJOR_STRING_TOKEN** _(optional)_ - Change the default `#major` commit message string tag.
- **MINOR_STRING_TOKEN** _(optional)_ - Change the default `#minor` commit message string tag.
- **PATCH_STRING_TOKEN** _(optional)_ - Change the default `#patch` commit message string tag.
- **NONE_STRING_TOKEN** _(optional)_ - Change the default `#none` commit message string tag.
- **BRANCH_HISTORY** _(optional)_ - Set the history of the branch for finding `#bumps`. Possible values `last`, `full` and `compare` defaults to `compare`.
  - `full`: attempt to show all history, does not work on rebase and squash due missing HEAD [should be deprecated in v2 is breaking many workflows]
  - `last`: show the single last commit
  - `compare`: show all commits since previous repo tag number
- **FORCE_WITHOUT_CHANGES** _(optional)_ - Enforce the brach creation even if there are no changes from the tag.
- **FORCE_WITHOUT_CHANGES_PRE** _(optional)_ - Similar to force without changes, for pre-releases.

### Outputs

- **new_tag** - The value of the newly created tag.
- **old_tag** - The value of the last semantic version tag before the version bump. Empty if no version bump is performed.
- **tag** - The value of the latest tag after running this action.
- **part** - The part of version which was bumped.

> **_Note:_** This action creates a [lightweight tag](https://developer.github.com/v3/git/refs/#create-a-reference).

### Bumping

**Manual Bumping:** Any commit message that includes `#major`, `#minor`, `#patch`, or `#none` will trigger the respective version bump. If two or more are present, the highest-ranking one will take precedence.
If `#none` is contained in the merge commit message, it will skip bumping regardless `DEFAULT_BUMP`.

**Automatic Bumping:** If no `#major`, `#minor` or `#patch` tag is contained in the merge commit message, it will bump whichever `DEFAULT_BUMP` is set to (which is `minor` by default). Disable this by setting `DEFAULT_BUMP` to `none`.