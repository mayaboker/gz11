import zmq

# 1️⃣ Create a context
context = zmq.Context()

# 2️⃣ Create a SUB (subscriber) socket
socket = context.socket(zmq.SUB)

# 3️⃣ Connect to the publisher
socket.connect("tcp://localhost:5555")

# 4️⃣ Subscribe to a topic (empty string = all messages)
socket.setsockopt_string(zmq.SUBSCRIBE, "")

# 5️⃣ Receive messages
while True:
    message = socket.recv_string()
    print(f"📩 Received: {message}")