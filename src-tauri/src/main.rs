#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use tauri::api::process::{Command, CommandEvent};
use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let window = app.get_window("main").unwrap();
            
            // Launch the Python backend as a sidecar
            // The sidecar binary must be named `ck3-engine` and placed in `src-tauri/bin/`
            // with the target triple appended, e.g., `ck3-engine-x86_64-pc-windows-msvc.exe`
            let (mut rx, mut child) = Command::new_sidecar("ck3-engine")
                .expect("failed to create `ck3-engine` binary command")
                .spawn()
                .expect("Failed to spawn sidecar");

            // Listen for sidecar events (optional, for logging)
            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    if let CommandEvent::Stdout(line) = event {
                        println!("Engine: {}", line);
                    }
                }
            });

            // Ensure the child process is killed when the window is closed
            window.on_window_event(move |event| match event {
                tauri::WindowEvent::Destroyed => {
                    println!("Window destroyed, killing sidecar...");
                    child.kill().expect("Failed to kill sidecar");
                }
                _ => {}
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
