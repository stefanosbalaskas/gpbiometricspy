#define BundleDir GetEnv("GPBIOMETRICSPY_INSTALLER_BUNDLE")
#define IconPath GetEnv("GPBIOMETRICSPY_INSTALLER_ICON")
#define AppVersion GetEnv("GPBIOMETRICSPY_INSTALLER_APP_VERSION")
#define FileVersion GetEnv("GPBIOMETRICSPY_INSTALLER_FILE_VERSION")

#if BundleDir == ""
  #error GPBIOMETRICSPY_INSTALLER_BUNDLE is required
#endif
#if IconPath == ""
  #error GPBIOMETRICSPY_INSTALLER_ICON is required
#endif
#if AppVersion == ""
  #error GPBIOMETRICSPY_INSTALLER_APP_VERSION is required
#endif
#if FileVersion == ""
  #error GPBIOMETRICSPY_INSTALLER_FILE_VERSION is required
#endif

[Setup]
AppId=fd3ca1af-0ebb-5061-9c59-f7ab1079252e
AppName=gpbiometricspy Studio
AppVersion={#AppVersion}
AppPublisher=Stefanos Balaskas
AppSupportURL=https://developer.microsoft.com/microsoft-edge/webview2/
DefaultDirName={localappdata}\Programs\gpbiometricspy Studio
DefaultGroupName=gpbiometricspy Studio
DisableProgramGroupPage=yes
AllowNoIcons=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=gpbiometricspy-studio-setup
SetupIconFile={#IconPath}
UninstallDisplayName=gpbiometricspy Studio
UninstallDisplayIcon={app}\gpbiometricspy-studio-native.exe
Uninstallable=yes
UsePreviousAppDir=yes
UsePreviousGroup=yes
UsePreviousTasks=yes
UsePreviousPrivileges=no
ChangesEnvironment=no
ChangesAssociations=no
RestartApplications=no
RestartIfNeededByRun=no
CloseApplications=no
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
VersionInfoCompany=Stefanos Balaskas
VersionInfoDescription=gpbiometricspy Studio Installer
VersionInfoProductName=gpbiometricspy Studio
VersionInfoProductVersion={#FileVersion}
VersionInfoVersion={#FileVersion}

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Registry]
Root: HKCU; Subkey: "Software\StefanosBalaskas\gpbiometricspy Studio"; ValueType: string; ValueName: "InstalledFileVersion"; ValueData: "{#FileVersion}"; Flags: uninsdeletevalue uninsdeletekeyifempty

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Icons]
Name: "{autoprograms}\gpbiometricspy Studio"; Filename: "{app}\gpbiometricspy-studio-native.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\gpbiometricspy Studio"; Filename: "{app}\gpbiometricspy-studio-native.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Code]
const
  WebView2ClientKey = 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  WebView2DownloadUrl = 'https://developer.microsoft.com/microsoft-edge/webview2/';
  UpgradePolicyKey = 'Software\StefanosBalaskas\gpbiometricspy Studio';
  UpgradePolicyValue = 'InstalledFileVersion';
  UninstallRegistrationKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\fd3ca1af-0ebb-5061-9c59-f7ab1079252e_is1';
  TargetFileVersion = '{#FileVersion}';

function IsUsableWebView2Version(const Version: String): Boolean;
begin
  Result := (Trim(Version) <> '') and (Trim(Version) <> '0.0.0.0');
end;

function DetectWebView2Runtime(var Version: String; var Scope: String): Boolean;
begin
  Result := False;
  Version := '';
  Scope := '';

  { CI may force the stricter missing-runtime branch. There is intentionally
    no environment variable that can bypass a real missing-runtime result. }
  if GetEnv('GPBIOMETRICSPY_CI_FORCE_WEBVIEW2_MISSING') = '1' then
  begin
    Log('WebView2 Runtime forced missing by CI validation hook.');
    Exit;
  end;

  if RegQueryStringValue(HKLM32, WebView2ClientKey, 'pv', Version) and
     IsUsableWebView2Version(Version) then
  begin
    Scope := 'machine';
    Result := True;
    Exit;
  end;

  Version := '';
  if RegQueryStringValue(HKCU, WebView2ClientKey, 'pv', Version) and
     IsUsableWebView2Version(Version) then
  begin
    Scope := 'user';
    Result := True;
    Exit;
  end;
end;

function DetectInstalledStudioVersion(var Version: Int64; var VersionText: String;
  var VersionSource: String): Boolean;
var
  Marker: String;
  Executable: String;
begin
  Result := False;
  VersionText := '';
  VersionSource := '';

  if RegQueryStringValue(HKCU, UpgradePolicyKey, UpgradePolicyValue, Marker) then
  begin
    Marker := Trim(Marker);
    if StrToVersion(Marker, Version) then
    begin
      VersionText := Marker;
      VersionSource := 'registry';
      Result := True;
      Exit;
    end;
    Log(Format('Upgrade policy: invalid registry version marker ignored: %s', [Marker]));
  end;

  Executable := ExpandConstant('{app}\gpbiometricspy-studio-native.exe');
  if GetPackedVersion(Executable, Version) then
  begin
    if not GetVersionNumbersString(Executable, VersionText) then
      VersionText := VersionToStr(Version);
    VersionSource := 'executable';
    Result := True;
  end;
end;

function CheckUpgradePolicy(var ErrorText: String): Boolean;
var
  TargetVersion: Int64;
  InstalledVersion: Int64;
  InstalledText: String;
  InstalledSource: String;
  Comparison: Integer;
begin
  Result := False;
  ErrorText := '';

  if not StrToVersion(TargetFileVersion, TargetVersion) then
  begin
    ErrorText := 'Setup cannot determine its numeric release file version.';
    Log('Upgrade policy: target file version is invalid.');
    Exit;
  end;

  if DetectInstalledStudioVersion(InstalledVersion, InstalledText, InstalledSource) then
  begin
    Comparison := ComparePackedVersion(InstalledVersion, TargetVersion);
    if Comparison < 0 then
    begin
      Log(Format('Upgrade policy: in-place upgrade allowed; installed=%s; target=%s; source=%s',
        [InstalledText, TargetFileVersion, InstalledSource]));
      Result := True;
      Exit;
    end;

    if Comparison = 0 then
    begin
      Log(Format('Upgrade policy: same-version repair allowed; installed=%s; target=%s; source=%s',
        [InstalledText, TargetFileVersion, InstalledSource]));
      Result := True;
      Exit;
    end;

    Log(Format('Upgrade policy: downgrade blocked; installed=%s; target=%s; source=%s',
      [InstalledText, TargetFileVersion, InstalledSource]));
    ErrorText := Format(
      'A newer gpbiometricspy Studio version (%s) is already installed. Setup %s will not downgrade it. Uninstall the newer version first if you intentionally need an older release.',
      [InstalledText, TargetFileVersion]);
    Exit;
  end;

  if RegKeyExists(HKCU, UninstallRegistrationKey) then
  begin
    Log('Upgrade policy: existing installation has indeterminate version; setup blocked fail-closed.');
    ErrorText :=
      'An existing gpbiometricspy Studio installation was detected, but its version could not be verified. Repair or uninstall that installation before continuing.';
    Exit;
  end;

  Log(Format('Upgrade policy: first install allowed; target=%s', [TargetFileVersion]));
  Result := True;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  RuntimeVersion: String;
  RuntimeScope: String;
  UpgradeError: String;
begin
  NeedsRestart := False;
  Result := '';

  if not CheckUpgradePolicy(UpgradeError) then
  begin
    Result := UpgradeError;
    Exit;
  end;

  if DetectWebView2Runtime(RuntimeVersion, RuntimeScope) then
  begin
    Log('WebView2 Runtime detected: scope=' + RuntimeScope + '; version=' + RuntimeVersion);
    Exit;
  end;

  Log('WebView2 Runtime missing; setup cannot continue.');
  Result :=
    'Microsoft Edge WebView2 Runtime is required to run gpbiometricspy Studio.' + #13#10 + #13#10 +
    'Install the Evergreen WebView2 Runtime from Microsoft, then run this setup again:' + #13#10 +
    WebView2DownloadUrl;
end;
