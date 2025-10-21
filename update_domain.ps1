# PowerShell script to update domain name to force cache reset

# Update const.py
$constFile = "custom_components\schoolcafe\const.py"
$content = Get-Content $constFile -Raw
$content = $content -replace 'DOMAIN = "schoolcafe"', 'DOMAIN = "schoolcafe_menu"'
Set-Content $constFile $content

# Update manifest.json
$manifestFile = "custom_components\schoolcafe\manifest.json"
$content = Get-Content $manifestFile -Raw
$content = $content -replace '"domain": "schoolcafe",', '"domain": "schoolcafe_menu",'
$content = $content -replace '"version": "1.3.0"', '"version": "1.4.0"'
Set-Content $manifestFile $content

# Update sensor.py
$sensorFile = "custom_components\schoolcafe\sensor.py"
$content = Get-Content $sensorFile -Raw
$content = $content -replace 'SCHOOLCAFE INTEGRATION v1.3.0: Simplified sensor naming - NEW CODE!', 'SCHOOLCAFE INTEGRATION v1.4.0: NEW DOMAIN schoolcafe_menu - COMPLETE RESET!'
$content = $content -replace 'schoolcafe_\{line_clean\}_\{day_suffix\}', 'schoolcafe_menu_{line_clean}_{day_suffix}'
$content = $content -replace 'sensor.schoolcafe_blue_line_today \(simple, clean pattern\)', 'sensor.schoolcafe_menu_blue_line_today (new domain, clean pattern)'
Set-Content $sensorFile $content

Write-Host "Domain updated to schoolcafe_menu in all files!" -ForegroundColor Green
Write-Host "Sensors will now be named: sensor.schoolcafe_menu_blue_line_today, etc." -ForegroundColor Yellow
