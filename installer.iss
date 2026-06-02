; Inno Setup script for the HJC Barcode Scanner.
; Wraps the PyInstaller-built executable into a Windows Setup.exe installer.
; AppVersion is supplied on the command line via /DAppVersion=... by the CI workflow.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{F2A7B3C1-9D4E-4A6B-8C2F-HJCBARCODE001}
AppName=HJC Barcode Scanner
AppVersion={#AppVersion}
AppPublisher=VillanyLeó
DefaultDirName={autopf}\HJC Barcode Scanner
DefaultGroupName=HJC Barcode Scanner
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=HJC-Barcode-Scanner-Setup-{#AppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\HJC Barcode Scanner.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\HJC Barcode Scanner"; Filename: "{app}\HJC Barcode Scanner.exe"
Name: "{group}\{cm:UninstallProgram,HJC Barcode Scanner}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\HJC Barcode Scanner"; Filename: "{app}\HJC Barcode Scanner.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\HJC Barcode Scanner.exe"; Description: "{cm:LaunchProgram,HJC Barcode Scanner}"; Flags: nowait postinstall skipifsilent
