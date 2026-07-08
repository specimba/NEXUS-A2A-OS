#Requires -Version 5.1
<#
.SYNOPSIS
    NEXUS Tidiness Move Script — Surgical file organization for Downloads, C:\tmp, and NEXUS root.

.DESCRIPTION
    Moves NEXUS-related documents from Downloads and C:\tmp into categorized NEXUS folders.
    Cleans duplicate task files and temp artifacts from NEXUS root.
    Creates a MIXED bucket for ambiguous items requiring manual review.

    Run with -WhatIf to preview. Run with -Force to execute.

.PARAMETER WhatIf
    Preview all moves without executing.

.PARAMETER Force
    Execute moves after -WhatIf preview is approved.

.PARAMETER SkipDownloads
    Skip Downloads folder processing.

.PARAMETER SkipTmp
    Skip C:\tmp folder processing.

.PARAMETER SkipRootCleanup
    Skip NEXUS root cleanup.

.EXAMPLE
    .\scripts\nexus-tidiness-move.ps1 -WhatIf
    .\scripts\nexus-tidiness-move.ps1 -Force
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$Force,
    [switch]$SkipDownloads,
    [switch]$SkipTmp,
    [switch]$SkipRootCleanup
)

$ErrorActionPreference = "Stop"
$NexusRoot = "C:\Users\speci.000\Documents\NEXUS"
$Downloads = "C:\Users\speci.000\Downloads"
$Tmp = "C:\tmp"

# ── Helpers ──────────────────────────────────────────────────────────
function Ensure-Dir($path) {
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Force -Path $path | Out-Null
        Write-Host "  [mkdir] $path" -ForegroundColor DarkGray
    }
}

function Safe-Move($src, $dst, $label) {
    if (-not (Test-Path $src)) {
        Write-Host "  [skip] Not found: $src" -ForegroundColor Yellow
        return
    }
    $dstPath = Join-Path $dst (Split-Path $src -Leaf)
    if (Test-Path $dstPath) {
        Write-Host "  [skip] Already exists at destination: $dstPath" -ForegroundColor Yellow
        return
    }
    if ($WhatIfPreference -or $PSCmdlet.ShouldProcess("$src -> $dst", "Move $label")) {
        if (-not $WhatIfPreference) {
            Move-Item -LiteralPath $src -Destination $dst -Force:$Force
        }
        Write-Host "  [move] $label" -ForegroundColor Green
    }
}

function Safe-Delete($path, $label) {
    if (-not (Test-Path $path)) {
        Write-Host "  [skip] Not found: $path" -ForegroundColor Yellow
        return
    }
    if ($WhatIfPreference -or $PSCmdlet.ShouldProcess($path, "Delete $label")) {
        if (-not $WhatIfPreference) {
            Remove-Item -LiteralPath $path -Recurse -Force:$Force
        }
        Write-Host "  [delete] $label" -ForegroundColor Red
    }
}

# ── 0. Validate prerequisites ─────────────────────────────────────────
Write-Host "`n=== NEXUS Tidiness Move ===" -ForegroundColor Cyan
Write-Host "NEXUS Root: $NexusRoot"
Write-Host "Downloads:  $Downloads"
Write-Host "C:\tmp:     $Tmp"
Write-Host "WhatIf:     $WhatIfPreference"
Write-Host "Force:      $Force`n"

if (-not $WhatIfPreference -and -not $Force) {
    Write-Host "ERROR: Run with -WhatIf first to preview, then with -Force to execute." -ForegroundColor Red
    exit 1
}

# ── 1. Create destination directories ────────────────────────────────
Write-Host "`n--- Creating destination directories ---" -ForegroundColor Cyan

$dirs = @(
    "$NexusRoot\research\incoming"
    "$NexusRoot\research\images"
    "$NexusRoot\research\Papers"
    "$NexusRoot\docs\archive\downloads-logs"
    "$NexusRoot\docs\archive\downloads-plans"
    "$NexusRoot\docs\archive\backups"
    "$NexusRoot\docs\archive\diagnostics"
    "$NexusRoot\docs\archive\pr-artifacts"
    "$NexusRoot\docs\archive\sessions"
    "$NexusRoot\scripts\archive\downloads-code"
    "$NexusRoot\benchmarks\archive\downloads"
    "$NexusRoot\datasets\archive\tmp"
    "$NexusRoot\MIXED"
)

