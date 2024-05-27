import cv2
from ultralytics import YOLO
import os
from firebase_admin import storage
import os
import shutil
classes = {0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 4: 'airplane', 5: 'bus', 6: 'train', 7: 'truck', 8: 'boat', 9: 'traffic light', 10: 'fire hydrant', 11: 'stop sign', 12: 'parking meter', 13: 'bench', 14: 'bird', 15: 'cat', 16: 'dog', 17: 'horse', 18: 'sheep', 19: 'cow', 20: 'elephant', 21: 'bear', 22: 'zebra', 23: 'giraffe', 24: 'backpack', 25: 'umbrella', 26: 'handbag', 27: 'tie', 28: 'suitcase', 29: 'frisbee', 30: 'skis', 31: 'snowboard', 32: 'sports ball', 33: 'kite', 34: 'baseball bat', 35: 'baseball glove', 36: 'skateboard', 37: 'surfboard', 38: 'tennis racket',
           39: 'bottle', 40: 'wine glass', 41: 'cup', 42: 'fork', 43: 'knife', 44: 'spoon', 45: 'bowl', 46: 'banana', 47: 'apple', 48: 'sandwich', 49: 'orange', 50: 'broccoli', 51: 'carrot', 52: 'hot dog', 53: 'pizza', 54: 'donut', 55: 'cake', 56: 'chair', 57: 'couch', 58: 'potted plant', 59: 'bed', 60: 'dining table', 61: 'toilet', 62: 'tv', 63: 'laptop', 64: 'mouse', 65: 'remote', 66: 'keyboard', 67: 'cell phone', 68: 'microwave', 69: 'oven', 70: 'toaster', 71: 'sink', 72: 'refrigerator', 73: 'book', 74: 'clock', 75: 'vase', 76: 'scissors', 77: 'teddy bear', 78: 'hair drier', 79: 'toothbrush'}

os.environ["XDG_SESSION_TYPE"] = "xcb"
model = YOLO("yolov9c.pt")


def predict(chosen_model, img, classes=[], conf=0.5):
    if classes:
        results = chosen_model.predict(img, classes=classes, conf=conf)
    else:
        results = chosen_model.predict(img, conf=conf)

    return results


def predict_and_detect(chosen_model, img, classes=[], conf=0.5, rectangle_thickness=2, text_thickness=1):
    results = predict(chosen_model, img, classes, conf=conf)
    for result in results:
        for box in result.boxes:
            cv2.rectangle(img, (int(box.xyxy[0][0]), int(box.xyxy[0][1])),
                          (int(box.xyxy[0][2]), int(box.xyxy[0][3])), (255, 0, 0), rectangle_thickness)
            cv2.putText(img, f"{result.names[int(box.cls[0])]}",
                        (int(box.xyxy[0][0]), int(box.xyxy[0][1]) - 10),
                        cv2.FONT_HERSHEY_PLAIN, 1, (255, 0, 0), text_thickness)
    return img, results


def find_deviations(inspectionId, db, firebase):
    frameCounter = 0
    lastResultsFrame = 0
    crop_percent = 0.2
    skipCount = 30
    deviationState = []
    bucket = storage.bucket("drone-control-db.appspot.com", firebase)
    video_path = r"missions/{0}.MP4".format(inspectionId)
    print("PATH:")
    print(video_path)
    video_blob = bucket.blob(video_path)
    tmp_save = r"./{0}.MP4".format(inspectionId)
    video_blob.download_to_filename(tmp_save)
    cap = cv2.VideoCapture(tmp_save)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    print(f"Got the video with fps: {fps}")
    while True:
        success, img = cap.read()
        if (frameCounter % skipCount != 0):
            frameCounter += 1
            print(f"skipping frame {frameCounter}")
            continue
        if frameCounter == 0 and not success:
            print("Could not read video from firebase, wrong id")
            return False
        if not success:
            print("Loop finished")
            break
        img_width = img.shape[1]
        crop_amount = int(crop_percent*img_width)
        cropped_img = img[:, crop_amount:img_width-crop_amount]
        result_img, results = predict_and_detect(model, cropped_img, classes=[
                                                 1, 10, 11, 12, 13, 24, 25, 26, 28, 30, 32, 36, 56, 57, 58, 59, 60, 71, 72], conf=0.8)
        if (len(results) > 0 and len(results[0].boxes) > 0):
            print("Found single deviation")
            if (int((frameCounter-lastResultsFrame)/fps) > 4):
                lastResultsFrame = frameCounter
                deviationObj = {
                    "inspectionId": inspectionId,
                    "deviationCount": len(deviationState),
                    "isValid": True,
                }
                print("trying to upload deviation .... ")
                update_time, doc_ref = db.collection(
                    "deviation").add(deviationObj)
                for finding in deviationState:
                    print(f"adding finding: {finding}")
                    db.collection("deviation").document(
                        doc_ref.id).collection("findings").add(finding)
                deviationState = []
            singledeviation = []
            for deviations in results[0].boxes:
                singledeviation.append({
                    "name": fr"{results[0].names[int(deviations.cls[0])]}",
                    "conf": deviations.conf.item(),
                })
            deviation_hash = id(singledeviation)
            PATH = f"inspections/{inspectionId}"
            if not os.path.exists(PATH):
                os.makedirs(PATH)
            img_url = r"{0}/{1}{2}.jpg".format(PATH,
                                               deviation_hash, frameCounter)
            deviationState.append({
                "deviations": singledeviation,
                "frame": frameCounter,
                "imgId": img_url,
            })
            print("Saving image")
            write_img = cv2.imwrite(img_url, result_img)
            if (not write_img):
                print("Could not save image")
                break
            print(f"Saved image state: {write_img}")
            print(f"Uploading {img_url} to firebase...")
            blob = bucket.blob(img_url)
            blob.upload_from_filename(img_url)
        frameCounter += 1
    folder = 'inspections'
    print("deleting video")
    os.unlink(tmp_save)
    for filename in os.listdir(folder):
        print("Deleting tmp images")
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))
    return True
