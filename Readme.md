# Deviation Detection Service

This repository contains a Flask API service designed to detect deviations in hallway videos using a YOLO model for object detection. Detected deviations are uploaded to Firebase storage and logged in a Firestore database.

## Features

- Object Detection: Utilizes YOLO for detecting predefined classes in video frames.
- Firebase Integration: Downloads videos from Firebase, processes them, and uploads detected frames back to Firebase storage.
- Deviations: Detected deviations is uploaded to firestore

## Setup

### Prerequisites

- Python 3.x
- Firebase Admin SDK
- GCP account for firebase
- OpenCV
- YOLO model weights (yolov9c.pt)

### Installation

1. Clone the repository:
   `git clone Drone-deviation-service`
2. Install the prerequisite
3. Start the flask server: `python3 server.py`

### Notes
- Ensure that your YOLO model weights (yolov9c.pt) are placed in the appropriate directory.
- Modify the class list in the predict_and_detect function as needed to suit your application.
