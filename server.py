from flask import Flask, request
from flask_socketio import SocketIO
import json
from firebase_admin import firestore, credentials, initialize_app

from object_detection_service import find_detensions

app = Flask(__name__)
sio = SocketIO(app, cors_allowed_origins="*")

# Application Default credentials are automatically created.
cred = credentials.Certificate('./drone-control-db-358c9ef52864.json')
firebase = initialize_app(cred)
db = firestore.client()


@app.route("/generate/detension", methods=["POST"])
def detension_finder():
    inspection = request.json['inspection']
    print("Got it", inspection)
    result = find_detensions(inspectionId=inspection, db=db, firebase=firebase)
    if (not result):
        return json.dumps({'success': False}), 500, {'ContentType': 'application/json'}
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


if __name__ == '__main__':
    # listen_for_video_feed(ros2_ports['video_feed'])  # Start listening for video feed
    sio.run(app, debug=True, use_reloader=False)
