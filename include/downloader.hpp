#pragma once
#include <string>
#include <sys/types.h>

class Downloader {
private:
    static double getFileSize(const std::string& url);
    static size_t writeCallback(void* contents, size_t size, size_t nmemb, void* userdata);
    static void downloadChunk(const std::string& url, int fd, off_t start, off_t end);

public:
    static bool downloadFile(const std::string& url, const std::string& output_path, int num_threads = 5);
};