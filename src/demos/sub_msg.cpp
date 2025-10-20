#include <zmq.hpp>
#include <msgpack.hpp>
#include <iostream>
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
    zmq::socket_t subscriber(context, zmq::socket_type::sub);
    subscriber.connect("tcp://localhost:5555");
    subscriber.setsockopt(ZMQ_SUBSCRIBE, "", 0);

    std::cout << "Subscriber connected to tcp://localhost:5555" << std::endl;

    while (true) {
        zmq::message_t msg;
        subscriber.recv(msg, zmq::recv_flags::none);

        // Deserialize using MessagePack
        msgpack::object_handle oh = msgpack::unpack(
            static_cast<const char*>(msg.data()), msg.size());

        msgpack::object obj = oh.get();
        Telemetry telemetry;
        obj.convert(telemetry);

        std::cout << "Received Telemetry → "
                  << "id=" << telemetry.id
                  << ", temp=" << telemetry.temperature
                  << ", volt=" << telemetry.voltage
                  << ", status=" << telemetry.status << std::endl;
    }

    return 0;
}
