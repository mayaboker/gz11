import zmq
import msgpack

# 1️⃣ Set up ZMQ subscriber
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:5555")

# Subscribe to all messages
socket.setsockopt_string(zmq.SUBSCRIBE, "")

print("✅ Waiting for msgpack messages...")

# 2️⃣ Receive and decode
while True:
    packed = socket.recv()
    data = msgpack.unpackb(packed, raw=False)
    print(f"📡 Received: {data}")