foreach ($d in $dirs) { Ensure-Dir $d }

# ── 2. Downloads → NEXUS ─────────────────────────────────────────────
if (-not $SkipDownloads) {
    Write-Host "`n--- Downloads → NEXUS ---" -ForegroundColor Cyan

    # 2.1 Research Texts
    $researchTexts = @(
        "HFways.txt","ciciKUS.txt","redisMEMORYservice.txt","geminiresearch01.txt",
        "SLM-smol-research01.txt","DERDDRE-04.txt","conciousnes1.txt","MCPinspirations.txt",
        "Nebiusrelated.txt","therm02.txt","therm03.txt","thermoLLMfix-001.txt",
        "HALLUCINATION-001-locale-bleed.md","escapeorpoisonBLACKbox.txt",
        "NEXUS-IMAGINE-pipeline-RAW.txt","cyberpunk_BIG_scenario.txt","AI Agents Gone Rogue.txt",
        "REWARD-TRY-FAIL-LEARN-001.txt","storyline01.txt","ErNIEg33.txt",
        "NEXUSscienceteamreport-01.txt","NEXUSbigLOGdeepseekV4-01.txt",
        "HFinternRnDtempbench-01.txt","nemotron 3 stress test for variant Temps.txt",
        "untitled.bib","untitled.ris","untitled.csv","memoryPLAN-01.md",
        "The Architecture of Global Money Control_ Strategic Projections and Market Capitalization of Technological Hegemons in 2026.md",
        "RESEARCH_BRIEF_2026-05-08.md","mythos_agent_orchestration_summary.txt","mythos_raw.txt",
        "deepsearchlinkdump-03.txt","Scientific researcher and scientist.txt","NEXUS approaches from others.txt",
        "Connect the A2A Tool.txt","oracle tech threat intelligence.txt","baseten and tensorblock.txt",
        "pi and other links.txt","Redis capabilities and local software.txt","zilliz storage capabilities.txt",
        "inkeep capabilities.txt","mem0 styled memory suggestions.txt","testcontainers guide starter.txt",
        "HF_Science_database.txt","gastownlog-01.txt","COMBINED_ALL_FILES.txt",
        "MODEL GURU.txt","MODEL GURU codes.txt","CRIPPLE AUTOCLAW.txt",
        "GatewayRequestError invalid config.txt","Kimi 2.6 FIX - 01.txt"
    )
    foreach ($f in $researchTexts) {
        Safe-Move "$Downloads\$f" "$NexusRoot\research\incoming" "research/$f"
    }

    # 2.2 Research Images
    $researchImages = @(
        "agentHARNESS.png","SLMworkflowinference.png","DigitalTwinAI-human.png","Visual ID workflow.png",
        "LLMdevHallicReasons.png","evoDivAgenticWorkflow.png","SLMworkflow.png","oldSLMexampletable.png",
        "PFMbasicschema.png","ASMRtempLLM.png","notion_mcp_agent_preview.png","mckinsey-attack-map.jpg",
        "UNLEARNING.png","HHvF-2sWQAMzsyD.jpg","HICu5iaWAAArJFa.jpg","1500x500.jpg",
        "image (5).jpg","image (4).jpg","image (3).jpg","image (2).jpg","image (1).jpg","image.jpg",
        "image.webp","gTTnhWW.png","xneq8pasytid1.webp","password-hint.png"
    )
    # Add grok images
    $grokImages = Get-ChildItem -LiteralPath $Downloads -Filter "grok-*.png" -ErrorAction SilentlyContinue
    $grokImages += Get-ChildItem -LiteralPath $Downloads -Filter "grok-*.jpg" -ErrorAction SilentlyContinue
    $grokImages += Get-ChildItem -LiteralPath $Downloads -Filter "V4B6N.jpg" -ErrorAction SilentlyContinue
    $grokImages += Get-ChildItem -LiteralPath $Downloads -Filter "UJ60Y.jpg" -ErrorAction SilentlyContinue
    $grokImages += Get-ChildItem -LiteralPath $Downloads -Filter "QUzgh.jpg" -ErrorAction SilentlyContinue
    $grokImages += Get-ChildItem -LiteralPath $Downloads -Filter "E2Y0D.jpg" -ErrorAction SilentlyContinue
    foreach ($img in $researchImages) {
        Safe-Move "$Downloads\$img" "$NexusRoot\research\images" "research-image/$img"
    }
    foreach ($img in $grokImages) {
        Safe-Move $img.FullName "$NexusRoot\research\images" "research-image/$($img.Name)"
    }

    # 2.3 Agent Logs / Handoffs
    $agentLogs = @(
        "grokSKILL-MCPlog.txt","clineMCPlog.txt","codexCUTTEDoptimizationwork-02.txt",
        "codexCUTTEDoptimizationwork-01.txt","NEXUSbigLOGdeepseekV4-01.txt",
        "foundryOPUSMANerrorsonMCP-01.txt","CloudflareWORKERtest.txt",
        "confluent_cloud_installationHELPneed-01.txt","devincont-01.txt",
        "ML-internbuildlogs-01.txt","Administrator Windows PowerShell.txt","gastownlog-01.txt"
    )
    foreach ($f in $agentLogs) {
        Safe-Move "$Downloads\$f" "$NexusRoot\docs\archive\downloads-logs" "log/$f"
    }

    # 2.4 Plans / Requirements
    $plans = @(
        "GREATPLAN-01.md","NotionMCPstyledPlan.txt","notionAIinstructionSUPERprompt.md",
        "notionlog01.txt","greatA2Aconnectionlogs-01.txt","PineConePackboot.txt","PineConePackboot2.txt",
        "TEMPtestsstart-01.txt","Grafanasettings.txt","project-requirements-document.md",
        "backend-structure-document.md","task-list.json","DASHBOARD.json","RESEARCH_BRIEF_2026-05-08.md",
        "memoryPLAN-01.md"
    )
    foreach ($f in $plans) {
        Safe-Move "$Downloads\$f" "$NexusRoot\docs\archive\downloads-plans" "plan/$f"
    }

    # 2.5 Scripts / Code
    $scripts = @(
        "tts_supertonic_subagent.py","nexus_mcp.py","check-textlogs.py","diagnostic_sweep.py",
        "test_archivist_integrity-grok.py","test_archivist_integrity-meta.py",
        "Speculative+Decoding+Technical+Report_code.js"
    )
    foreach ($f in $scripts) {
        Safe-Move "$Downloads\$f" "$NexusRoot\scripts\archive\downloads-code" "script/$f"
    }

    # 2.6 Benchmarks / Archives
    $archives = @(
        "dashboard-app-development.zip",
        "nexus-os-week-2026-05-08-to-12.zip","nexus-os-week-2026-05-08-to-12",
        "Workflows.zip","Workflows",
        "hitcheck (1).zip","hitcheck.zip",
        "workspace-a7c67231-d24f-4e1a-a283-f9ed68340dae.tar",
        "modelrelay.zip","modelrelay",
        "revisionofsources.zip","files-d2f5095b.zip","deepseek_data-2026-05-06.zip",
        "NEXUS_OS_v3.2_Clean_Stabilization_Pack_2026-04-25.zip",
        "NEXUS_OS_v3.2_Full_Deliverables_2026-04-25.zip",
        "NEXUS_OS_v3.2_opusmanSEEKv4_Claw_System_2026-04-29.zip",
        "nexusdashboards-main.zip","nexusdashboards-main",
        "mythOS.zip","mythOS",
        "pc_Windows_x86_64.zip","pc_Windows_x86_64",
        "ccloud-python-client.zip","ccloud-python-client",
        "DERDDRE.zip","DERDDRE"
    )
    foreach ($f in $archives) {
        Safe-Move "$Downloads\$f" "$NexusRoot\benchmarks\archive\downloads" "archive/$f"
    }

    # 2.7 Speculative Decoding Reports
    $specReports = @(
        "Speculative_Decoding_Text_Report (1).docx","Speculative_Decoding_Text_Report.docx",
        "Speculative+Decoding+Technical+Report.html","Scientific_Report.docx","speculativecompres.txt"
    )
    foreach ($f in $specReports) {
        Safe-Move "$Downloads\$f" "$NexusRoot\docs\archive\downloads-plans" "report/$f"
    }

    # 2.8 ErNIE Research
    Safe-Move "$Downloads\ErNIEg33_full_content.docx" "$NexusRoot\research\incoming" "research/ErNIEg33_full_content.docx"

    # 2.9 Papers (directory move)
    if (Test-Path "$Downloads\Papers") {
        $paperFiles = Get-ChildItem -LiteralPath "$Downloads\Papers" -ErrorAction SilentlyContinue
        foreach ($p in $paperFiles) {
            Safe-Move $p.FullName "$NexusRoot\research\Papers" "paper/$($p.Name)"
        }
    }

    # 2.10 MIXED bucket
    $mixed = @(
        "1505","PsyTR","ClaW01.txt","AIKIDOsecuritytest-01.txt",
        "governor","team","vault","ernie_mcp","DOCKERaiGORDON",
        "Telegram Desktop","1500","DOWNLOADSDUMP",
        "doppelground_full_pack_v2","twave_v3_scaffold_unpacked",
        "grokIMAGINEtestv1","very old legacy down",
        "NEXUS_MCP_Server_Phase6.zip","NEXUS_MCP_Server_Phase6"
    )
    foreach ($f in $mixed) {
        Safe-Move "$Downloads\$f" "$NexusRoot\MIXED" "MIXED/$f"
    }
    # Grok videos → MIXED
    $grokVideos = Get-ChildItem -LiteralPath $Downloads -Filter "grok-video-*.mp4" -ErrorAction SilentlyContinue
    $grokVideos += Get-ChildItem -LiteralPath $Downloads -Filter "tmp1x8hwzxx.mp4" -ErrorAction SilentlyContinue
    foreach ($v in $grokVideos) {
        Safe-Move $v.FullName "$NexusRoot\MIXED" "MIXED/$($v.Name)"
    }
}

