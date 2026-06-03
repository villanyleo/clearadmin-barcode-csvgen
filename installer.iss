; Inno Setup szkript a ClearAdmin CSV vonalkód olvasóhoz.
; A PyInstaller által épített futtatható fájlt Windows Setup.exe telepítőbe csomagolja.
; Az AppVersion értékét a CI munkafolyamat adja át a parancssorban: /DAppVersion=...

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define AppName "ClearAdmin CSV vonalkód olvasó"
#define ExeName "ClearAdmin-CSV-vonalkod-olvaso.exe"

[Setup]
AppId={{C1EA2A2D-1111-4C7B-9E3A-CLEARADMINCSV1}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=VillanyLeó
DefaultDirName={autopf}\ClearAdmin CSV vonalkod olvaso
DefaultGroupName=ClearAdmin CSV vonalkod olvaso
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=ClearAdmin-CSV-vonalkod-olvaso-Setup-{#AppVersion}
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#ExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "hungarian"; MessagesFile: "compiler:Languages\Hungarian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\{#ExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#ExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#ExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
