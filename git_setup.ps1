Remove-Item -Recurse -Force "web-dashboard\.git" -ErrorAction SilentlyContinue
git rm --cached web-dashboard 2>$null
git add .
git commit -m "Initial-commit-Super-Job-Scrapper"
Write-Host "Git commit OK"
