# Export-ComplianceReport.ps1
# Pulls compliance results from NetGuard API and exports to Excel/CSV

param(
    [string]$ApiBase    = "http://localhost:8000",
    [string]$OutputPath = ".\netguard_compliance_report.csv"
)

try {
    $response = Invoke-RestMethod -Uri "$ApiBase/compliance/" -Method GET
    $report   = $response | Select-Object device_id, score,
        @{Name="violations"; Expression={ ($_.violations -join "; ") }},
        evaluated_at

    $report | Export-Csv -Path $OutputPath -NoTypeInformation
    Write-Host "Report saved to $OutputPath ($($report.Count) devices)"
} catch {
    Write-Error "Failed to reach NetGuard API: $_"
}
