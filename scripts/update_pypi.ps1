param(
    [Parameter(Mandatory=$true)]
    [string]$NewVersion,

    [Parameter(Mandatory=$false)]
    [string]$ChangelogMessage = "",

    [Parameter(Mandatory=$false)]
    [switch]$TestOnly = $false,

    [Parameter(Mandatory=$false)]
    [switch]$BugFix = $false
)

Write-Host "Visus Desktop - Update Script" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# If this is a bug fix, add a special note
if ($BugFix) {
    Write-Host "BUG FIX RELEASE - Critical fix" -ForegroundColor Red
    if (!$ChangelogMessage) {
        $ChangelogMessage = "Critical bug fix"
    }
}

# Check that we are in the correct directory
if (!(Test-Path "pyproject.toml")) {
    Write-Error "Run this script from the visus-desktop repository root that contains pyproject.toml"
    exit 1
}

# 1. Update the version in pyproject.toml
Write-Host "Updating version to $NewVersion..." -ForegroundColor Yellow
$content = Get-Content pyproject.toml
$newContent = $content -replace 'version = ".*"', "version = `"$NewVersion`""
$newContent | Set-Content pyproject.toml

# 2. Update the changelog if a message was provided
if ($ChangelogMessage) {
    Write-Host "Adding changelog entry..." -ForegroundColor Yellow
    $date = Get-Date -Format "yyyy-MM-dd"
    $changelogEntry = "`n## [$NewVersion] - $date`n- $ChangelogMessage`n"

    # Add to README.md right after the main title
    $readme = Get-Content README.md -Raw
    $readme = $readme -replace "(# Visus Desktop.*?\n)", "`$1$changelogEntry"
    $readme | Set-Content README.md
}

# 3. Clean previous builds
Write-Host "Cleaning previous builds..." -ForegroundColor Yellow
Remove-Item -Recurse -Force dist, build, *.egg-info -ErrorAction SilentlyContinue

# 4. Run tests
Write-Host "Running tests..." -ForegroundColor Yellow
$testResult = pytest --tb=short
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Some tests failed. Continue anyway? (y/N)"
    $response = Read-Host
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "Aborted by the user" -ForegroundColor Red
        exit 1
    }
}

# 5. Build
Write-Host "Building the package..." -ForegroundColor Yellow
python -m build
if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed!"
    exit 1
}

# 6. Validate the package
Write-Host "Validating the package..." -ForegroundColor Yellow
twine check dist/*
if ($LASTEXITCODE -ne 0) {
    Write-Error "Validation failed!"
    exit 1
}

# 7. Upload
if ($TestOnly) {
    Write-Host "Uploading to TestPyPI..." -ForegroundColor Magenta
    twine upload --repository testpypi dist/*

    if ($LASTEXITCODE -eq 0) {
        Write-Host "Upload to TestPyPI completed!" -ForegroundColor Green
        Write-Host "Test at: https://test.pypi.org/project/visus-desktop/" -ForegroundColor Cyan
        Write-Host "Install: pip install -i https://test.pypi.org/simple/ visus-desktop==$NewVersion" -ForegroundColor Cyan
    }
} else {
    Write-Host "Uploading to the official PyPI..." -ForegroundColor Magenta
    Write-Host "This will publish version $NewVersion permanently!" -ForegroundColor Yellow
    Write-Host "Continue? (y/N): " -NoNewline -ForegroundColor Yellow
    $response = Read-Host

    if ($response -eq "y" -or $response -eq "Y") {
        twine upload dist/*

        if ($LASTEXITCODE -eq 0) {
            Write-Host "Success! Version $NewVersion published to PyPI!" -ForegroundColor Green
            Write-Host "Check at: https://pypi.org/project/visus-desktop/" -ForegroundColor Cyan
            Write-Host "Install: pip install visus-desktop==$NewVersion" -ForegroundColor Cyan

            # Commit the changes
            Write-Host "Committing the changes..." -ForegroundColor Yellow
            git add pyproject.toml README.md
            git commit -m "Release version $NewVersion"
            git tag "v$NewVersion"

            Write-Host "Run 'git push && git push --tags' to send to GitHub" -ForegroundColor Cyan
        } else {
            Write-Error "Upload failed!"
        }
    } else {
        Write-Host "Upload cancelled by the user" -ForegroundColor Red
    }
}

Write-Host "`n================================================" -ForegroundColor Cyan
Write-Host "Script finished!" -ForegroundColor Cyan
