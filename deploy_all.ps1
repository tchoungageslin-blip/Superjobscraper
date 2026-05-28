Write-Host "Commit de tous les changements..."
git add .
git commit -m "Add-profile-onboarding-system-Resend-email"

Write-Host "Deploiement du dashboard sur Vercel..."
Set-Location web-dashboard
npx vercel deploy --yes --env "DATABASE_URL=postgresql://postgres.lffeiajzjdhsjdcsialt:Tchoungageslin1234567890%@aws-0-eu-west-1.pooler.supabase.com:6543/postgres" --prod
Set-Location ..

Write-Host "Tout est deploye!"
