; BPS Fishing Macro V5.3 - Inno Setup Installer Script
; Date: 02/09/2026
; Distribution for clean PCs (without Python installed)

[Setup]
; Application identification
AppName=BPS Fishing Macro
AppVersion=5.3
AppPublisher=BPS
AppPublisherURL=https://github.com/BPS
AppSupportURL=https://github.com/BPS
AppUpdatesURL=https://github.com/BPS

; Installation settings
DefaultDirName={autopf}\BPS Fishing Macro
DefaultGroupName=BPS Fishing Macro
AllowNoIcons=yes
OutputDir=.
OutputBaseFilename=BPSFishingMacro-Setup-v5.3
; SetupIconFile=icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

; Architecture
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Permissions (admin required for PATH)
PrivilegesRequired=admin

; UI
LicenseFile=
InfoBeforeFile=
InfoAfterFile=
WizardImageFile=
WizardSmallImageFile=

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; ===== MAIN EXECUTABLE =====
Source: "bps_fishing_macroV5.3.exe"; DestDir: "{app}"; Flags: ignoreversion

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
Name: "{group}\BPS Fishing Macro"; Filename: "{app}\bps_fishing_macroV5.3.exe"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,BPS Fishing Macro}"; Filename: "{uninstallexe}"

; Desktop Shortcut (optional)
Name: "{autodesktop}\BPS Fishing Macro"; Filename: "{app}\bps_fishing_macroV5.3.exe"; WorkingDir: "{app}"; Tasks: desktopicon

; Quick Launch (optional)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\BPS Fishing Macro"; Filename: "{app}\bps_fishing_macroV5.3.exe"; WorkingDir: "{app}"; Tasks: quicklaunchicon

[Run]
; Run after installation (optional)
Filename: "{app}\bps_fishing_macroV5.3.exe"; Description: "{cm:LaunchProgram,BPS Fishing Macro}"; Flags: nowait postinstall skipifsilent

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
    'This wizard will install BPS Fishing Macro v5.3 on your computer.' + #13#10 + #13#10 +
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
