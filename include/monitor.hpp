#pragma once
#include <string>

class Monitor {
private: 
    int fd;
    int wd;

    Monitor();
    ~Monitor();
    Monitor(const Monitor&) = delete;
    Monitor& operator=(const Monitor&) = delete;

    static void* monitorLoop(void* arg);

public:
    static Monitor& getInstance();
    void start(const std::string& watch_dir);
};