# ── 3. C:\tmp → NEXUS ───────────────────────────────────────────────
if (-not $SkipTmp) {
    Write-Host "`n--- C:\tmp → NEXUS ---" -ForegroundColor Cyan

    # 3.1 Config Backups
    $backups = @(
        ".modelrelay.before_literal_modelid_fix_20260505_115956.json",
        "pi-settings-before-nexus-provider-fix.json",
        "nexus-modelrelay-mirror-before-safe-filter.ts"
    )
    foreach ($f in $backups) {
        Safe-Move "$Tmp\$f" "$NexusRoot\docs\archive\backups" "backup/$f"
    }
    Safe-Move "$Tmp\nexus-env-backups" "$NexusRoot\docs\archive\backups" "backup/nexus-env-backups"

    # 3.2 Diagnostics / Logs
    $diags = @(
        "CDB_050426-23750-01_RELOAD.txt","CDB_042326-34390-01.txt","CDB_050426-23750-01.txt",
        "nexus-model-id-proxy.out.log","nexus-model-id-proxy.err.log","agt_verify_output.txt"
    )
    foreach ($f in $diags) {
        Safe-Move "$Tmp\$f" "$NexusRoot\docs\archive\diagnostics" "diag/$f"
    }

    # 3.3 PR Artifacts
    Safe-Move "$Tmp\nexusalpha-pr32-comment.md" "$NexusRoot\docs\archive\pr-artifacts" "pr/nexusalpha-pr32-comment.md"
    Safe-Move "$Tmp\sandbox_changes.patch" "$NexusRoot\docs\archive\pr-artifacts" "pr/sandbox_changes.patch"
    Safe-Move "$Tmp\drs_environment.yaml" "$NexusRoot\docs\archive\pr-artifacts" "pr/drs_environment.yaml"

    # 3.4 Test Data
    $testData = @("test_brotli.parquet","test_zstd.parquet","test_gzip.parquet","test_snappy.parquet")
    foreach ($f in $testData) {
        Safe-Move "$Tmp\$f" "$NexusRoot\datasets\archive\tmp" "dataset/$f"
    }

    # 3.5 MIXED
    Safe-Move "$Tmp\earth_science" "$NexusRoot\MIXED" "MIXED/earth_science"

    # 3.6 Delete temp / leave
    Write-Host "`n  [info] The following C:\tmp items should be manually reviewed/deleted:" -ForegroundColor DarkYellow
    @("nexusalpha-safe-push","nexus-governed-mcp-python-clone","nexus-governed-mcp-python-pr",
      "nexus-governed-mcp-pr","openclaw","nexus-windows-recovery-transfer","nexus-resource-guard",
      "nexus_pi_active_fix_20260505_115645","symbols2","symbols","winsdksetup.exe","qdrant") |
        ForEach-Object { Write-Host "    - $_" -ForegroundColor DarkGray }
}

