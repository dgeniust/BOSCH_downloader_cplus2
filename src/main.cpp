#include "monitor.hpp"
#include <filesystem>
#include <curl/curl.h>
#include <thread>
#include <chrono>

namespace fs = std::filesystem;

int main() {
    fs::create_directories("new");
    fs::create_directories("tmp");
    fs::create_directories("per");
    fs::create_directories("cmp");

    curl_global_init(CURL_GLOBAL_ALL);

    Monitor::getInstance().start("new");

    while(true){
        std::this_thread::sleep_for(std::chrono::hours(1));
    }

    curl_global_cleanup();
    return 0;
}