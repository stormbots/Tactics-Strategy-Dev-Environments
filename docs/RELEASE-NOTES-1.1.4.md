# Skyview Dev Setup 1.1.4

Startup validation now shows a prominent spinner and a clear message while checking installed tools. The spinner also accompanies operation progress. Reduced-motion preferences disable rotation while retaining the visible status and screen-reader announcements.

Install, Repair, Validate and Update show live details directly below their progress bar, without requiring a separate disclosure to be found or expanded. The running view brings progress and output forward, and focuses the progress status when an operation starts. Output follows new lines automatically; scrolling upward lets you read earlier output without being pulled back to the bottom. Details remain visible on the overview after completion or failure, and full logs remain available through Open log folder.

Frontend checks cover pending startup validation, streaming output, operation completion and failure, keyboard focus, desktop/mobile layouts, reduced motion and automated WCAG AA accessibility rules. Native packaging and backend checks run on disposable CI runners. This UI release retains the Windows 1.1.3 backend and its guarded Node 24 migration.

Follow the installer's update/reinstall flow and relaunch Skyview Dev Setup. This remains an unsigned mentor-testing prerelease; physical-laptop and assistive-technology acceptance testing remain required. Earlier releases remain available.
