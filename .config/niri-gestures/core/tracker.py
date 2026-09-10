import math
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class VisionTracker:
    def __init__(self, hand_model_path: str, face_model_path: str, mode: str = "head_eye", camera_index: int = 0, target_fps: int = 25):
        self.mode = mode # "head_eye", "hand", or "both"
        self.camera_index = camera_index
        self.target_fps = target_fps
        self.cap = None

        self.hand_recognizer = None
        self.face_landmarker = None

        # Load models according to mode
        if self.mode in ("hand", "both"):
            try:
                base_options = python.BaseOptions(model_asset_path=hand_model_path)
                options = vision.GestureRecognizerOptions(
                    base_options=base_options,
                    running_mode=vision.RunningMode.IMAGE,
                    num_hands=1,
                    min_hand_detection_confidence=0.5,
                    min_hand_presence_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                self.hand_recognizer = vision.GestureRecognizer.create_from_options(options)
            except Exception as e:
                print(f"[VisionTracker] Failed to load hand model: {e}")

        if self.mode in ("head_eye", "both"):
            try:
                base_options = python.BaseOptions(model_asset_path=face_model_path)
                options = vision.FaceLandmarkerOptions(
                    base_options=base_options,
                    output_face_blendshapes=True,
                    running_mode=vision.RunningMode.IMAGE,
                    num_faces=1,
                    min_face_detection_confidence=0.5,
                    min_face_presence_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                self.face_landmarker = vision.FaceLandmarker.create_from_options(options)
            except Exception as e:
                print(f"[VisionTracker] Failed to load face model: {e}")

    def start_camera(self):
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.camera_index)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)

    def stop_camera(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def read_frame(self):
        if self.cap is None or not self.cap.isOpened():
            self.start_camera()

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return None, None

        # Flip horizontally for natural mirror behavior
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        event = {}

        # 1. Face & Eye tracking
        if self.face_landmarker:
            face_res = self.face_landmarker.detect(mp_image)
            if face_res.face_landmarks and len(face_res.face_landmarks) > 0:
                face_lm = face_res.face_landmarks[0]
                # Landmark 1: Nose tip
                nose_tip = (face_lm[1].x, face_lm[1].y, face_lm[1].z)

                blink_left = 0.0
                blink_right = 0.0
                if face_res.face_blendshapes and len(face_res.face_blendshapes) > 0:
                    bs_dict = {b.category_name: b.score for b in face_res.face_blendshapes[0]}
                    blink_left = float(bs_dict.get("eyeBlinkLeft", 0.0))
                    blink_right = float(bs_dict.get("eyeBlinkRight", 0.0))

                event["face"] = {
                    "nose_tip": nose_tip,
                    "blink_left": blink_left,
                    "blink_right": blink_right,
                    "landmarks": [(lm.x, lm.y, lm.z) for lm in face_lm]
                }

        # 2. Hand tracking
        if self.hand_recognizer:
            hand_res = self.hand_recognizer.recognize(mp_image)
            if hand_res.hand_landmarks and len(hand_res.hand_landmarks) > 0:
                landmarks = [(lm.x, lm.y, lm.z) for lm in hand_res.hand_landmarks[0]]
                gesture_name = "None"
                confidence = 0.0
                if hand_res.gestures and len(hand_res.gestures) > 0 and len(hand_res.gestures[0]) > 0:
                    top_cat = hand_res.gestures[0][0]
                    gesture_name = top_cat.category_name
                    confidence = float(top_cat.score)

                handedness = "Right"
                if hand_res.handedness and len(hand_res.handedness) > 0 and len(hand_res.handedness[0]) > 0:
                    handedness = hand_res.handedness[0][0].category_name

                index_tip = (landmarks[8][0], landmarks[8][1])
                thumb_tip = (landmarks[4][0], landmarks[4][1])
                palm_center = (
                    (landmarks[0][0] + landmarks[5][0] + landmarks[17][0]) / 3.0,
                    (landmarks[0][1] + landmarks[5][1] + landmarks[17][1]) / 3.0
                )
                pinch_dist = math.hypot(index_tip[0] - thumb_tip[0], index_tip[1] - thumb_tip[1])

                event["gesture"] = gesture_name
                event["confidence"] = confidence
                event["handedness"] = handedness
                event["landmarks"] = landmarks
                event["index_tip"] = index_tip
                event["thumb_tip"] = thumb_tip
                event["palm_center"] = palm_center
                event["pinch_dist"] = pinch_dist

        return frame, event if event else None
