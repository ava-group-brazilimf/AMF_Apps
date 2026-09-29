Add-MpPreference -ExclusionPath (Resolve-Path "projects\Meu-ERP\outputs\tobe\source-code").Path -EA SilentlyContinue
$ts = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
Write-Host "exclusion_added=True"
Write-Host "NTP_START=$ts"
