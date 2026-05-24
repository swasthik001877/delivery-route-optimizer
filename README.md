<div align="center">

# 🚚 Last-Mile Delivery Route Optimizer

### MCA Final Year Major Project

**A production-ready desktop application that solves the Travelling Salesman Problem (TSP) for last-mile logistics using a custom-built Genetic Algorithm — with no cloud, no paid APIs, and no internet server.**

<br/>

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet)
![SQLite](https://img.shields.io/badge/Database-SQLite3-lightgrey?logo=sqlite)
![Leaflet](https://img.shields.io/badge/Maps-Leaflet%20%2B%20OSRM-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Lines](https://img.shields.io/badge/Lines%20of%20Code-5200%2B-orange)
![Tests](https://img.shields.io/badge/Tests-19%20Passing-brightgreen)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Running the App](#-running-the-app)
- [Usage Guide](#-usage-guide)
- [Genetic Algorithm](#-genetic-algorithm-explained)
- [GA Parameter Guide](#-ga-parameter-guide)
- [Database Schema](#-database-schema)
- [Testing](#-testing)
- [Sample Data](#-sample-data)
- [Demo Flow](#-demo-flow-for-viva)

---

## 🎯 Overview

This application is a **smart logistics optimization system** that:

- Accepts multiple delivery addresses and geocodes them using OpenStreetMap (free, no API key)
- Stores all data locally in an SQLite3 database
- Optimizes the delivery order using a **hand-coded Genetic Algorithm** (no scipy, no OR-Tools)
- Visualizes the optimized route on an **interactive map with real road-aligned routing** via OSRM
- Generates professional reports in CSV, JSON, PDF, and Excel formats

Everything runs **100% locally** on your machine.

---

## ✨ Features

| Module | Description |
|--------|-------------|
| 🔐 **Authentication** | Login / Register with bcrypt password hashing, remember me |
| 📦 **Delivery Management** | Add, edit, delete, search, bulk import CSV/JSON, checkbox multi-select delete |
| 🌍 **Geocoding** | Nominatim (OpenStreetMap) with rate limiting, retry, and coordinate caching |
| 📐 **Distance Matrix** | Haversine formula, SQLite cache, handles up to 500 nodes |
| 🧬 **Genetic Algorithm** | Custom GA: OX crossover, swap + 2-opt mutation, tournament selection, elitism |
| 🗺️ **Route Maps** | Self-contained HTML maps — road-aligned routing via OSRM, works offline with fallback |
| 📊 **Analytics** | Matplotlib charts: distance improvement, run comparison, runtime, delivery stats |
| 📂 **History** | View, compare, and manage past optimization runs |
| 📤 **Exports** | CSV, JSON, PDF (ReportLab), Excel (openpyxl) |
| 🖥️ **Terminal Logs** | Rich-powered colored logs and progress output |

---

## 🛠 Tech Stack

| Technology | Version | Role |
|-----------|---------|------|
| Python | 3.11 | Core language |
| CustomTkinter | 5.2.2 | Modern dark/light desktop GUI |
| SQLAlchemy | 2.0.30 | ORM / database management |
| SQLite3 | built-in | Local database |
| Geopy + Nominatim | 2.4.1 | Free geocoding (no API key) |
| NumPy | 1.26.4 | Numerical computation |
| Matplotlib | 3.8.4 | Analytics charts |
| Leaflet + LRM | 1.9.4 | Interactive route maps (bundled, offline-ready) |
| OSRM | public API | Road-aligned routing (called from browser) |
| Rich | 13.7.1 | Terminal logging and progress bars |
| bcrypt | 4.1.3 | Secure password hashing |
| ReportLab | 4.2.0 | PDF export |
| openpyxl | 3.1.2 | Excel export |

---

## 📁 Project Structure

```
delivery_optimizer/
│
├── main.py                         # Entry point — python main.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── algorithms/
│   └── genetic_algorithm.py        # Complete GA from scratch (TSP solver)
│
├── models/
│   └── models.py                   # SQLAlchemy ORM — 7 tables
│
├── services/
│   ├── auth_service.py             # Login, register, session management
│   ├── delivery_service.py         # CRUD, CSV/JSON import, distance cache
│   ├── geocoding.py                # Nominatim geocoder with rate limiting
│   └── optimization_service.py     # Orchestrate GA + persist results
│
├── gui/
│   ├── theme.py                    # Colors, fonts, widget style constants
│   ├── main_app.py                 # Main window + sidebar + login root
│   ├── dashboard_frame.py          # Overview dashboard with stats cards
│   ├── address_frame.py            # Delivery management (with bulk delete)
│   ├── optimizer_frame.py          # GA configuration + live monitor
│   ├── map_frame.py                # Embedded map viewer
│   ├── analytics_frame.py          # Charts panel with export buttons
│   └── history_frame.py            # Run history (with bulk delete)
│
├── analytics/
│   └── charts.py                   # Matplotlib chart functions
│
├── maps/
│   └── map_service.py              # Self-contained Leaflet HTML map generator
│
├── exports/
│   └── export_service.py           # CSV, JSON, PDF, Excel report generation
│
├── utils/
│   └── helpers.py                  # Logger, validators, Rich terminal helpers
│
├── assets/                         # Bundled Leaflet JS/CSS (no CDN needed)
│   ├── leaflet.js
│   ├── leaflet.css
│   ├── leaflet-routing-machine.js
│   ├── leaflet-routing-machine.css
│   └── images/                     # Marker icons (base64-embedded in maps)
│
├── database/                       # SQLite DB created here on first run
├── logs/                           # Daily log files
├── maps/                           # Generated HTML route maps
├── exports/                        # Generated report exports
│
├── sample_data/
│   ├── sample_deliveries.csv       # 15 pan-India delivery addresses
│   └── sample_bengaluru.json       # 8 Bengaluru stops (pre-geocoded, demo-ready)
│
└── tests/
    └── test_all.py                 # 19 unit + integration tests
```

---

## ⚙️ Installation

### Prerequisites

- Python 3.11 or higher
- pip

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/delivery-route-optimizer.git
cd delivery-route-optimizer

# 2. Create a virtual environment (recommended)
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

> **Linux users:** If you get a Tkinter error, install it with:
> ```bash
> sudo apt install python3-tk
> ```

---

## 🚀 Running the App

```bash
# GUI mode (default)
python main.py

# CLI mode (no display — for testing or headless environments)
python main.py --cli

# Run tests
python -m pytest tests/ -v
```

### Default Login Credentials

```
Username : admin
Password : admin123
```
*Created automatically on first launch.*

---

## 📖 Usage Guide

### 1. Add Deliveries
Go to **Deliveries** tab → click **+ Add** to add individual addresses, or use **Import JSON** / **Import CSV** for bulk import. Use the provided sample files for a quick demo.

### 2. Geocode Addresses
Click **Geocode All** to convert addresses to GPS coordinates via Nominatim. Coordinates are cached in the database — no re-geocoding on subsequent runs. A green dot (●) indicates geocoded stops.

### 3. Run the Optimizer
Go to **Optimizer** tab → select deliveries using checkboxes → configure GA parameters → click **▶ START OPTIMIZATION**. Watch the live generation counter, distance graph, and terminal log update in real time.

### 4. View the Route Map
After optimization, the app automatically switches to the **Maps** tab. The generated map:
- Uses **road-aligned routing** via OSRM (requires internet in the browser)
- Falls back to straight dashed lines when offline
- Has numbered stop markers (green = start/end)
- Supports Dark / Light / Street tile layers
- Works from `file://` — all JS/CSS are bundled locally

### 5. Explore Analytics
Go to **Analytics** tab to view:
- Distance improvement per generation
- Run summary (distance + stats side by side)
- Comparison across multiple runs
- Runtime analysis

All charts can be exported as **PNG** or **PDF** directly from the chart toolbar.

### 6. Export Reports
In the **History** tab, select any completed run and export as **CSV**, **JSON**, **PDF**, or **Excel**.

---

## 🧬 Genetic Algorithm Explained

The GA is implemented **entirely from scratch** in `algorithms/genetic_algorithm.py` — no optimization libraries used.

### How It Works

```
1. INITIALISE  →  Create N random delivery orderings (population)
2. EVALUATE    →  Score each route: fitness = 1 / total_distance
3. SELECT      →  Tournament selection — best of K random individuals
4. CROSSOVER   →  Ordered Crossover (OX) — preserves relative stop order
5. MUTATE      →  Randomly swap two stops (keeps diversity)
6. ELITISM     →  Top 5 routes always survive unchanged
7. REPEAT      →  Until max generations or stagnation (80 gens no improvement)
8. 2-OPT       →  Final local search polish on the best route found
```

### Distance Formula

Uses the **Haversine formula** for accurate geodesic distance between GPS coordinates:

```
a = sin²(Δlat/2) + cos(lat₁)·cos(lat₂)·sin²(Δlon/2)
d = 2R · arcsin(√a)      where R = 6371 km
```

---

## 🎛 GA Parameter Guide

| Parameter | What It Means | Recommended |
|-----------|--------------|-------------|
| **Population Size** | Number of different route solutions created each generation. More = better results but slower. Think of it as 100 runners in a race. | 50 – 150 |
| **Max Generations** | How many rounds of evolution to run. Each generation, bad routes die and good ones breed. More = more refined answer, takes longer. | 200 – 500 |
| **Mutation Rate** | Probability of randomly swapping two delivery stops in a route. Prevents the algorithm from getting stuck. Too high = chaos. Too low = stuck early. | 0.01 – 0.05 |
| **Crossover Rate** | Probability that two parent routes combine to create a child route. High value = most new routes are bred from the best parents. | 0.80 – 0.95 |

---

## 🗄 Database Schema

| Table | Purpose |
|-------|---------|
| `users` | User accounts — bcrypt hashed passwords |
| `user_settings` | Per-user GA defaults and UI preferences |
| `deliveries` | Delivery records with GPS coordinates |
| `distance_cache` | Cached pairwise Haversine distances (avoids recomputation) |
| `optimization_runs` | GA run metadata, parameters, fitness history (JSON) |
| `optimized_routes` | Ordered stop sequences for each run |
| `application_settings` | Key-value application configuration |

- All tables use primary keys, foreign keys with `ON DELETE CASCADE`, and indexes
- SQLite WAL mode enabled for better concurrent performance
- Database auto-created on first launch at `database/optimizer.db`

---

## 🧪 Testing

```bash
python -m pytest tests/test_all.py -v
```

**19 tests covering:**

- Haversine accuracy (known city distances)
- Distance matrix shape, symmetry, zero diagonal
- Population initialization (valid permutations)
- Ordered Crossover — no duplicates, all genes present
- Swap mutation — preserves gene set
- 2-opt — never worsens a route
- Full GA integration — valid route indices, positive distance
- Auth service — registration, login, wrong password rejection
- Delivery service — add, search, duplicate address prevention

---

## 📦 Sample Data

### `sample_data/sample_bengaluru.json`
8 Bengaluru locations with **pre-geocoded coordinates** — perfect for instant demo without waiting for geocoding. Import this and run the optimizer immediately.

### `sample_data/sample_deliveries.csv`
15 delivery addresses across major Indian cities (Bengaluru, Delhi, Mumbai, Chennai, etc.) — requires geocoding before optimization.

**Quick demo with pre-geocoded data:**
1. Deliveries → Import JSON → select `sample_bengaluru.json`
2. Optimizer → Start (all 8 stops ready immediately)
3. Maps tab opens automatically with the road-aligned route

---

## 🎬 Demo Flow (for Viva)

| Step | Action | What to Show |
|------|--------|-------------|
| 1 | `python main.py` | Terminal banner, DB init, GUI launch |
| 2 | Login with `admin / admin123` | Login screen → Dashboard |
| 3 | Dashboard | Stats cards, recent history, system status |
| 4 | Import `sample_bengaluru.json` | 8 stops added instantly, pre-geocoded |
| 5 | Optimizer tab | Explain GA parameters using the help cards |
| 6 | Start optimization | Live generation counter, distance dropping |
| 7 | Maps tab | Interactive Leaflet map with OSRM road routing |
| 8 | Analytics tab | Distance improvement chart, run summary |
| 9 | History tab | Show past runs, export PDF report |
| 10 | Dark/Light theme toggle | Show theme switching |

---

## 📄 License

This project is developed as an MCA Final Year Major Project for academic purposes.

---

<div align="center">
Made with ❤️ for MCA Final Year Project
</div>