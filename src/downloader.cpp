#include "downloader.hpp"
#include <fcntl.h>
#include <curl/curl.h>
#include <unistd.h>
#include <thread>
#include <vector>

struct ChunkData {
    int file_descriptor;
    off_t current_offset;
};

double Downloader::getFileSize(const std::string& url){
    CURL* curl = curl_easy_init();
    curl_off_t file_size = -1.0;
    if(curl){
        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_NOBODY, 1L);
        if(curl_easy_perform(curl) == CURLE_OK){
            curl_easy_getinfo(curl, CURLINFO_CONTENT_LENGTH_DOWNLOAD_T, &file_size);
        }
        curl_easy_cleanup(curl);
    }
    return static_cast<double>(file_size);
}

size_t Downloader::writeCallback(void* contents, size_t size, size_t nmemb, void* userdata){
    size_t real_size = size * nmemb;
    ChunkData* chunk = static_cast<ChunkData*>(userdata);

    ssize_t written = pwrite(chunk->file_descriptor, contents, real_size, chunk->current_offset);

    if(written > 0){
        chunk->current_offset += written;
    }
    return real_size;
}

void Downloader::downloadChunk(const std::string& url, int fd, off_t start, off_t end){
    CURL* curl = curl_easy_init();
    if(curl){
        ChunkData chunkInfo = {fd, start};
        std::string range = std::to_string(start) + "-" + std::to_string(end);

        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writeCallback);
        curl_easy_setopt(curl, CURLOPT_RANGE, range.c_str());
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &chunkInfo);

        curl_easy_perform(curl);
        curl_easy_cleanup(curl);
    }
}

bool Downloader::downloadFile(const std::string& url, const std::string& output_path, int num_threads){
    double file_size = getFileSize(url);
    if(file_size <=0) return false;

    int fd = open(output_path.c_str(), O_CREAT | O_WRONLY, 0666);
    if(fd < 0) return false;

    if(fallocate(fd, 0, 0, (off_t)file_size) != 0){
        close(fd);
        return false;
    }

    off_t chunk_size = (off_t)file_size / num_threads;
    std::vector<std::thread> threads;

    for(int i = 0; i < num_threads; ++i){
        off_t start = i * chunk_size;
        off_t end = (i==num_threads - 1) ? (off_t)file_size - 1 : (start + chunk_size -1); 
        threads.emplace_back(downloadChunk, url, fd, start, end);
    }

    for(auto& t : threads) {
        if(t.joinable()) t.join();
    }

    close(fd);
    return true;
}