/*
 * Gazebo Camera to ZMQ Publisher
 * Subscribes to Gazebo camera image topic and publishes via ZMQ
 */

#include <gazebo/transport/transport.hh>
#include <gazebo/msgs/msgs.hh>
#include <gazebo/gazebo_client.hh>
#include <zmq.hpp>
#include <opencv2/opencv.hpp>
#include <iostream>
#include <cstring>

// Global ZMQ publisher
zmq::context_t g_context(1);
zmq::socket_t g_publisher(g_context, zmq::socket_type::pub);

/////////////////////////////////////////////////
// Callback function called when image is received
void onImageMsg(ConstImageStampedPtr &_msg)
{
    // Extract image data from Gazebo message
    int width = _msg->image().width();
    int height = _msg->image().height();
    int pixel_format = _msg->image().pixel_format();
    
    std::cout << "Received image: " << width << "x" << height 
              << " format: " << pixel_format << std::endl;
    
    // Convert Gazebo image to OpenCV Mat
    cv::Mat img;
    
    // Gazebo pixel formats: L_INT8 = 1, BGR_INT8 = 3, RGB_INT8 = 4
    if (pixel_format == 3) // BGR_INT8 (most common in Gazebo)
    {
        // BGR 8-bit format - already in OpenCV format!
        img = cv::Mat(height, width, CV_8UC3);
        const char* data = _msg->image().data().c_str();
        std::memcpy(img.data, data, height * width * 3);
    }
    else if (pixel_format == 4) // RGB_INT8
    {
        // RGB 8-bit format
        img = cv::Mat(height, width, CV_8UC3);
        const char* data = _msg->image().data().c_str();
        std::memcpy(img.data, data, height * width * 3);
        
        // Convert RGB to BGR for OpenCV
        cv::cvtColor(img, img, cv::COLOR_RGB2BGR);
    }
    else if (pixel_format == 1) // L_INT8 (grayscale)
    {
        // Grayscale 8-bit format
        img = cv::Mat(height, width, CV_8UC1);
        const char* data = _msg->image().data().c_str();
        std::memcpy(img.data, data, height * width);
    }
    else
    {
        std::cerr << "Unsupported pixel format: " << pixel_format << std::endl;
        std::cerr << "Known formats: 1=L_INT8, 3=BGR_INT8, 4=RGB_INT8" << std::endl;
        return;
    }
    
    // Publish via ZMQ (same protocol as pub_img.cpp)
    int rows = img.rows;
    int cols = img.cols;
    int type = img.type();
    size_t data_size = img.total() * img.elemSize();
    
    // Send metadata first
    zmq::message_t meta_msg(sizeof(int) * 3);
    std::memcpy(meta_msg.data(), &rows, sizeof(int));
    std::memcpy((char*)meta_msg.data() + sizeof(int), &cols, sizeof(int));
    std::memcpy((char*)meta_msg.data() + 2 * sizeof(int), &type, sizeof(int));
    g_publisher.send(meta_msg, zmq::send_flags::sndmore);
    
    // Send image buffer as second part
    zmq::message_t img_msg(data_size);
    std::memcpy(img_msg.data(), img.data, data_size);
    g_publisher.send(img_msg, zmq::send_flags::none);
    
    std::cout << "Published frame via ZMQ: " << rows << "x" << cols << std::endl;
}

/////////////////////////////////////////////////
int main(int _argc, char **_argv)
{
    std::string camera_topic = "/gazebo/default/iris_demo/iris_demo/gimbal_small_2d/tilt_link/camera/image";
    std::string zmq_address = "tcp://*:5556";
    
    // Parse command line arguments
    if (_argc > 1) {
        camera_topic = _argv[1];
    }
    if (_argc > 2) {
        zmq_address = _argv[2];
    }
    
    std::cout << "Camera2ZMQ Publisher\n";
    std::cout << "===================\n";
    std::cout << "Gazebo topic: " << camera_topic << "\n";
    std::cout << "ZMQ address: " << zmq_address << "\n\n";
    
    // Setup ZMQ publisher
    g_publisher.bind(zmq_address);
    std::cout << "ZMQ publisher bound to " << zmq_address << "\n";
    
    // Load Gazebo client
    gazebo::client::setup(_argc, _argv);
    
    // Create Gazebo transport node
    gazebo::transport::NodePtr node(new gazebo::transport::Node());
    node->Init();
    
    // Subscribe to camera topic
    gazebo::transport::SubscriberPtr sub = 
        node->Subscribe(camera_topic, onImageMsg);
    
    std::cout << "Subscribed to Gazebo camera topic\n";
    std::cout << "Waiting for images...\n\n";
    
    // Main loop
    while (true)
        gazebo::common::Time::MSleep(10);
    
    // Cleanup
    gazebo::client::shutdown();
    return 0;
}

