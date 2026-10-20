//! The window caption and Windows taskbar use separate icon slots.
//! Load the running executable's resource directly so a stale Shell cache entry
//! for its stable filename cannot supply the taskbar icon.

#[cfg(windows)]
pub fn set_taskbar_icon(window: &tauri::WebviewWindow) {
    use std::ptr;
    use windows_sys::Win32::{
        System::LibraryLoader::GetModuleHandleW,
        UI::WindowsAndMessaging::{
            LoadImageW, SendMessageW, ICON_BIG, IMAGE_ICON, LR_DEFAULTSIZE, LR_SHARED, WM_SETICON,
        },
    };

    let Ok(window) = window.hwnd() else { return };
    // Tauri embeds the application's ICO as resource 32512. LR_SHARED keeps
    // ownership with Windows for the lifetime of the loaded module.
    unsafe {
        let instance = GetModuleHandleW(ptr::null());
        if instance.is_null() {
            return;
        }
        let icon = LoadImageW(
            instance,
            tauri::utils::platform::WINDOWS_APP_ICON_RESOURCE_ID as usize as *const u16,
            IMAGE_ICON,
            0,
            0,
            LR_DEFAULTSIZE | LR_SHARED,
        );
        if !icon.is_null() {
            SendMessageW(window.0, WM_SETICON, ICON_BIG as usize, icon as isize);
        }
    }
}
