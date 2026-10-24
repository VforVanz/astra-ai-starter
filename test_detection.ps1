$ErrorActionPreference = 'Stop'
$uri = 'http://127.0.0.1:5000/api/ingest'
$now = [DateTimeOffset]::Now
$events = @()

# Synthetic request logs only: no high-volume network traffic is generated.
for ($i = 0; $i -lt 35; $i++) {
    $events += @{
        timestamp = $now.AddSeconds(-35 + $i).ToString('o')
        source_ip = '198.51.100.77'
        event_type = 'http_request'
        method = 'GET'
        path = '/demo-check'
        status_code = 200
        user_agent = 'ASTRA-local-detection-test'
    }
}
$events += @{
    timestamp = $now.ToString('o')
    source_ip = '198.51.100.78'
    event_type = 'http_request'
    method = 'GET'
    path = '/search?q=%3Cscript%3E'
    status_code = 400
    user_agent = 'ASTRA-local-detection-test'
}

$body = @{ events = $events } | ConvertTo-Json -Depth 6
$result = Invoke-RestMethod -Uri $uri -Method Post -ContentType 'application/json' -Body $body
$result | Format-List
Write-Host "Done. Refresh dashboard; look for http_traffic_spike and xss_indicator alerts." -ForegroundColor Green
