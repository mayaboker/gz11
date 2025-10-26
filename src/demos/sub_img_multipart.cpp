/*
 * ZMQ Image Subscriber - Multipart Format
 * Receives: (TOPIC, msgpack_data) 
 * Matching Python format: socket.send_multipart((TOPIC, msgpack.packb(frame)))
 */

#include <zmq.hpp>
#include <msgpack.hpp>
#include <opencv2/opencv.hpp>
#include <iostream>
#include <vector>

int main(int argc, char** argv)
{
    std::string zmq_address = "tcp://localhost:5556";
    std::string expected_topic = "camera/image";
    
    // Parse command line arguments
    if (argc > 1) {
        zmq_address = argv[1];
    }
    if (argc > 2) {
        expected_topic = argv[2];
    }
    
    std::cout << "ZMQ Image Subscriber (Multipart Format)\n";
    std::cout << "========================================\n";
    std::cout << "Connecting to: " << zmq_address << "\n";
    std::cout << "Expected topic: " << expected_topic << "\n\n";
    
    // Setup ZMQ subscriber
    zmq::context_t context(1);
    zmq::socket_t subscriber(context, zmq::socket_type::sub);
    subscriber.connect(zmq_address);
    
    // Subscribe to all topics (empty string means all)
    subscriber.set(zmq::sockopt::subscribe, "");
    
    std::cout << "Waiting for images...\n";
    std::cout << "Press ESC in the image window to exit\n\n";
    
    int frame_count = 0;
    
    // Image dimensions (from Gazebo camera)
    const int HEIGHT = 480;
    const int WIDTH = 640;
    const int CHANNELS = 3;
    const int EXPECTED_SIZE = HEIGHT * WIDTH * CHANNELS;
    
    while (true) {
        try {
            // Receive multipart message: (TOPIC, data)
            zmq::message_t topic_msg;
            zmq::message_t data_msg;
            
            // Receive topic (first part)
            auto result = subscriber.recv(topic_msg, zmq::recv_flags::none);
            if (!result) {
                std::cerr << "Failed to receive topic\n";
                continue;
            }
            
            // Check if there's more
            int more = subscriber.get(zmq::sockopt::rcvmore);
            if (!more) {
                std::cerr << "Expected multipart message, but got single part\n";
                continue;
            }
            
            // Receive data (second part)
            result = subscriber.recv(data_msg, zmq::recv_flags::none);
            if (!result) {
                std::cerr << "Failed to receive data\n";
                continue;
            }
            
            // Extract topic string
            std::string received_topic(static_cast<char*>(topic_msg.data()), topic_msg.size());
            std::cout << "Received from topic: " << received_topic;
            
            if (received_topic != expected_topic) {
                std::cout << " (Warning: Expected '" << expected_topic << "')";
            }
            std::cout << "\n";
            
            // Unpack msgpack data
            msgpack::object_handle oh = msgpack::unpack(
                static_cast<const char*>(data_msg.data()), 
                data_msg.size()
            );
            
            msgpack::object obj = oh.get();
            
            // Convert to vector
            std::vector<unsigned char> frame_bytes;
            obj.convert(frame_bytes);
            
            std::cout << "Frame bytes length: " << frame_bytes.size() << "\n";
            
            // Check size
            if (frame_bytes.size() != EXPECTED_SIZE) {
                std::cerr << "Error: Unexpected frame size. Got " << frame_bytes.size() 
                         << ", expected " << EXPECTED_SIZE << "\n";
                std::cerr << "Cannot reshape and display\n";
                std::cout << "-------------------------------------------\n";
                continue;
            }
            
            // Create OpenCV Mat from bytes
            // Reshape to (HEIGHT, WIDTH, CHANNELS)
            cv::Mat frame(HEIGHT, WIDTH, CV_8UC3, frame_bytes.data());
            
            // Make a copy since frame_bytes will be destroyed
            cv::Mat frame_copy = frame.clone();
            
            std::cout << "Reshaped to: " << frame_copy.rows << "x" << frame_copy.cols 
                     << " channels: " << frame_copy.channels() << "\n";
            
            // Display the frame
            cv::imshow("Camera Feed (Multipart Format)", frame_copy);
            
            frame_count++;
            std::cout << "✓ Frame #" << frame_count << " received and displayed\n";
            std::cout << "-------------------------------------------\n";
            
            // Wait 1ms for key press
            int key = cv::waitKey(1);
            if (key == 27) { // ESC key
                std::cout << "\nExiting...\n";
                break;
            }
            
        } catch (const msgpack::unpack_error& e) {
            std::cerr << "MsgPack unpack error: " << e.what() << "\n";
        } catch (const msgpack::type_error& e) {
            std::cerr << "MsgPack type error: " << e.what() << "\n";
        } catch (const std::exception& e) {
            std::cerr << "Error: " << e.what() << "\n";
        }
    }
    
    std::cout << "\nTotal frames received: " << frame_count << "\n";
    cv::destroyAllWindows();
    subscriber.close();
    context.close();
    
    return 0;
}

