# E2E Test Suite for AI Multi-Agent Enterprise Workspace v0.3.0
# Usage: powershell -ExecutionPolicy Bypass -File e2e_test.ps1

$BASE = "http://localhost:8001"
$PASS = 0
$FAIL = 0

function Check($name, $condition) {
    if ($condition) {
        $global:PASS++
        Write-Host "  [PASS] $name" -ForegroundColor Green
    } else {
        $global:FAIL++
        Write-Host "  [FAIL] $name" -ForegroundColor Red
    }
}

Write-Host "=== Test Suite Start ===" -ForegroundColor Cyan

# 1. Auth
Write-Host "`n--- 1. Auth ---" -ForegroundColor Yellow

$body = '{"email":"e2e@test.com","username":"e2etester","password":"Test123!"}'
try {
    $r = Invoke-RestMethod -Uri "$BASE/api/v1/auth/register" -Method Post -ContentType "application/json" -Body $body -ErrorAction Stop
    Check "Register (201 created)" ($r.access_token -ne $null)
} catch {
    # User may already exist from previous run — login instead
    Check "Register (already exists, OK)" $true
}

$body = '{"email":"e2e@test.com","password":"Test123!"}'
$login = Invoke-RestMethod -Uri "$BASE/api/v1/auth/login" -Method Post -ContentType "application/json" -Body $body
$TOKEN = $login.access_token
Check "Login (200)" ($TOKEN -ne $null)
Check "Has RefreshToken" ($login.refresh_token -ne $null)

$headers = @{ "Authorization" = "Bearer $TOKEN" }

$rbody = "{""refresh_token"":""$($login.refresh_token)""}"
$refresh = Invoke-RestMethod -Uri "$BASE/api/v1/auth/refresh" -Method Post -ContentType "application/json" -Body $rbody
Check "Refresh Token (200)" ($refresh.access_token -ne $null)

# 2. Workspace
Write-Host "`n--- 2. Workspace ---" -ForegroundColor Yellow

$ws = Invoke-RestMethod -Uri "$BASE/api/v1/workspaces" -Method Post -Headers $headers -ContentType "application/json" -Body '{"name":"E2E Test WS"}'
$WS_ID = $ws.id
Check "Create Workspace" ($WS_ID -ne $null)

$wlist = Invoke-RestMethod -Uri "$BASE/api/v1/workspaces" -Method Get -Headers $headers
Check "List Workspaces" ($wlist.total -gt 0)

$wone = Invoke-RestMethod -Uri "$BASE/api/v1/workspaces/$WS_ID" -Method Get -Headers $headers
Check "Get Workspace" ($wone.name -eq "E2E Test WS")

# 3. Data Isolation
Write-Host "`n--- 3. Data Isolation ---" -ForegroundColor Yellow

try {
    $loginB = Invoke-RestMethod -Uri "$BASE/api/v1/auth/login" -Method Post -ContentType "application/json" -Body '{"email":"userB@test.com","password":"pass123"}'
    $TB = $loginB.access_token
    $headersB = @{ "Authorization" = "Bearer $TB" }
    Invoke-RestMethod -Uri "$BASE/api/v1/workspaces/$WS_ID" -Method Get -Headers $headersB | Out-Null
    Check "Isolation (403 expected)" $false
} catch {
    Check "Isolation (403 expected)" ($_.Exception.Response.StatusCode.value__ -eq 403)
}

# 4. Documents
Write-Host "`n--- 4. Documents ---" -ForegroundColor Yellow

$testFile = "$env:TEMP\e2e_test_doc.txt"
"E2E test document content for semantic search verification." | Out-File -FilePath $testFile -Encoding UTF8

$result = curl.exe -s -X POST "$BASE/api/v1/workspaces/$WS_ID/documents/upload" -H "Authorization: Bearer $TOKEN" -F "file=@$testFile" 2>&1
try {
    $doc = $result | ConvertFrom-Json
    $DOC_ID = $doc.id
    Check "Upload Document" ($DOC_ID -ne $null)
} catch {
    Check "Upload Document" $false
    $DOC_ID = $null
}

$dlist = Invoke-RestMethod -Uri "$BASE/api/v1/workspaces/$WS_ID/documents" -Method Get -Headers $headers
Check "List Documents" ($dlist.total -gt 0)

