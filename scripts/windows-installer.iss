; Compile with Inno Setup after running scripts/build_desktop.py.
[Setup]
AppName=Sentinel
AppVersion=0.3.0rc1
DefaultDirName={localappdata}\Programs\Sentinel
DefaultGroupName=Sentinel
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Sentinel-Setup-Windows
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\Sentinel.exe
[Files]
Source: "..\dist\Sentinel\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Sentinel"; Filename: "{app}\Sentinel.exe"
Name: "{autodesktop}\Sentinel"; Filename: "{app}\Sentinel.exe"
[Run]
Filename: "{app}\Sentinel.exe"; Description: "Open Sentinel"; Flags: nowait postinstall skipifsilent
