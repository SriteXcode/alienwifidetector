[Setup]
AppName=WiFi Clone Detector
AppVersion=1.0
AppPublisher=Ritesh Kumar Yadav & Prem
DefaultDirName={autopf}\WiFi Clone Detector by ritesh&prem
DefaultGroupName=WiFi Clone Detector
OutputDir=dist
OutputBaseFilename=WiFi_Clone_Detector_Installer
Compression=lzma
SolidCompression=yes
SetupIconFile=icon.ico

[Files]
Source: "dist\main2.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\WiFi Clone Detector"; Filename: "{app}\WiFi Clone Detector.exe"
Name: "{commondesktop}\WiFi Clone Detector"; Filename: "{app}\WiFi Clone Detector.exe"

[Run]
Filename: "{app}\WiFi Clone Detector.exe"; Description: "Launch WiFi Clone Detector"; Flags: nowait postinstall skipifsilent
