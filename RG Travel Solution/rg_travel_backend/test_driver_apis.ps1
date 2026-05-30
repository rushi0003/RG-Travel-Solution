# Test all driver management endpoints
$baseUrl = "http://127.0.0.1:5000"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "TESTING RG TRAVEL DRIVER APIs" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 1. Health Check
Write-Host "[1/8] Health Check..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/admin/ping" -Method Get
    Write-Host "✅ Health: $($response.message)" -ForegroundColor Green
} catch {
    Write-Host "❌ Health check failed: $_" -ForegroundColor Red
}

# 2. List Driver Requests
Write-Host "`n[2/8] List Driver Requests..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/admin/driver-requests" -Method Get
    Write-Host "✅ Found $($response.data.Count) driver requests" -ForegroundColor Green
} catch {
    Write-Host "❌ List requests failed: $_" -ForegroundColor Red
}

# 3. List All Drivers
Write-Host "`n[3/8] List All Drivers..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/admin/drivers" -Method Get
    Write-Host "✅ Found $($response.data.Count) drivers" -ForegroundColor Green
    if ($response.data.Count -gt 0) {
        Write-Host "   Sample driver:" -ForegroundColor Cyan
        Write-Host "   - ID: $($response.data[0].id)" -ForegroundColor White
        Write-Host "   - Name: $($response.data[0].name)" -ForegroundColor White
        Write-Host "   - Cab No: $($response.data[0].cab_no)" -ForegroundColor White
        Write-Host "   - Approved: $($response.data[0].approved)" -ForegroundColor White
    }
} catch {
    Write-Host "❌ List drivers failed: $_" -ForegroundColor Red
}

# 4. Search Drivers
Write-Host "`n[4/8] Search Drivers (query='test')..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/admin/drivers/search?query=test" -Method Get
    Write-Host "✅ Search returned $($response.data.Count) results" -ForegroundColor Green
} catch {
    Write-Host "❌ Search failed: $_" -ForegroundColor Red
}

# 5. Create Driver (test)
Write-Host "`n[5/8] Create Test Driver..." -ForegroundColor Yellow
try {
    $testDriver = @{
        name = "Test Driver $(Get-Random -Maximum 9999)"
        mobile = "98765$(Get-Random -Minimum 10000 -Maximum 99999)"
        dl_no = "MH142026$(Get-Random -Minimum 10000 -Maximum 99999)"
        cab_no = "MH12XY$(Get-Random -Minimum 1000 -Maximum 9999)"
        vehicle_type = "4"
        home_town = "Mumbai, Maharashtra"
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$baseUrl/api/admin/drivers" -Method Post `
        -Body $testDriver -ContentType "application/json"
    Write-Host "✅ Created driver ID: $($response.data.driver_id)" -ForegroundColor Green
    $createdDriverId = $response.data.driver_id
} catch {
    Write-Host "❌ Create driver failed: $_" -ForegroundColor Red
    $createdDriverId = $null
}

# 6. Update Driver (if created)
if ($createdDriverId) {
    Write-Host "`n[6/8] Update Test Driver..." -ForegroundColor Yellow
    try {
        $updateData = @{
            name = "Updated Test Driver"
            mobile = "9876543210"
            dl_no = "MH1420260000"
            cab_no = "MH12XY0000"
            vehicle_type = "6"
            home_town = "Pune, Maharashtra"
        } | ConvertTo-Json

        $response = Invoke-RestMethod -Uri "$baseUrl/api/admin/drivers/$createdDriverId" -Method Put `
            -Body $updateData -ContentType "application/json"
        Write-Host "✅ Updated driver successfully" -ForegroundColor Green
    } catch {
        Write-Host "❌ Update driver failed: $_" -ForegroundColor Red
    }

    # 7. Delete Driver
    Write-Host "`n[7/8] Delete Test Driver..." -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "$baseUrl/api/admin/drivers/$createdDriverId" -Method Delete
        Write-Host "✅ Deleted driver successfully" -ForegroundColor Green
    } catch {
        Write-Host "❌ Delete driver failed: $_" -ForegroundColor Red
    }
} else {
    Write-Host "`n[6/8] Skipped Update (no driver created)" -ForegroundColor Gray
    Write-Host "[7/8] Skipped Delete (no driver created)" -ForegroundColor Gray
}

# 8. Final Health Check
Write-Host "`n[8/8] Final Health Check..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/admin/ping" -Method Get
    Write-Host "✅ Backend still healthy" -ForegroundColor Green
} catch {
    Write-Host "❌ Final health check failed: $_" -ForegroundColor Red
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "TEST COMPLETE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