# ── 4. NEXUS Root Cleanup ────────────────────────────────────────────
if (-not $SkipRootCleanup) {
    Write-Host "`n--- NEXUS Root Cleanup ---" -ForegroundColor Cyan

    # 4.1 Delete duplicate task/handoff files at root
    $dups = @(
        "$NexusRoot\2026-05-18-010-docker-wsl-resource-optimization.task.md",
        "$NexusRoot\2026-05-18-011-docker-secret-hardening.task.md",
        "$NexusRoot\2026-05-20-pi-broken.md",
        "$NexusRoot\NEXUS_DOCKER_SECRET_HARDENING_2026-05-19.md"
    )
    foreach ($f in $dups) {
        Safe-Delete $f "duplicate root file"
    }

    # 4.2 Move handoff directory → docs/handoff/
    if (Test-Path "$NexusRoot\handoff") {
        $handoffItems = Get-ChildItem -LiteralPath "$NexusRoot\handoff" -ErrorAction SilentlyContinue
        foreach ($item in $handoffItems) {
            Safe-Move $item.FullName "$NexusRoot\docs\handoff" "handoff/$($item.Name)"
        }
        # Remove empty handoff directory after moving contents
        if ((Get-ChildItem -LiteralPath "$NexusRoot\handoff" -ErrorAction SilentlyContinue | Measure-Object).Count -eq 0) {
            Safe-Delete "$NexusRoot\handoff" "empty handoff directory"
        }
    }

    # 4.3 Move loose handoff docs
    $handoffs = @(
        @{Src="$NexusRoot\2026-05-20-alpha-branch-comparison.md"; Dst="$NexusRoot\docs\handoff"; Label="alpha-branch-comparison"},
        @{Src="$NexusRoot\cline_agent_review.md"; Dst="$NexusRoot\docs"; Label="cline_agent_review"},
        @{Src="$NexusRoot\NEO_NEXUS_GROUNDING.md"; Dst="$NexusRoot\docs"; Label="NEO_NEXUS_GROUNDING"},
        @{Src="$NexusRoot\nexus_grounding_report.md"; Dst="$NexusRoot\docs"; Label="nexus_grounding_report"}
    )
    foreach ($h in $handoffs) {
        Safe-Move $h.Src $h.Dst $h.Label
    }

    # 4.3 Move session logs
    $sessions = @(
        "$NexusRoot\pi-session-2026-05-12T01-45-21-849Z_019e19dc-32b8-7399-b033-ab11c960cafa.html",
        "$NexusRoot\pi-session-2026-05-15T04-08-28-478Z_019e29d2-4c3d-774b-a6a8-5d8922126d59.html",
        "$NexusRoot\session-ses_1e41.md"
    )
    foreach ($f in $sessions) {
        Safe-Move $f "$NexusRoot\docs\archive\sessions" "session/$(Split-Path $f -Leaf)"
    }

    # 4.4 Delete temp artifacts
    $temps = @(
        "$NexusRoot\_tmp_run_guard_eval2.py",
        "$NexusRoot\package.json.tmp",
        "$NexusRoot\nul",
        "$NexusRoot\.env_backup.txt",
        "$NexusRoot\test_heartbeat.db"
    )
    foreach ($f in $temps) {
        Safe-Delete $f "temp artifact"
    }

    # 4.5 Move corrupted backup
    Safe-Move "$NexusRoot\.env_corrupted_backup.txt" "$NexusRoot\docs\archive\backups" "backup/.env_corrupted_backup.txt"
}

# ── 5. Final Report ──────────────────────────────────────────────────
Write-Host "`n=== Move Summary ===" -ForegroundColor Cyan
Write-Host "Review the output above for [move], [delete], and [skip] actions."
Write-Host "If -WhatIf was used, no changes were made."
Write-Host "If -Force was used, changes have been applied."
Write-Host "`nNext steps:"
Write-Host "  1. Review MIXED/ folder contents and reclassify manually."
Write-Host "  2. Delete or quarantine sensitive items in Downloads (env.txt, sshkey.pem, etc.)."
Write-Host "  3. Clean C:\tmp temp directories listed in section 3.6."
Write-Host "  4. Run: git status --short to verify repo state."
Write-Host "  5. Stage docs/ and scripts/ changes explicitly if desired."
