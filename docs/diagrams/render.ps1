$ErrorActionPreference = 'Stop'
# Local render only. No install, network request, deployment, or Git operation.
$diagramRoot = $PSScriptRoot
$toolsRoot = Join-Path $diagramRoot '.render-tools'
$d2 = Join-Path $toolsRoot 'd2-v0.9.0/bin/d2.exe'
$java = Join-Path $toolsRoot 'java/jdk-21.0.13+9-jre/bin/java.exe'
$plantuml = Join-Path $toolsRoot 'plantuml-1.2026.9.verified.jar'
$expected = @{
    $d2 = '204bdd0a11e2922f7bff47da4fa279f4131a67b5804223beb1e6a802a9a659d7'
    $java = 'f8dc082a7dedbfd2924c3562405a5a1fd12efd2641808c92e2de819c76a58b7e'
    $plantuml = 'aa4a1d06f8911c4b842beff4828dd955be431692b631a312d04c0e9fab9581de'
}
foreach ($file in $expected.Keys) {
    if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected[$file]) {
        throw ('Renderer integrity mismatch: ' + (Split-Path $file -Leaf))
    }
}
$log = foreach ($source in (Get-ChildItem -LiteralPath $diagramRoot -Filter '*.d2' | Sort-Object Name)) {
    & $d2 --theme 0 --pad 24 $source.FullName ([System.IO.Path]::ChangeExtension($source.FullName, 'svg')) 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { throw ('D2 render failed: ' + $source.Name) }
}
$log | Set-Content -LiteralPath (Join-Path $diagramRoot 'render-d2.log') -Encoding utf8
$plantLog = & $java -jar $plantuml -charset UTF-8 -tsvg -nometadata (Join-Path $diagramRoot 'use-cases.puml') 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) { throw 'PlantUML render failed' }
('PlantUML exit=0; use-cases.svg generated.' + [Environment]::NewLine + $plantLog) |
    Set-Content -LiteralPath (Join-Path $diagramRoot 'render-plantuml.log') -Encoding utf8
Write-Output 'PASS: 10 D2 sequences and 1 PlantUML use-case diagram rendered locally.'
