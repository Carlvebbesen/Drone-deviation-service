from flask import Flask, request
import json
from firebase_admin import firestore, credentials, initialize_app

from object_detection_service import find_deviations

app = Flask(__name__)

# Application Default credentials are automatically created.
cred = credentials.Certificate('./drone-control-db-firebase-adminsdk-olkbr-d783616bac.json')
firebase = initialize_app(cred)
db = firestore.client()


@app.route("/generate/deviation", methods=["POST"])
def deviation_finder():
    inspection = request.json['inspection']
    print("Got it", inspection)
    result =find_deviations(inspectionId=inspection, db=db, firebase=firebase)
    if(not result):
        return json.dumps({'success':False}), 500, {'ContentType':'application/json'}
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}