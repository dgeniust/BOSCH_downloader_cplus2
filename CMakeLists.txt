cmake_minimum_required(VERSION 3.10)
project(DownloadManager CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

find_package(CURL REQUIRED)
find_package(Threads REQUIRED)

find_package(nlohmann_json REQUIRED)
include_directories(include)

set(SOURCES
    src/main.cpp
    src/downloader.cpp
    src/monitor.cpp
    src/task_processor.cpp
    src/thread_safe.cpp
)

add_executable(download_service ${SOURCES})

target_link_libraries(download_service
    PRIVATE
    CURL::libcurl
    Threads::Threads
    nlohmann_json::nlohmann_json
    uuid
)