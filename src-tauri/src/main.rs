#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use std::{
    fs::File,
    net::{SocketAddr, TcpStream},
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::Mutex,
    thread,
    time::Duration,
};
use tauri::{Manager, RunEvent};

const PORT: u16 = 8765; // keep in sync with config.json "port"

struct Engine(Mutex<Option<Child>>);

/// Find the project folder (the one containing engine/main.py), walking up from the exe.
fn project_root() -> PathBuf {
    if let Ok(p) = std::env::var("SPRITEFORGE_ROOT") {
        return p.into();
    }
    if let Ok(mut dir) = std::env::current_exe() {
        while dir.pop() {
            if dir.join("engine").join("main.py").exists() {
                return dir;
            }
        }
    }
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().to_path_buf()
}

fn spawn_engine(root: &PathBuf) -> Option<Child> {
    let venv_py = root.join(".venv").join("Scripts").join("python.exe");
    let python = if venv_py.exists() { venv_py } else { PathBuf::from("python") };
    let log = File::create(root.join("engine.log")).ok()?;
    let err = log.try_clone().ok()?;
    let mut cmd = Command::new(python);
    cmd.args(["-m", "engine.main"]).current_dir(root).stdout(Stdio::from(log)).stderr(Stdio::from(err));
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
    }
    cmd.spawn().ok()
}

fn main() {
    let app = tauri::Builder::default()
        .setup(|app| {
            let addr: SocketAddr = ([127, 0, 0, 1], PORT).into();
            let already = TcpStream::connect_timeout(&addr, Duration::from_millis(300)).is_ok();
            let child = if already { None } else { spawn_engine(&project_root()) };
            app.manage(Engine(Mutex::new(child)));
            let win = app.get_webview_window("main").unwrap();
            thread::spawn(move || {
                for _ in 0..240 {
                    if TcpStream::connect_timeout(&addr, Duration::from_millis(500)).is_ok() {
                        let _ = win.eval(&format!("window.location.replace('http://127.0.0.1:{}')", PORT));
                        return;
                    }
                    thread::sleep(Duration::from_millis(500));
                }
                let _ = win.eval("document.getElementById('msg').textContent='Engine did not start. Open engine.log in the project folder.'");
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building SpriteForge");

    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            if let Some(state) = handle.try_state::<Engine>() {
                if let Some(mut c) = state.0.lock().unwrap().take() {
                    let _ = c.kill();
                }
            }
        }
    });
}
