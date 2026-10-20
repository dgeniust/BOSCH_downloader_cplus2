#include "monitor.hpp"
#include "task_processor.hpp"
#include <sys/inotify.h>
#include <pthread.h>
#include <unistd.h>
#include <iostream>
#include <thread>

#define EVENT_SIZE ( sizeof (struct inotify_event) )
#define EVENT_BUF_LEN ( 1024 * ( EVENT_SIZE + 16 ) )

Monitor::Monitor() : fd(-1), wd(-1), monitorThread(0) {}

Monitor::~Monitor() {
    if(fd >= 0 && wd >= 0) {
        inotify_rm_watch(fd, wd); // Xóa theo dõi
        close(fd);
    }
    if(monitorThread != 0){
        pthread_cancel(monitorThread);
        pthread_join(monitorThread, nullptr);
    }
}

Monitor& Monitor::getInstance() {
    static Monitor instance;
    return instance;
}

void* Monitor::monitorLoop (void* arg) {
    Monitor* self = static_cast<Monitor*>(arg);
    char buffer[EVENT_BUF_LEN];

    while(true) {
        int length = read(self->fd, buffer, EVENT_BUF_LEN); // Đọc event
        if(length < 0) break;

        int i = 0;
        while(i < length) {
            struct inotify_event* event = (struct inotify_event*)&buffer[i];
            if(event->len && (event->mask & IN_MOVED_TO)) { // Check IN_MOVED_TO
                std::string filename = event->name;

                if(filename.length() > 5 && filename.substr(filename.length() - 5) == ".json") {
                    std::string full_path = "./new/" + filename;
                    
                    // Tạo thread độc lập để xử lý
                    std::thread(TaskProcessor::processTask, full_path).detach(); // Gọi TaskProcessor
                }
            }
            i += EVENT_SIZE + event->len;
        }
    }
    return nullptr;
}

void Monitor::start(const std::string& watch_dir) {
    fd = inotify_init();
    if(fd < 0) {
        perror("inotify_init");
        return;
    }

    wd = inotify_add_watch(fd, watch_dir.c_str(), IN_MOVED_TO); // Bắt đầu theo dõi
    
    // pthread_t threadId;
    pthread_create(&monitorThread, nullptr, &Monitor::monitorLoop, this);
    std::cout << "Monitor started on: " << watch_dir << "\n";
}