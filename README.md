# Qwen-AI-CPU ⚡

**Run a 35B-parameter Qwen model on a normal Windows laptop: CPU only, no GPU, no internet, no cloud.**

A small PyQt6 desktop launcher for [llama.cpp](https://github.com/ggml-org/llama.cpp). It starts `llama-server` with a GGUF model, shows a loading popup until the model is ready, then opens the built-in chat UI in your browser at `http://127.0.0.1:8080`. It works like a lightweight, offline alternative to Ollama.

It's tuned for **Qwen3.6-35B-A3B**, a Mixture-of-Experts model with 35B total parameters and about 3B active per token. That's why it runs at usable speed on a CPU.

---

## ✨ Features

- One-click **Start / Stop**: stopping frees all of the model's RAM.
- **Loading popup** that shows elapsed time and model memory while the model loads.
- **Live stats**: RAM used and free, model memory, CPU %.
- **RAM guard**: stops the model automatically if free RAM drops too low, so your PC doesn't freeze.
- **Prompt cache limit**: caps llama.cpp's prompt cache (8 GB by default) so it can't slowly use up your RAM.
- **Thinking mode** toggle (better reasoning but slower).
- Use **any `.gguf` model**: pick it with *Browse…*
- Settings are saved to `settings.json`. Errors are always shown with the last log lines, never hidden.
- `--autostart` and `--selftest` command-line flags.

---

## 📦 Downloads

| What | Link | Notes |
|---|---|---|
| **Python 3.11+** | https://www.python.org/downloads/windows/ | Tick *"Add python.exe to PATH"* during install |
| **llama.cpp engine** (build `b12561`, Windows CPU x64) | https://github.com/ggml-org/llama.cpp/releases/download/b12561/llama-b12561-bin-win-cpu-x64.zip | Release page: https://github.com/ggml-org/llama.cpp/releases/tag/b12561 · `setup.ps1` downloads this for you |
| **Model: Qwen3.6-35B-A3B (UD-IQ3_XXS GGUF)** | https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF/resolve/main/Qwen3.6-35B-A3B-UD-IQ3_XXS.gguf | All quantizations: https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF/tree/main |
| Original model card | https://huggingface.co/Qwen/Qwen3.6-35B-A3B | Official Qwen release |
| Microsoft VC++ Redistributable (only if llama-server won't start) | https://aka.ms/vs/17/release/vc_redist.x64.exe | Fixes missing `VCRUNTIME140.dll` errors |

> **Which quant should I use?** `UD-IQ3_XXS` is the default: it fits in about 12 GB of RAM and is a good fit for a 16 GB laptop. With 32 GB or more, try `UD-Q4_K_M` for better quality. With less RAM, try `UD-IQ2_M`. Any GGUF from the link above works; just select it with *Browse…*

> **Have an NVIDIA / AMD GPU?** Download a different engine build from the [release page](https://github.com/ggml-org/llama.cpp/releases/tag/b12561) (`cuda`, `vulkan` or `rocm` zip) and point the app at its `llama-server.exe`.

---

## 🖥️ Requirements

- Windows 10/11 x64
- **16 GB RAM** minimum for the default model (the model uses about 12 GB)
- Disk space for the model file (check its size on the Hugging Face page)
- Python 3.11+ (only to run from source or build the exe)

Python packages are listed in [`requirements.txt`](requirements.txt): `PyQt6`, `psutil`, and `pyinstaller` (pyinstaller is only needed to build the exe).

---

## 🚀 Installation

### Option A: automatic (recommended)

```powershell
git clone https://github.com/PhantomAnas/Qwen-AI-CPU.git
cd Qwen-AI-CPU

# installs Python packages + downloads the llama.cpp engine into .\llama
.\setup.ps1

# ...or also download the model into .\models (large download)
.\setup.ps1 -DownloadModel
```

> If PowerShell blocks the script, run this once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### Option B: manual

1. Install Python and the packages:
   ```powershell
   pip install -r requirements.txt
   ```
2. Download the [llama.cpp CPU zip](https://github.com/ggml-org/llama.cpp/releases/download/b12561/llama-b12561-bin-win-cpu-x64.zip) and extract **all** its files (`llama-server.exe` and every `.dll`) into a folder named `llama` next to `qwen_launcher.py`.
3. Download the [model `.gguf`](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF/resolve/main/Qwen3.6-35B-A3B-UD-IQ3_XXS.gguf) into a folder named `models` (or anywhere you like; you can pick it in the app).

Your folder should then look like this:

```
Qwen-AI-CPU/
├── qwen_launcher.py
├── llama/                 <- llama-server.exe + ggml*.dll, llama*.dll, ...
└── models/
    └── Qwen3.6-35B-A3B-UD-IQ3_XXS.gguf
```

---

## ▶️ Usage

```powershell
python qwen_launcher.py
```

1. Check the **model file** (use *Browse…* to pick any `.gguf`).
2. Click **Start model**. A loading popup appears, and when the model is ready the chat opens in your browser at http://127.0.0.1:8080
3. When you're done, click **Stop model** to free the RAM. Closing the window also asks whether to stop it.

| Flag | What it does |
|---|---|
| `--autostart` | Starts the model as soon as the window opens |
| `--selftest` | Starts the model, waits until it's ready (max 3 min), stops it, and writes `PASS`/`FAIL` to `logs/selftest.txt` |

### ⚙️ Settings

| Setting | Tip |
|---|---|
| CPU threads | Around 6 is usually as fast as more threads and leaves room for other apps |
| Context (tokens) | How much text the model can read at once. 8192 is fine for chat; bigger uses more RAM |
| Thinking mode | Better reasoning, but answers take 1–3 minutes. Off: 5–20 s |
| Prompt cache limit | Keep it around 512 MB. llama.cpp's 8 GB default slowly uses up memory |
| RAM guard | Stops the model automatically if free RAM drops below this value |
| Show log | Shows the engine's output live. The log is saved to `logs/server.log` |

Settings are saved to `settings.json` next to the script/exe (see [`settings.example.json`](settings.example.json)).

---

## 🛠️ Build a standalone .exe

```powershell
.\setup.ps1       # make sure .\llama exists
.\build.ps1       # or: .\build.ps1 -Python "C:\path\to\python.exe"
```

Output: `dist\LocalChatLauncher\LocalChatLauncher.exe`, with the `llama\` engine bundled. The model is not bundled; you pick it in the app. You can zip that folder and run it on any Windows PC without installing Python.

---

## ❓ Troubleshooting

| Problem | Fix |
|---|---|
| `llama-server.exe not found` | Run `.\setup.ps1`, or set the path with *Browse…* |
| `Port 8080 is already in use` | Change the port, or close the other server (Ollama, another llama-server, …) |
| Server stops right away | Click *Show log*. It's usually not enough RAM, a corrupt or incomplete download, or a missing [VC++ runtime](https://aka.ms/vs/17/release/vc_redist.x64.exe) |
| Very slow answers | Turn off Thinking mode, use a smaller context, close other heavy apps |
| PC freezes | Lower the context and raise the RAM guard, or use a smaller quant (`UD-IQ2_M`) |

---

## 🙏 Credits

- [llama.cpp](https://github.com/ggml-org/llama.cpp) by ggml-org: the inference engine and web chat UI
- [Qwen](https://huggingface.co/Qwen): the Qwen3.6 model
- [Unsloth](https://huggingface.co/unsloth): the GGUF quantizations
