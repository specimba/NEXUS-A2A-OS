param([int]$Port = 9224, [int]$MaxWaitSec = 0, [string]$TaskClass = "handoff")
# Back-compat: Zo idle wait delegates to intelligent lane waiter.
$Repo = "C:\Users\speci.000\Documents\NEXUS"
$args = @{
    Port       = $Port
    Required   = "zo.computer"
    AgentId    = "zo"
    TaskClass  = $TaskClass
}
if ($MaxWaitSec -gt 0) { $args.MaxWaitSec = $MaxWaitSec }
& "$Repo\tools\browser_ai_supervisor\wait_lane_response.ps1" @args