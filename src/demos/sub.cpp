#include <zmq.hpp>
#include <string>
#include <iostream>

int main() {
    zmq::context_t context(1);
    zmq::socket_t subscriber(context, zmq::socket_type::sub);

    // Connect to the publisher
    subscriber.connect("tcp://localhost:5555");

    // Subscribe to all messages ("")
    subscriber.setsockopt(ZMQ_SUBSCRIBE, "", 0);

    std::cout << "Subscriber connected to tcp://localhost:5555" << std::endl;

    while (true) {
        zmq::message_t msg;
        subscriber.recv(msg, zmq::recv_flags::none);
        std::string received(static_cast<char*>(msg.data()), msg.size());
        std::cout << "Received: " << received << std::endl;
    }

    return 0;
}
