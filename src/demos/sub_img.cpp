#include <zmq.hpp>
#include <opencv2/opencv.hpp>
#include <iostream>
#include <cstring>

int main() {
    zmq::context_t context(1);
    zmq::socket_t subscriber(context, zmq::socket_type::sub);
    subscriber.connect("tcp://localhost:5556");
    subscriber.setsockopt(ZMQ_SUBSCRIBE, "", 0);

    std::cout << "Subscriber listening on tcp://localhost:5556\n";

    while (true) {
        zmq::message_t meta_msg;
        zmq::message_t img_msg;

        // Receive metadata + image buffer
        subscriber.recv(meta_msg, zmq::recv_flags::none);
        subscriber.recv(img_msg, zmq::recv_flags::none);

        int rows, cols, type;
        std::memcpy(&rows, meta_msg.data(), sizeof(int));
        std::memcpy(&cols, (char*)meta_msg.data() + sizeof(int), sizeof(int));
        std::memcpy(&type, (char*)meta_msg.data() + 2 * sizeof(int), sizeof(int));

        cv::Mat img(rows, cols, type, img_msg.data());
        cv::imshow("Received", img);
        if (cv::waitKey(1) == 27) break; // ESC to exit
    }

    return 0;
}
