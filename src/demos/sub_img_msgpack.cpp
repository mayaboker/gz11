#include <zmq.hpp>
#include <opencv2/opencv.hpp>
#include <msgpack.hpp>
#include <iostream>
#include <cstring>
#include <map>
#include <vector>

int main() {
    zmq::context_t context(1);
    zmq::socket_t subscriber(context, zmq::socket_type::sub);
    subscriber.connect("tcp://localhost:5556");
    subscriber.setsockopt(ZMQ_SUBSCRIBE, "", 0);

    std::cout << "MsgPack Image Subscriber listening on tcp://localhost:5556\n";

    while (true) {
        zmq::message_t msg;

        // Receive msgpack message
        subscriber.recv(msg, zmq::recv_flags::none);
        
        // Unpack msgpack
        msgpack::object_handle oh = msgpack::unpack(
            static_cast<const char*>(msg.data()), msg.size());
        msgpack::object obj = oh.get();
        
        // Convert to map
        std::map<std::string, msgpack::object> data;
        obj.convert(data);
        
        // Extract fields
        std::string topic;
        int rows, cols, type;
        std::vector<unsigned char> img_data;
        
        data["topic"].convert(topic);
        data["rows"].convert(rows);
        data["cols"].convert(cols);
        data["type"].convert(type);
        data["data"].convert(img_data);
        
        std::cout << "Received: " << rows << "x" << cols 
                  << " topic: " << topic << std::endl;
        
        // Create OpenCV Mat from data
        cv::Mat img(rows, cols, type, img_data.data());
        
        // Clone to ensure data persistence
        cv::Mat display_img = img.clone();
        
        cv::imshow("Received (MsgPack)", display_img);
        if (cv::waitKey(1) == 27) break; // ESC to exit
    }

    return 0;
}

