// Prevents an extra console window from appearing on Windows in release builds.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|_app| {
            // Spawn the compiled FastAPI server as a sidecar.
            // In development the server is started by run_ui.bat; the sidecar
            // is only active in a packaged (release) build.
            #[cfg(not(debug_assertions))]
            {
                use tauri_plugin_shell::ShellExt;

                let shell = _app.shell();
                let sidecar = shell
                    .sidecar("api_server")
                    .expect("api_server sidecar not found in bundle");

                // Spawn without blocking — the child runs for the app lifetime.
                sidecar
                    .spawn()
                    .expect("failed to spawn api_server sidecar");
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}