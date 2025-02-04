#!/bin/bash

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print with color
print_status() {
    echo -e "${GREEN}==>${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}WARNING:${NC} $1"
}

print_error() {
    echo -e "${RED}ERROR:${NC} $1"
}

# Check if a version bump type was provided
if [ -z "$1" ]; then
    print_error "Please provide a version bump type: patch, minor, or major"
    echo "Usage: ./release.sh [patch|minor|major]"
    exit 1
fi

# Validate version bump type
if [ "$1" != "patch" ] && [ "$1" != "minor" ] && [ "$1" != "major" ]; then
    print_error "Invalid version bump type. Please use: patch, minor, or major"
    exit 1
fi

# Make sure we're on the master branch
BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "master" ]; then
    print_error "Please switch to the master branch before creating a release"
    exit 1
fi

# Make sure the working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    print_error "Working directory is not clean. Please commit or stash changes first."
    exit 1
fi

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    print_error "Poetry could not be found. Please install it first."
    exit 1
fi

# Check if pytest is installed
if ! poetry run python -c "import pytest" 2>/dev/null; then
    print_warning "pytest is not installed. Skipping tests."
    RUN_TESTS=false
else
    RUN_TESTS=true
fi

# Pull latest changes
print_status "Pulling latest changes from master..."
git pull origin master

# Show what the new version will be and ask for confirmation
CURRENT_VERSION=$(poetry version -s)
NEW_VERSION=$(poetry version $1 --dry-run)
print_status "Current version: $CURRENT_VERSION"
print_status "New version will be: $NEW_VERSION"

# Generate changelog
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "none")
if [ "$LAST_TAG" != "none" ]; then
    print_status "Generating changelog since $LAST_TAG..."
    CHANGELOG=$(git log "$LAST_TAG"..HEAD --oneline --pretty=format:"- %s")
else
    CHANGELOG=$(git log --oneline --pretty=format:"- %s")
fi

echo -e "\nChangelog:"
echo "$CHANGELOG"
echo

# Check dependencies
print_status "Checking for outdated dependencies..."
poetry show --outdated || true

# Run tests if available
if [ "$RUN_TESTS" = true ]; then
    print_status "Running tests..."
    poetry run pytest || {
        print_error "Tests failed!"
        exit 1
    }
fi

# Final confirmation
echo
print_status "Ready to release version $NEW_VERSION"
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_status "Release cancelled."
    exit 1
fi

# Update version using Poetry
print_status "Bumping version ($1)..."
poetry version $1

# Create release notes file
RELEASE_NOTES="release_notes.md"
echo "# Release Notes for v$NEW_VERSION" > $RELEASE_NOTES
echo "" >> $RELEASE_NOTES
echo "## Changes" >> $RELEASE_NOTES
echo "$CHANGELOG" >> $RELEASE_NOTES

# Stage and commit version bump
print_status "Committing version bump..."
git add pyproject.toml $RELEASE_NOTES
git commit -m "Bump version to $NEW_VERSION

Release Notes:
$CHANGELOG"

# Create and push tag
print_status "Creating and pushing tag v$NEW_VERSION..."
git tag -a "v$NEW_VERSION" -m "Version $NEW_VERSION

$CHANGELOG"
git push && git push --tags

# Cleanup
rm $RELEASE_NOTES

print_status "Release process initiated!"
print_status "Version $NEW_VERSION will be published to PyPI and GitHub releases automatically."
print_status "You can monitor the progress at: https://github.com/xian-network/xian-core/actions"