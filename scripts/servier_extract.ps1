# Extract every drawing from Servier Medical Art PPTX sets as high-resolution transparent PNGs,
# with a catalog (set, slide title, nearest text label, file) for servier.py to search.
# Needs Microsoft PowerPoint (COM). Servier Medical Art is CC BY 4.0: credit "Servier Medical Art (smart.servier.com), CC BY 4.0".
#   powershell -ExecutionPolicy Bypass -File servier_extract.ps1 -Raw <folder with SMART-*.pptx> -Out <library folder>
param([string]$Raw, [string]$Out, [int]$Px = 1400)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force $Out | Out-Null
$app = New-Object -ComObject PowerPoint.Application
$cat = @()
foreach ($f in Get-ChildItem $Raw -Filter "SMART-*.pptx") {
  $set = $f.BaseName -replace '^SMART-', ''
  $dir = Join-Path $Out $set; New-Item -ItemType Directory -Force $dir | Out-Null
  $pr = $app.Presentations.Open($f.FullName, $true, $false, $false)
  foreach ($s in $pr.Slides) {
    $texts = @(); $title = ""
    foreach ($sh in $s.Shapes) {
      if ($sh.HasTextFrame -and $sh.TextFrame.HasText) {
        $t = ($sh.TextFrame.TextRange.Text -replace '\s+', ' ').Trim()
        if (-not $title) { $title = $t }
        $texts += [pscustomobject]@{t = $t; x = $sh.Left + $sh.Width / 2; y = $sh.Top + $sh.Height / 2 }
      }
    }
    $k = 0
    foreach ($sh in $s.Shapes) {
      if ($sh.HasTextFrame -and $sh.TextFrame.HasText) { continue }
      if ($sh.Width -lt 25 -or $sh.Height -lt 25) { continue }      # skip lines, ticks, tiny bits
      $k++
      $cx = $sh.Left + $sh.Width / 2; $cy = $sh.Top + $sh.Height / 2
      $near = $texts | Where-Object { $_.t -ne $title } | Sort-Object { [math]::Pow($_.x - $cx, 2) + [math]::Pow($_.y - $cy, 2) } | Select-Object -First 1
      $label = if ($near) { $near.t } else { "" }
      $name = ("{0}_s{1}_{2}" -f $set, $s.SlideIndex, $k)
      $file = Join-Path $dir "$name.png"
      $sc = $Px / [math]::Max($sh.Width, $sh.Height)
      $sh.Export($file, 2, [int]($sh.Width * $sc), [int]($sh.Height * $sc))   # 2 = PNG, transparent background
      $cat += [pscustomobject]@{set = $set; slide = $s.SlideIndex; title = $title; label = $label; file = "$set/$name.png";
        w = [int]($sh.Width * $sc); h = [int]($sh.Height * $sc) }
    }
  }
  $pr.Close()
  "done $set"
}
$app.Quit()
$cat | ConvertTo-Json -Depth 3 | Out-File -Encoding utf8 (Join-Path $Out "catalog.json")
"catalog: $($cat.Count) drawings"
