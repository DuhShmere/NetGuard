# Get-DeviceInventory.ps1
# Exports network device hostnames and IPs to CSV for NetGuard ingestion

param(
    [string]$OutputPath = ".\device_inventory.csv",
    [string]$Subnet     = "192.168.1.0/24"
)

$devices = @()

# Option 1: Pull from Active Directory (requires RSAT)
# $computers = Get-ADComputer -Filter * -Properties Name, IPv4Address | Select-Object Name, IPv4Address
# $devices = $computers | ForEach-Object { [PSCustomObject]@{ hostname=$_.Name; ip=$_.IPv4Address; vendor="cisco"; platform="ios" } }

# Option 2: Static CSV merge — edit device_list.csv manually then run this
$staticList = @(
    [PSCustomObject]@{ hostname="core-sw-01"; ip="192.168.1.1"; vendor="cisco";   platform="nxos" },
    [PSCustomObject]@{ hostname="edge-rt-01"; ip="192.168.1.2"; vendor="juniper"; platform="junos" },
    [PSCustomObject]@{ hostname="dist-sw-01"; ip="192.168.1.3"; vendor="cisco";   platform="ios" }
)

$staticList | Export-Csv -Path $OutputPath -NoTypeInformation
Write-Host "Exported $($staticList.Count) devices to $OutputPath"
