#include "thread_safe.hpp"
#include <uuid/uuid.h>

DeduplicationCache& DeduplicationCache::getInstance(){
    static DeduplicationCache instance;
    return instance;
}
bool DeduplicationCache::isDownloaded(const std::string& url){
    std::lock_guard<std::mutex> lock(mtx);
    return downloaded_urls.find(url) != downloaded_urls.end();
}

void DeduplicationCache::markDownloaded(const std::string& url){
    std::lock_guard<std::mutex> lock(mtx);
    downloaded_urls.insert(url);
}
std::string generateUUID(){
    uuid_t uuid;
    uuid_generate(uuid);
    char uuid_str[37];
    uuid_unparse_lower(uuid, uuid_str);
    return std::string(uuid_str);
}