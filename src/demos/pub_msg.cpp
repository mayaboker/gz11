#include <zmq.hpp>
#include <msgpack.hpp>
#include <iostream>
#include <thread>
#include <vector>
#include <string>

struct Telemetry {
    int id;
    double temperature;
    double voltage;
    std::string status;

    MSGPACK_DEFINE(id, temperature, voltage, status);
};

int main() {
    zmq::context_t context(1);
    zmq::socket_t publisher(context, zmq::socket_type::pub);
    publisher.bind("tcp://*:5555");

    std::cout << "Publisher started on tcp://*:5555" << std::endl;

    int count = 0;
    while (true) {
        Telemetry msg{count++, 22.5 + (rand() % 100) / 10.0, 3.7, "OK"};

        // Serialize using MessagePack
        msgpack::sbuffer buffer;
        msgpack::pack(buffer, msg);

        // Send via ZeroMQ
        zmq::message_t zmq_msg(buffer.size());
        std::memcpy(zmq_msg.data(), buffer.data(), buffer.size());
        publisher.send(zmq_msg, zmq::send_flags::none);

        std::cout << "Sent telemetry: id=" << msg.id
                  << ", temp=" << msg.temperature
                  << ", volt=" << msg.voltage << std::endl;

        std::this_thread::sleep_for(std::chrono::milliseconds(500));
    }

    return 0;
}
