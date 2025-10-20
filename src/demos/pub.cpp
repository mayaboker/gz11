#include <zmq.hpp>
#include <string>
#include <iostream>
#include <thread>
#include <chrono>

int main() {
    zmq::context_t context(1); // 1 I/O thread
    zmq::socket_t publisher(context, zmq::socket_type::pub);

    // Bind to TCP address
    publisher.bind("tcp://*:5555");

    std::cout << "Publisher started on tcp://*:5555" << std::endl;

    int counter = 0;
    while (true) {
        std::string message = "Hello " + std::to_string(counter++);
        zmq::message_t msg(message.begin(), message.end());

        publisher.send(msg, zmq::send_flags::none);
        std::cout << "Sent: " << message << std::endl;

        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    return 0;
}
