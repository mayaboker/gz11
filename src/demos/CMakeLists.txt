cmake_minimum_required(VERSION 3.10)
project(zmq_pub_sub_example)

find_package(Threads REQUIRED)
find_package(PkgConfig REQUIRED)
find_package(OpenCV REQUIRED)
find_package(Msgpack REQUIRED)

pkg_check_modules(ZMQ REQUIRED libzmq)

add_executable(pub pub.cpp)
add_executable(sub sub.cpp)

target_include_directories(pub PRIVATE ${ZMQ_INCLUDE_DIRS})
target_include_directories(sub PRIVATE ${ZMQ_INCLUDE_DIRS})



target_link_libraries(pub PRIVATE ${ZMQ_LIBRARIES} Threads::Threads)
target_link_libraries(sub PRIVATE ${ZMQ_LIBRARIES} Threads::Threads)


add_executable(pub_img pub_img.cpp)
target_include_directories(pub_img PRIVATE ${ZMQ_INCLUDE_DIRS}  ${OpenCV_INCLUDE_DIRS})
target_link_libraries(pub_img PRIVATE ${ZMQ_LIBRARIES} Threads::Threads ${OpenCV_LIBRARIES})


add_executable(sub_img sub_img.cpp)
target_include_directories(sub_img PRIVATE ${ZMQ_INCLUDE_DIRS}  ${OpenCV_INCLUDE_DIRS})
target_link_libraries(sub_img PRIVATE ${ZMQ_LIBRARIES} Threads::Threads ${OpenCV_LIBRARIES})

add_executable(sub_img_msgpack sub_img_msgpack.cpp)
target_include_directories(sub_img_msgpack PRIVATE ${ZMQ_INCLUDE_DIRS} ${OpenCV_INCLUDE_DIRS} ${MSGPACK_INCLUDE_DIRS})
target_link_libraries(sub_img_msgpack PRIVATE ${ZMQ_LIBRARIES} Threads::Threads ${OpenCV_LIBRARIES})

add_executable(pub_msg pub_msg.cpp)
target_include_directories(pub_msg PRIVATE ${ZMQ_INCLUDE_DIRS}  ${MSGPACK_INCLUDE_DIRS})
target_link_libraries(pub_msg PRIVATE ${ZMQ_LIBRARIES})


add_executable(sub_msg sub_msg.cpp)
target_include_directories(sub_msg PRIVATE ${ZMQ_INCLUDE_DIRS}  ${MSGPACK_INCLUDE_DIRS})
target_link_libraries(sub_msg PRIVATE ${ZMQ_LIBRARIES})