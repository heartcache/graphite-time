# Graphite Time

Hi there! Thank you for stopping by. 

**Graphite Time** is a small, minimalist focus timer and task tracker I built to help myself stay on track without feeling overwhelmed. I decided to share it publicly in case someone else finds it useful for their daily routine too.

It tries to stay out of your way—especially with a tiny mini-panel that quietly snaps to the edge of your screen—while keeping a gentle record of your work.

---

### What's inside

* **Flexible Timing:** Set sessions from 1 to 480 minutes, save your own presets, or use **Flow Mode** (a simple stopwatch) when you don't want a strict countdown. You can also take optional breaks or add +5/+10 minutes on the fly if you're in the zone.
* **No Penalty for Finishing Early:** If you wrap up a task ahead of schedule, you can mark it as done right away—your actual time spent and points are still saved.
* **Tasks & Goals:** Keep a simple to-do list, set daily goals (with or without time targets), and track a weekly target.
* **Gentle Gamification:** Earn points and levels for honest focus time, build daily streaks, and unlock 24 small achievements along the way.
* **Visual Stats:** Check your progress through daily charts, category breakdowns, an activity calendar, and insights into your most productive time of day.
* **Comfort & Languages:** Includes both Light and Dark themes, and supports 6 languages (English, Русский, 简体中文, Español, Português (BR), 日本語).

---

### How to get it

If you'd like to give it a try, you can grab the latest `Graphite-Time.exe` from the **[Releases](../../releases/latest)** page. It's portable, so no installation is needed—just run the file.

> **A small note for Windows users:** 
> Because I'm an independent developer and don't have an expensive paid code-signing certificate yet, Windows SmartScreen might show an *"Unknown publisher"* warning. 
> If you're comfortable proceeding, click **More info → Run anyway**. The entire source code is right here in the repository if you'd ever like to inspect it or run it yourself for peace of mind.

---

### Running from source

If you prefer running the Python script directly (or if you're on macOS/Linux):

```bash
pip install PySide6
python graphite_time.py
```

### Building the `.exe` yourself

If you want to compile your own executable:

```bash
python graphite_time.py --make-icon
pip install pyinstaller
pyinstaller --noconsole --onefile --name "Graphite-Time" --icon app.ico graphite_time.py
```

The compiled file will appear in the `dist/` folder.

---

### Feedback & Credits

This is a personal project, so there might be rough edges here and there. If you run into any bugs or have a quiet suggestion, feel free to open an issue—I'd really appreciate it.

* **Created by:** [heartcache](https://github.com/heartcache)
* **License:** MIT (feel free to tinker with it!)
