# Run from any directory with Windows PowerShell.
Add-Type -AssemblyName System.Drawing
$outputDirectory = Join-Path $PSScriptRoot 'images'
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

function New-StateDiagram {
    param([bool]$IncludeSleep, [string]$FileName)

    $height = if ($IncludeSleep) { 1570 } else { 1190 }
    $bitmap = New-Object System.Drawing.Bitmap(1800, $height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $graphics.Clear([System.Drawing.Color]::White)
    $ink = [System.Drawing.ColorTranslator]::FromHtml('#183047')
    $muted = [System.Drawing.ColorTranslator]::FromHtml('#496176')
    $blue = [System.Drawing.ColorTranslator]::FromHtml('#2773AE')
    $titleFont = New-Object System.Drawing.Font('Malgun Gothic', 31, [System.Drawing.FontStyle]::Bold)
    $stateFont = New-Object System.Drawing.Font('Malgun Gothic', 28, [System.Drawing.FontStyle]::Bold)
    $bodyFont = New-Object System.Drawing.Font('Malgun Gothic', 18)
    $labelFont = New-Object System.Drawing.Font('Malgun Gothic', 18, [System.Drawing.FontStyle]::Bold)
    $brush = New-Object System.Drawing.SolidBrush($ink)
    $mutedBrush = New-Object System.Drawing.SolidBrush($muted)
    $linePen = New-Object System.Drawing.Pen($blue, 4)
    $cap = New-Object System.Drawing.Drawing2D.AdjustableArrowCap(5, 6, $true)
    $linePen.CustomEndCap = $cap
    $borderPen = New-Object System.Drawing.Pen($ink, 3)
    $format = New-Object System.Drawing.StringFormat
    $format.Alignment = [System.Drawing.StringAlignment]::Center
    $format.LineAlignment = [System.Drawing.StringAlignment]::Center

    function Text-Centered([string]$Text, [float]$X, [float]$Y, $Font, $TextBrush) {
        $graphics.DrawString($Text, $Font, $TextBrush, [System.Drawing.PointF]::new($X, $Y), $format)
    }
    function Label([string]$Text, [float]$X, [float]$Y) {
        $size = $graphics.MeasureString($Text, $labelFont)
        $graphics.FillRectangle([System.Drawing.Brushes]::White, $X - $size.Width / 2 - 10, $Y - $size.Height / 2 - 4, $size.Width + 20, $size.Height + 8)
        Text-Centered $Text $X $Y $labelFont $brush
    }
    function Arrow([float[]]$Coordinates) {
        $points = for ($i = 0; $i -lt $Coordinates.Length; $i += 2) {
            [System.Drawing.PointF]::new($Coordinates[$i], $Coordinates[$i + 1])
        }
        $graphics.DrawLines($linePen, [System.Drawing.PointF[]]$points)
    }
    function State([string]$Name, [string]$Detail, [float]$X, [float]$Y, [string]$Fill) {
        $fillBrush = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml($Fill))
        $graphics.FillRectangle($fillBrush, $X, $Y, 340, 200)
        $graphics.DrawRectangle($borderPen, $X, $Y, 340, 200)
        Text-Centered $Name ($X + 170) ($Y + 62) $stateFont $brush
        Text-Centered $Detail ($X + 170) ($Y + 137) $bodyFont $mutedBrush
        $fillBrush.Dispose()
    }

    $title = if ($IncludeSleep) { '소년 전체 상태 다이어그램' } else { '자동 무적 런 핵심 상태 다이어그램' }
    Text-Centered $title 900 85 $titleFont $brush
    Text-Centered '화살표 방향은 상태 전이, 화살표 옆 문구는 전이 조건' 900 147 $bodyFont $mutedBrush

    State 'AutoRun' "자동 이동 · 가속 · 확대`n좌우 경계에서 방향 반전" 730 255 '#E7F4EF'
    State 'IDLE' "제자리 대기`n진입 시 대기 시간 초기화" 130 700 '#ECF3FC'
    State 'RUN' "방향키로 일반 달리기`n누른 방향으로 이동" 1330 700 '#FFF1DD'

    # Initial state.
    $graphics.FillEllipse($brush, 44, 788, 24, 24)
    Arrow @(68, 800, 130, 800)
    Label '시작' 86 752

    # AutoRun entry, timeout exit, and manual exit.
    Arrow @(300, 700, 300, 355, 730, 355)
    Label 'A 키 누름' 510 320
    Arrow @(730, 420, 520, 420, 520, 625, 390, 625, 390, 700)
    Label '진입 후 5초 이상 경과' 545 530
    Arrow @(1070, 355, 1510, 355, 1510, 700)
    Label '좌우 방향키 누름' 1285 320

    # Existing manual running transitions.
    Arrow @(470, 752, 1330, 752)
    Label '좌우 방향키 누름' 900 713
    Arrow @(1330, 842, 470, 842)
    Label '방향키 모두 해제' 900 881

    if ($IncludeSleep) {
        State 'SLEEP' "누워서 잠들기`nSpace 또는 방향키로 복귀" 730 1170 '#F1EDF9'
        Arrow @(300, 900, 300, 1270, 730, 1270)
        Label 'IDLE에서 5초 이상 경과' 490 1320
        Arrow @(730, 1200, 520, 1200, 520, 985, 390, 985, 390, 900)
        Label 'Space 키 누름' 535 1090
        Arrow @(1070, 1270, 1510, 1270, 1510, 900)
        Label '좌우 방향키 누름' 1285 1320
        Text-Centered '경계 반전은 AutoRun 내부 동작이며, 상태 재진입이나 타이머 초기화가 발생하지 않음' 900 1470 $bodyFont $mutedBrush
        Text-Centered '키 누름 = KEYDOWN / 모든 지속 시간은 해당 상태 진입 시점부터 측정' 900 1515 $bodyFont $mutedBrush
    } else {
        Text-Centered '경계 반전은 AutoRun 내부 동작이며, 상태 재진입이나 타이머 초기화가 발생하지 않음' 900 1050 $bodyFont $mutedBrush
        Text-Centered '기존 SLEEP 전이는 전체 상태 다이어그램 참조 / 키 누름 = KEYDOWN' 900 1095 $bodyFont $mutedBrush
    }

    $bitmap.Save((Join-Path $outputDirectory $FileName), [System.Drawing.Imaging.ImageFormat]::Png)
    $format.Dispose()
    $borderPen.Dispose()
    $linePen.Dispose()
    $cap.Dispose()
    $brush.Dispose()
    $mutedBrush.Dispose()
    $titleFont.Dispose()
    $stateFont.Dispose()
    $bodyFont.Dispose()
    $labelFont.Dispose()
    $graphics.Dispose()
    $bitmap.Dispose()
}

New-StateDiagram -IncludeSleep $false -FileName 'state_diagram_core.png'
New-StateDiagram -IncludeSleep $true -FileName 'state_diagram_full.png'
