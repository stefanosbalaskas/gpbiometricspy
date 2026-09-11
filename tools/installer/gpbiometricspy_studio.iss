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
UsePreviousAppDir=no
UsePreviousGroup=no
UsePreviousTasks=no
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

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Icons]
Name: "{autoprograms}\gpbiometricspy Studio"; Filename: "{app}\gpbiometricspy-studio-native.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\gpbiometricspy Studio"; Filename: "{app}\gpbiometricspy-studio-native.exe"; WorkingDir: "{app}"; Tasks: desktopicon
