#include "task_processor.hpp"
#include "downloader.hpp"
#include "thread_safe.hpp"
#include <nlohmann/json.hpp>
#include <fstream>
#include <filesystem>
#include <iostream>

using json = nlohmann::json;
namespace fs = std::filesystem;

void TaskProcessor::processTask(const std::string& json_filepath){
    std::error_code ec;
    fs::create_directories("./tmp", ec);
    fs::create_directories("./per", ec);
    fs::create_directories("./cmp", ec);

    std::ifstream file(json_filepath);
    if(!file.is_open()) return;

    json payload;
    try{
        file >> payload;
    } catch (...){
        return;
    }
    file.close();

    auto& cache = DeduplicationCache::getInstance();

    if(payload.contains("urls") && payload["urls"].is_array()){
        for(const auto& url_element : payload["urls"]){
            std::string url = url_element.get<std::string>();

            if(cache.isDownloaded(url)){
                std::cout<<"Skipping dupplicate" << url << "\n";
                continue;
            }

            std::string file_uuid = generateUUID();
            std::string tmp_path = "./tmp/" + file_uuid + ".download";
            std::string final_path = "./per/" + file_uuid + ".file";

            std::cout << "Starting download" << url << "\n";

            if(Downloader::downloadFile(url, tmp_path)){
                fs::rename(tmp_path, final_path);
                cache.markDownloaded(url);
                std::cout << "Completed: " << final_path << "\n";
            }
        }
    }

    fs::path p(json_filepath);
    std::string cmp_path = "./cmp/" + p.filename().string();
    fs::rename(json_filepath, cmp_path);
}

