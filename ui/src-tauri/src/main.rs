// Prevents an extra console window from appearing on Windows in release builds
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri_plugin_shell::ShellExt;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // Spawn the compiled FastAPI server as a sidecar.
            // In development the server is started manually; the sidecar only
            // runs in the packaged application.
            #[cfg(not(debug_assertions))]
            {
                let shell = app.shell();
                let sidecar = shell
                    .sidecar("api_server")
                    .expect("api_server sidecar not found in bundle");

                // Spawn without blocking — the child runs for the lifetime of the app
                sidecar
                    .spawn()
                    .expect("failed to spawn api_server sidecar");
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}