#define MyAppName "BPS Fishing Macro"
#define MyAppVersion "1.0.3"
#define MyAppPublisher "BPS Softworks"
#define MyAppURL "https://github.com/BPS-Softworks"
#define MyAppExeName "bps_fishing_macro_v1.0.3.exe"

; BPS Fishing Macro V5.3 - Inno Setup Installer Script
; Date: 02/09/2026
; Distribution for clean PCs (without Python installed)

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{A8F93210-4B1C-4D5E-9F2A-3B6C8A1D7E8F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Installation settings
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName=BPS Fishing Macro
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=bps_fishing_macro_v1.0.3_setup
; SetupIconFile=icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

; Architecture
; "ArchitecturesAllowed=x64compatible" specifies that Setup cannot run
; on anything but x64 and Windows 11 on Arm.
ArchitecturesAllowed=x64compatible
; "ArchitecturesInstallIn64BitMode=x64compatible" requests that the
; install be done in "64-bit mode" on x64 or Windows 11 on Arm,
; meaning that {autopf} is the native 64-bit Program Files directory
; and the 64-bit view of the registry will be used.
ArchitecturesInstallIn64BitMode=x64compatible

; Permissions (admin required for PATH)
; Uncomment the following line to run in non administrative install mode (install for current user only.)
;PrivilegesRequired=lowest
PrivilegesRequired=admin

; UI
LicenseFile=
InfoBeforeFile=
InfoAfterFile=
WizardImageFile=
WizardSmallImageFile=
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; ===== MAIN EXECUTABLE =====
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; NOTE: Settings JSON is NOT included - users will configure their own webhooks/settings
; The application will create bpsfishmacrosettings.json with defaults on first run

; ===== TESSERACT OCR (PORTABLE) =====
; Main executable
Source: "tesseract-portable\tesseract.exe"; DestDir: "{app}\tesseract"; Flags: ignoreversion

; Required DLLs (all)
Source: "tesseract-portable\*.dll"; DestDir: "{app}\tesseract"; Flags: ignoreversion

; Training data (tessdata)
Source: "tesseract-portable\tessdata\*"; DestDir: "{app}\tesseract\tessdata"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu
Name: "{group}\BPS Fishing Macro"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,BPS Fishing Macro}"; Filename: "{uninstallexe}"

; Desktop Shortcut (optional)
Name: "{autodesktop}\BPS Fishing Macro"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

; Quick Launch (optional)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\BPS Fishing Macro"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: quicklaunchicon

[Run]
; Run after installation (optional)
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,BPS Fishing Macro}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up residual files on uninstall
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\*.tmp"
Type: dirifempty; Name: "{app}"

[Code]
// Pascal code for Python detection (optional)
function IsPythonInstalled(): Boolean;
var
  ResultCode: Integer;
begin
  // Check if Python is installed (not required, but warns user)
  Result := RegKeyExists(HKEY_CURRENT_USER, 'Software\Python') or
            RegKeyExists(HKEY_LOCAL_MACHINE, 'Software\Python');
end;

procedure InitializeWizard;
begin
  // Custom welcome message
  WizardForm.WelcomeLabel2.Caption := 
    'This wizard will install BPS Fishing Macro v{#MyAppVersion} on your computer.' + #13#10 + #13#10 +
    'The installer includes:' + #13#10 +
    '  * Macro executable (95 MB)' + #13#10 +
    '  * Tesseract OCR portable (~50 MB)' + #13#10 +
    '  * Default settings' + #13#10 + #13#10 +
    'No additional installation required!';
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  // Check if executable is not running
  Result := '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Success message
    MsgBox('Installation completed successfully!' + #13#10 + #13#10 +
           'Tesseract OCR was installed at:' + #13#10 +
           ExpandConstant('{app}\tesseract') + #13#10 + #13#10 +
           'You can now run the macro.', mbInformation, MB_OK);
  end;
end;
