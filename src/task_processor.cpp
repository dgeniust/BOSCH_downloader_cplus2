#include <iostream>
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
    try {
        std::error_code ec;
        fs::create_directories("./tmp", ec);
        fs::create_directories("./per", ec);
        fs::create_directories("./cmp", ec);

        std::ifstream file(json_filepath);
        if(!file.is_open()) {
            throw std::runtime_error("Cannot open JSON file");
        }

        json payload;
        try{
            file >> payload;
        } catch (const std::exception& e){
            throw std::runtime_error(std::string("Invalid JSON format: ") + e.what());
        }
        file.close();

        auto& cache = DeduplicationCache::getInstance();

        if(payload.contains("urls") && payload["urls"].is_array()){
            for(const auto& url_element : payload["urls"]){
                std::string url = url_element.get<std::string>();

                if(cache.isDownloaded(url)){
                    std::cout<<"Skipping dupplicate: " << url << "\n";
                    continue;
                }

                std::string file_uuid = generateUUID();
                std::string tmp_path = "./tmp/" + file_uuid + ".download";
                std::string final_path = "./per/" + file_uuid + ".file";

                std::cout << "Starting download: " << url << "\n";

                if(Downloader::downloadFile(url, tmp_path)){
                    fs::rename(tmp_path, final_path);
                    cache.markDownloaded(url);
                    std::cout << "Completed: " << final_path << "\n";
                } else {
                    fs::remove(tmp_path);
                }
            }
        }

        fs::path p(json_filepath);
        std::string cmp_path = "./cmp/" + p.filename().string();
        fs::rename(json_filepath, cmp_path);
    } catch (const std::exception& e){
        std::cerr << "Error processing task [" << json_filepath << "]: " << e.what() << "\n";
        try {
            fs::path p(json_filepath);
            std::string err_path = "./cmp/" + p.filename().string() + ".err";
            fs::rename(json_filepath, err_path);
        } catch (...) {
            std::cerr << "Critical failure: Could not move corrupted JSON file out of ./new \n";
        }
    }
}

