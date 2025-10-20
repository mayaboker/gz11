#include <zmq.hpp>
#include <opencv2/opencv.hpp>
#include <iostream>
#include <thread>
#include <cstring>

int main() {
    zmq::context_t context(1);
    zmq::socket_t publisher(context, zmq::socket_type::pub);
    publisher.bind("tcp://*:5555");

    // cv::VideoCapture cap(0);
    // if (!cap.isOpened()) {
    //     std::cerr << "Error: Cannot open camera\n";
    //     return -1;
    // }

    std::cout << "Publisher started on tcp://*:5555\n";
    int frame_id = 0;
    
    while (true) {
        // cv::Mat frame;
        // cap >> frame;
        // if (frame.empty()) continue;
        int rows = 480;
        int cols = 640;
        cv::Mat img(rows, cols, CV_8UC3);

        // Fill with gradient pattern
        for (int r = 0; r < rows; ++r) {
            for (int c = 0; c < cols; ++c) {
                img.at<cv::Vec3b>(r, c) = cv::Vec3b(
                    (uchar)((r + frame_id) % 255),
                    (uchar)((c + frame_id * 2) % 255),
                    (uchar)((r + c + frame_id * 3) % 255)
                );
            }
        }
        // --- Metadata ---
        // int rows = img.rows;
        // int cols = img.cols;
        int type = img.type();
        size_t data_size = img.total() * img.elemSize();

        // Send metadata first
        zmq::message_t meta_msg(sizeof(int) * 3);
        std::memcpy(meta_msg.data(), &rows, sizeof(int));
        std::memcpy((char*)meta_msg.data() + sizeof(int), &cols, sizeof(int));
        std::memcpy((char*)meta_msg.data() + 2 * sizeof(int), &type, sizeof(int));
        publisher.send(meta_msg, zmq::send_flags::sndmore);

        // Send image buffer as second part
        zmq::message_t img_msg(data_size);
        std::memcpy(img_msg.data(), img.data, data_size);
        publisher.send(img_msg, zmq::send_flags::none);

        std::cout << "Sent frame: " << rows << "x" << cols << std::endl;
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }

    return 0;
}
