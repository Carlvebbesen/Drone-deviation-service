from flask import Flask, request
from flask_socketio import SocketIO
import socket
import threading
import struct
import pickle
import cv2
import base64
import json
from firebase_admin import firestore, credentials, initialize_app

from api.object_detection_service import find_detensions

app = Flask(__name__)
sio = SocketIO(app, cors_allowed_origins="*")

# Application Default credentials are automatically created.
cred = credentials.Certificate('./drone-control-db-358c9ef52864.json')
firebase = initialize_app(cred)
db = firestore.client()

#How to add an inspection:
# inspection = {
# "areaName": "E5",

# "buildingAreaId": "/buildingArea/pj5p0BaCEebdNw5zerYC",

# "date": "29 March 2024 at 04:32:06 UTC+1",

# "droneId": "/drones/Zs5h4QJjRRpnEr8e6bk1",

# "errorMsg": "",

# "floorId": 3,

# "floorName": "5",

# "inspectionType": "escaperoute inspection",

# "status": "Success",

# "statusMsg": "Vellykket inspeksjon utført, ingen avvik funnet" }
# update_time, city_ref = db.collection("inspection").add(inspection)

# For ROS2 Nodes Communication
ros2_ports = {
    'manual_control': 5685,  # Port for sending control commands
    'video_feed': 5533       # Port for receiving video feed
}

def send_message(port: int, message: str):
    """Function to send messages to a specific port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ros2_socket:
            ros2_socket.connect(('localhost', port))
            ros2_socket.sendall(message.encode())
            response = ros2_socket.recv(1024).decode()
            print(f"Response: {response}")
            # Emit response back to the client if necessary
    except Exception as e:
        print(f'Error sending message to node at port {port}: {e}')

def listen_for_video_feed(port):
    """Function to listen for incoming video feed on a specific port."""
    def handle_client_connection(client_socket):
        try:
            while True:
                # Receive the size of the pickled image
                raw_msglen = recvall(client_socket, 8)
                if not raw_msglen:
                    break
                msglen = struct.unpack("L", raw_msglen)[0]

                # Receive the actual image data
                data = recvall(client_socket, msglen)
                if not data:
                    break

                # Unpickle the image data
                cv_image = pickle.loads(data)
                
                # Encode the image as JPEG
                _, buffer = cv2.imencode('.jpg', cv_image)
                
                # Convert to base64 encoding and decode to string
                jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                sio.emit('image_data', jpg_as_text)
        finally:
            client_socket.close()

    def recvall(sock, n):
        """Helper function to receive n bytes or return None if EOF is hit."""
        data = b''
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data

    def server_listen():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('localhost', port))
            server_socket.listen()
            print(f"Server listening on port {port}...")
            while True:
                client_socket, addr = server_socket.accept()
                print(f"Accepted connection from {addr}")
                client_thread = threading.Thread(target=handle_client_connection, args=(client_socket,))
                client_thread.start()

    # Start the server listening in a new thread
    threading.Thread(target=server_listen).start()

@sio.event
def connect():
    print('WebApp connected:', request.sid)

@sio.event
def disconnect():
    print('WebApp disconnected:', request.sid)

@sio.on('manual_control')
def handle_manual_control(data):
    print('Manual control event received:', data)
    port = ros2_ports['manual_control']
    threading.Thread(target=send_message, args=(port, data)).start()
    return data + " Done"

@app.route("/generate/detension", methods=["POST"])
def detension_finder():
    inspection = request.json['inspection']
    print("Got it", inspection)
    result =find_detensions(inspectionId=inspection, db=db, firebase=firebase)
    if(not result):
        return json.dumps({'success':False}), 500, {'ContentType':'application/json'}
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 


if __name__ == '__main__':
    #listen_for_video_feed(ros2_ports['video_feed'])  # Start listening for video feed
    sio.run(app, debug=True, use_reloader=False)