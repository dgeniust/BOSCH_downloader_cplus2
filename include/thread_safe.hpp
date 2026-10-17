#pragma once 
#include <string>
#include <unordered_set>
#include <mutex>

std::string generateUUID();

class DeduplicationCache {
private: 
    std::unordered_set<std::string> downloaded_urls;
    std::mutex mtx;

    DeduplicationCache() = default;
    ~DeduplicationCache() = default;

    DeduplicationCache(const DeduplicationCache&) = delete;
    DeduplicationCache& operator=(const DeduplicationCache&) = delete;

public:
    static DeduplicationCache& getInstance();
    bool isDownloaded(const std::string& url);
    void markDownloaded(const std::string& url);
};