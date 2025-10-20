
find_package(gazebo REQUIRED)
find_package(TBB REQUIRED)

include_directories(${GAZEBO_INCLUDE_DIRS})
link_directories(${GAZEBO_LIBRARY_DIRS})
list(APPEND CMAKE_CXX_FLAGS "${GAZEBO_CXX_FLAGS}")

add_executable(listener listener.cpp)
target_link_libraries(listener ${GAZEBO_LIBRARIES} TBB::tbb)

add_executable(gps2zmq gps2zmq.cpp)
target_link_libraries(gps2zmq ${GAZEBO_LIBRARIES} TBB::tbb)


add_subdirectory(demos)