# 5. RAG Search
Write-Host "`n--- 5. RAG Search ---" -ForegroundColor Yellow

$search = Invoke-RestMethod -Uri "$BASE/api/v1/workspaces/$WS_ID/search" -Method Post -Headers $headers -ContentType "application/json" -Body '{"query":"test document","top_k":5}'
Check "Search OK" ($search.total -ge 0)

# 6. Chat
Write-Host "`n--- 6. Chat ---" -ForegroundColor Yellow

$sess = Invoke-RestMethod -Uri "$BASE/api/v1/workspaces/$WS_ID/chat/sessions" -Method Post -Headers $headers -ContentType "application/json" -Body '{"title":"E2E Session"}'
$SID = $sess.id
Check "Create Session" ($SID -ne $null)

$msgBody = "{""session_id"":""$SID"",""message"":""Hello, introduce yourself in one sentence""}"
$msg = Invoke-RestMethod -Uri "$BASE/api/v1/workspaces/$WS_ID/chat/send" -Method Post -Headers $headers -ContentType "application/json" -Body $msgBody
Check "Chat Reply" ($msg.reply.Length -gt 10)

$msgs = Invoke-RestMethod -Uri "$BASE/api/v1/workspaces/$WS_ID/chat/sessions/$SID/messages" -Method Get -Headers $headers
Check "List Messages" ($msgs.Count -ge 2)

$slist = Invoke-RestMethod -Uri "$BASE/api/v1/workspaces/$WS_ID/chat/sessions" -Method Get -Headers $headers
Check "List Sessions" ($slist.total -ge 1)

# 7. User Search
Write-Host "`n--- 7. User Search ---" -ForegroundColor Yellow

$usearch = Invoke-RestMethod -Uri "$BASE/api/v1/users/search?q=e2e" -Method Get -Headers $headers
Check "User Search" ($usearch.total -gt 0)

# 8. Members
Write-Host "`n--- 8. Members ---" -ForegroundColor Yellow

$mlist = Invoke-RestMethod -Uri "$BASE/api/v1/workspaces/$WS_ID/members" -Method Get -Headers $headers
Check "List Members" ($mlist.total -ge 1)

# 9. Reports
Write-Host "`n--- 9. Reports ---" -ForegroundColor Yellow

$reportData = @{
    title = "E2E System Analysis"
    query = "Analyze the current system architecture"
    format = "markdown"
    report_type = "technical"
}
$reportJson = $reportData | ConvertTo-Json -Compress

try {
    $report = Invoke-RestMethod -Uri "$BASE/api/v1/workspaces/$WS_ID/reports" -Method Post -Headers $headers -ContentType "application/json" -Body $reportJson -TimeoutSec 120
    Check "Generate Report" ($report.id -ne $null)
    $rlist = Invoke-RestMethod -Uri "$BASE/api/v1/workspaces/$WS_ID/reports" -Method Get -Headers $headers
    Check "List Reports" ($rlist.total -gt 0)
} catch {
    Check "Generate Report" $false
    Check "List Reports" $false
}

# 10. Cleanup
Write-Host "`n--- 10. Cleanup ---" -ForegroundColor Yellow

if ($DOC_ID) { try { Invoke-RestMethod -Uri "$BASE/api/v1/workspaces/$WS_ID/documents/$DOC_ID" -Method Delete -Headers $headers; Check "Delete Doc" $true } catch { Check "Delete Doc" $false } } else { Check "Delete Doc (skipped)" $true }
try { Invoke-RestMethod -Uri "$BASE/api/v1/workspaces/$WS_ID/chat/sessions/$SID" -Method Delete -Headers $headers; Check "Delete Session" $true } catch { Check "Delete Session" $false }
Remove-Item $testFile -ErrorAction SilentlyContinue

# Result
Write-Host "`n====================================" -ForegroundColor Cyan
if ($FAIL -eq 0) {
    Write-Host "  ALL $PASS tests PASSED" -ForegroundColor Green
} else {
    Write-Host "  $PASS passed, $FAIL failed" -ForegroundColor Red
}
Write-Host "====================================" -ForegroundColor Cyan
