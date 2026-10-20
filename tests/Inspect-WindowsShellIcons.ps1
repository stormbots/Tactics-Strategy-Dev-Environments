param(
    [Parameter(Mandatory = $true)][string]$PreviousExe,
    [Parameter(Mandatory = $true)][string]$CandidateExe,
    [Parameter(Mandatory = $true)][string]$CandidateIco,
    [Parameter(Mandatory = $true)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Cache-replacement probe is restricted to disposable CI.' }
if (Test-Path $OutputDirectory) { throw 'Use a new output directory.' }
New-Item -ItemType Directory $OutputDirectory | Out-Null
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @'
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

public static class SdeShellIconProbe {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    struct FileInfo {
        public IntPtr Icon;
        public int Index;
        public uint Attributes;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 260)] public string Name;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 80)] public string Type;
    }
    [DllImport("shell32.dll", CharSet = CharSet.Unicode, EntryPoint = "SHGetFileInfoW")]
    static extern IntPtr ShellIcon(string path, uint attributes, ref FileInfo info, uint size, uint flags);
    [DllImport("user32.dll", CharSet = CharSet.Unicode, EntryPoint = "PrivateExtractIconsW")]
    static extern uint Extract(string path, int index, int width, int height,
        out IntPtr icon, out uint id, uint count, uint flags);
    [DllImport("user32.dll")]
    static extern bool DrawIconEx(IntPtr dc, int x, int y, IntPtr icon, int width,
        int height, uint step, IntPtr brush, uint flags);
    [DllImport("user32.dll")]
    static extern bool DestroyIcon(IntPtr icon);
    [DllImport("shell32.dll")]
    static extern void SHChangeNotify(int change, uint flags, IntPtr item1, IntPtr item2);

    public static int[] Render(string path, int size, bool shell, string output) {
        IntPtr icon = IntPtr.Zero;
        try {
            if (shell) {
                FileInfo info = new FileInfo();
                if (ShellIcon(path, 0, ref info, (uint)Marshal.SizeOf(typeof(FileInfo)),
                    0x100u | (size == 16 ? 1u : 0u)) == IntPtr.Zero)
                    throw new InvalidOperationException("SHGetFileInfo failed");
                icon = info.Icon;
            } else {
                uint id;
                if (Extract(path, 0, size, size, out icon, out id, 1, 0) != 1)
                    throw new InvalidOperationException("PrivateExtractIcons failed");
            }
            if (icon == IntPtr.Zero) throw new InvalidOperationException("Missing icon");
            using (Bitmap bitmap = new Bitmap(size, size, PixelFormat.Format24bppRgb)) {
                using (Graphics graphics = Graphics.FromImage(bitmap)) {
                    graphics.Clear(Color.FromArgb(24, 32, 48));
                    IntPtr dc = graphics.GetHdc();
                    try {
                        if (!DrawIconEx(dc, 0, 0, icon, size, size, 0, IntPtr.Zero, 3))
                            throw new InvalidOperationException("DrawIconEx failed");
                    } finally { graphics.ReleaseHdc(dc); }
                }
                bitmap.Save(output, ImageFormat.Png);
                return new int[] { bitmap.GetPixel(0, 0).R, bitmap.GetPixel(size - 1, 0).R,
                    bitmap.GetPixel(0, size - 1).R, bitmap.GetPixel(size - 1, size - 1).R };
            }
        } finally { if (icon != IntPtr.Zero) DestroyIcon(icon); }
    }
    public static void Refresh() {
        // Documented Shell icon/thumbnail cache invalidation, disposable CI only.
        SHChangeNotify(0x08000000, 0x1000, IntPtr.Zero, IntPtr.Zero);
    }
}
'@
$previous = (Resolve-Path $PreviousExe).Path
$candidate = (Resolve-Path $CandidateExe).Path
$output = (Resolve-Path $OutputDirectory).Path
$samePath = Join-Path $output 'same-name.exe'
$linkPath = Join-Path $output 'application.lnk'
$versionedIcon = Join-Path $output 'skyview-dev-setup-v1.2.11.ico'
$shortcutShell = New-Object -ComObject WScript.Shell
$rows = New-Object System.Collections.Generic.List[object]
function Measure-Icons([string]$Stage, [string]$Exe) {
    foreach ($size in @(16, 32, 48, 256)) {
        foreach ($shell in @($false, $true)) {
            if ($shell -and $size -notin @(16, 32)) { continue }
            $api = if ($shell) { 'shell' } else { 'direct' }
            $image = Join-Path $output "$Stage-$api-$size.png"
            $corners = [SdeShellIconProbe]::Render($Exe, $size, $shell, $image)
            $rounded = @($corners | Where-Object { $_ -ge 160 }).Count -eq 0
            $rows.Add([pscustomobject]@{Stage=$Stage;Api=$api;Size=$size;CornerRed=$corners;Rounded=$rounded})
        }
    }
}
function Measure-Shortcut([string]$Stage) {
    foreach ($size in @(16, 32)) {
        $image = Join-Path $output "$Stage-shell-$size.png"
        $corners = [SdeShellIconProbe]::Render($linkPath, $size, $true, $image)
        # The Shell adds the shortcut-arrow badge at bottom left. Check the
        # three unbadged corners; retain all four measurements in the evidence.
        $rounded = @($corners[0], $corners[1], $corners[3] | Where-Object { $_ -ge 160 }).Count -eq 0
        $rows.Add([pscustomobject]@{Stage=$Stage;Api='shell';Size=$size;CornerRed=$corners;Rounded=$rounded})
    }
}
Copy-Item $previous $samePath
$link = $shortcutShell.CreateShortcut($linkPath)
$link.TargetPath = $samePath
$link.IconLocation = "$samePath,0"
$link.Save()
Measure-Icons 'previous' $samePath
Measure-Shortcut 'previous-shortcut'
Copy-Item $candidate $samePath -Force
Measure-Icons 'replacement' $samePath
[SdeShellIconProbe]::Refresh()
Measure-Icons 'refreshed' $samePath
Measure-Icons 'fresh-path' $candidate
Copy-Item (Resolve-Path $CandidateIco).Path $versionedIcon
$link = $shortcutShell.CreateShortcut($linkPath)
$link.IconLocation = "$versionedIcon,0"
$link.Save()
Measure-Shortcut 'versioned-shortcut'
$rows | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $output 'results.json')
$rows | Format-Table -AutoSize
if (@($rows | Where-Object { $_.Stage -eq 'previous' -and $_.Api -eq 'direct' -and $_.Rounded }).Count) {
    throw 'Previous square-icon fixture did not render square.'
}
if (@($rows | Where-Object { $_.Stage -in @('fresh-path','versioned-shortcut') -and -not $_.Rounded }).Count) {
    throw 'Rounded candidate or versioned shortcut rendered square; inspect evidence.'
}
Write-Output 'SDE_WINDOWS_SHELL_ICON_PROBE_OK'
