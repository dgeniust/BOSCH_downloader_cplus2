#pragma once
#include <string>
#include <pthread.h>

class Monitor {
private: 
    int fd;
    int wd;
    pthread_t monitorThread;

    Monitor();
    ~Monitor();
    Monitor(const Monitor&) = delete;
    Monitor& operator=(const Monitor&) = delete;

    static void* monitorLoop(void* arg);

public:
    static Monitor& getInstance();
    void start(const std::string& watch_dir);
};