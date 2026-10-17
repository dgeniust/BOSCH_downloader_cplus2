# Multi-Threaded Download Manager

<p align="center">
  <img src="https://img.shields.io/badge/C%2B%2B-17-00599C?style=for-the-badge&logo=cplusplus&logoColor=white" alt="C++17">
  <img src="https://img.shields.io/badge/Ubuntu-Linux-E95420?style=for-the-badge&logo=ubuntu&logoColor=white" alt="Ubuntu">
  <img src="https://img.shields.io/badge/Linux-POSIX-FCC624?style=for-the-badge&logo=linux&logoColor=black" alt="Linux">
  <img src="https://img.shields.io/badge/CMake-Build-064F8C?style=for-the-badge&logo=cmake&logoColor=white" alt="CMake">
  <img src="https://img.shields.io/badge/Python-Flask%20Service-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
</p>

<img align="right" alt="Coding" width="400" src ="https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExem5kbG00d3A5N21tMXpwOW5rMmtzcXo5ZmRkOThtbzZtbGQ5NDl2aiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/YAlhwn67KT76E/giphy.gif">

A system-level C++17 service for orchestrating large file downloads on Linux. It uses POSIX APIs, atomic filesystem operations, and a zero-merge multithreaded design to maximize disk and network throughput.

The service is designed to run behind a web frontend (e.g., Flask). The two sides are fully decoupled and communicate only through a folder-based pipeline using atomic file moves, which eliminates race conditions.

## Table of Contents

- [Key Features](#key-features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Getting Started](#getting-started)
- [Testing the Pipeline](#testing-the-pipeline)
- [API & Function Reference](#api--function-reference)

---

## Key Features

| Feature | Description |
| --- | --- |
| **Event-driven intake** | Uses `inotify` instead of polling to detect new tasks instantly. |
| **Atomic handoff** | Task files are consumed only on `IN_MOVED_TO`, so a half-written JSON is never read. |
| **Deduplication** | A thread-safe in-memory cache skips previously downloaded URLs, with size limits / LRU eviction to bound RAM usage. |
| **Disk pre-allocation** | `fallocate()` reserves space up front to reduce fragmentation, with a fallback for filesystems that do not support it. |
| **Parallel range downloads** | Files are split into byte ranges and fetched by `N` threads via `libcurl`. |
| **Zero-merge writes** | Each thread writes directly to its offset using `pwrite()`; no temporary chunks to merge. |
| **Safe fallback** | If the server does not support byte ranges, the download automatically uses a single thread. |
| **Failure handling** | Exception handling and cleanup of incomplete files in `./tmp` on network interruptions. |

---

## Architecture

### Folder Pipeline

The system behaves like a state machine, where each folder represents a stage:

| Folder | Purpose |
| --- | --- |
| `./new` | **Intake.** The web server atomically moves `.json` task files here. |
| `./tmp` | **Staging.** Files are pre-allocated and downloaded concurrently here. |
| `./per` | **Permanent storage.** Completed downloads are moved here. |
| `./cmp` | **Archive.** Completed `.json` task files are moved here for logging. |

### Processing Flow

1. **Handoff.** The web API receives a request, writes a JSON file containing the URLs to a temporary location, and moves it into `./new/` with an atomic `rename()`.
2. **Detection.** The `inotify` monitor receives the `IN_MOVED_TO` event, which guarantees the file is fully written.
3. **Deduplication.** Each URL is hashed and checked against the thread-safe cache. Previously downloaded URLs are skipped.
4. **Pre-allocation.** The engine issues an HTTP `HEAD` request to determine the file size, then reserves disk space with `fallocate()`. The return value is checked, and a fallback is used if the filesystem does not support the call.
5. **Parallel download.** The engine checks for `Accept-Ranges: bytes`. If supported, the file is divided among `N` threads, each requesting its own range through `libcurl`. Otherwise, a single thread is used to avoid corruption.
6. **Direct-to-disk writes.** As data arrives, each thread calls `pwrite()` at its assigned offset in the pre-allocated file. This is lock-free and requires no merge step.
7. **Finalization.** After all threads join, the completed file is atomically moved to `./per`, and the task JSON is moved to `./cmp`.

---

## Technology Stack

- **Platform:** Ubuntu Linux (POSIX-compliant)
- **Language:** C++17 (OOP, `std::thread`, `std::filesystem`)
- **Build system:** CMake
- **Libraries:** libcurl, libuuid, nlohmann/json

---

## Getting Started

### Prerequisites

```bash
sudo apt update
sudo apt install -y g++ cmake make libcurl4-openssl-dev uuid-dev nlohmann-json3-dev
```

### Build

```bash
git clone https://github.com/dgeniust/BOSCH_downloader_cplus2.git
cd BOSCH_downloader_cplus2

mkdir build && cd build
cmake ..
make
```

### Run

No root privileges are required.

```bash
./download_service
```

Expected output:

```
Monitor started on: ./new
```

---

## Testing the Pipeline

Keep the service running in one terminal and use a second terminal to simulate the web frontend.

**1. Create a task file** containing a test URL (a 10 MB sample file):

```bash
echo '{"urls": ["https://proof.ovh.net/files/10Mb.dat"]}' > dummy.json
```

**2. Submit the task** using `mv`:

```bash
mv dummy.json ./new/dummy.json
```

> **Important:** Use `mv`, not `cp`. A move is an atomic rename and triggers `IN_MOVED_TO`; a copy can expose a partially written file.

**3. Observe the service log.** The first terminal should show the task being detected, space being allocated, and download threads starting.

**4. Verify the results:**

```bash
# Completed download
ls -lh ./per/

# Archived task file
cat ./cmp/dummy.json
```

---

## API & Function Reference

### Filesystem & I/O

| Function | Purpose |
| --- | --- |
| `inotify_init()`, `inotify_add_watch()` | Monitor filesystem events without polling. |
| `IN_MOVED_TO` | Inotify mask that prevents reading half-written files. |
| `open()`, `close()` | Low-level POSIX file descriptors. |
| `fallocate()` | Reserve disk blocks for a file without writing zeros. |
| `pwrite()` | Write at a specific offset. Thread-safe because it does not use a shared file pointer. |
| `std::filesystem::rename()` | Atomic move at the OS level. |

### Networking

| Function | Purpose |
| --- | --- |
| `curl_easy_setopt(..., CURLOPT_NOBODY, 1L)` | Perform an HTTP `HEAD` request to obtain the file size. |
| `curl_easy_setopt(..., CURLOPT_RANGE, "x-y")` | Request a specific byte range. |
| `curl_easy_setopt(..., CURLOPT_WRITEFUNCTION)` | Custom callback to intercept the incoming byte stream. |

### Concurrency & Memory

| Function | Purpose |
| --- | --- |
| `pthread_create()` | POSIX thread creation. |
| `void*` and `static` | Bridge C++ class instances (singletons) to the C-style function pointers required by `pthread` and `libcurl` callbacks. |
| `std::thread`, `detach()`, `join()` | Standard C++ threading. |
| `std::mutex`, `std::lock_guard` | Guard access to the deduplication cache. |

### Utilities

| Function / Library | Purpose |
| --- | --- |
| `uuid_generate()` | Generate unique identifiers to prevent filename collisions. |
| `nlohmann/json` | JSON parsing. |
