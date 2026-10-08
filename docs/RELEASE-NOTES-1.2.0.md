# Skyview Dev Setup 1.2.0

This release candidate adds version-aware update status and makes scheduled maintenance visible in the GUI.

- Overview says **Updates available** when tools pass validation and managed updates exist. Passes, failed checks, and available updates have separate counts.
- Development tools show **Ready · installed version** or **Update available · installed version → available version**. Skipped or unavailable update checks are explicit. Versions come from installed tools or package metadata; Linux package versions can include distribution revisions.
- Windows checks the pinned Node 24 family independently of newer Node majors. Linux uses the same APT Node 24 resolver as its updater and checks the managed PyCharm release with JetBrains.
- **Schedule** displays the system task/timer, actual frequency, next/last run, last result, catch-up policy, managed scope, maintenance log folder, and Refresh. It is read-only and runs without elevation. Missing tasks and inaccessible history are explicit; it never treats missing history as success.
- **About** describes the app and Skyview Robotics, shows the app version/platform, and links to GitHub and skyviewrobotics.com in the system browser.
- Navigation, loading states, local timestamps, focus, narrow layouts, and reduced motion remain accessible.

Supported platforms: Windows 11 x64 and Linux Mint Cinnamon 22.x amd64. Node stays on 24.x; Python stays on 3.14.x. Windows installers ship unsigned by project decision.

Both native installers must pass CI before publication. Manual Windows/Mint acceptance for **1.2.0 is pending**; see [the feature acceptance checklist](ACCEPTANCE-1.2.0.md). The existing 1.1.5 manual sign-off remains historical evidence for that version. This candidate is not yet promoted to stable.
