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
                    num_hands=2,
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

    def close(self):
        self.stop_camera()
        if self.hand_recognizer:
            try:
                self.hand_recognizer.close()
            except Exception:
                pass
            self.hand_recognizer = None
        if self.face_landmarker:
            try:
                self.face_landmarker.close()
            except Exception:
                pass
            self.face_landmarker = None

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

        # 2. Hand tracking (Up to 2 hands for full dual-hand gestures)
        if self.hand_recognizer:
            hand_res = self.hand_recognizer.recognize(mp_image)
            if hand_res.hand_landmarks and len(hand_res.hand_landmarks) > 0:
                hands_list = []
                for i in range(len(hand_res.hand_landmarks)):
                    raw_lms = hand_res.hand_landmarks[i]
                    landmarks = [(lm.x, lm.y, lm.z) for lm in raw_lms]

                    gesture_name = "None"
                    confidence = 0.0
                    if hand_res.gestures and i < len(hand_res.gestures) and len(hand_res.gestures[i]) > 0:
                        top_cat = hand_res.gestures[i][0]
                        gesture_name = top_cat.category_name
                        confidence = float(top_cat.score)

                    handedness = "Right"
                    if hand_res.handedness and i < len(hand_res.handedness) and len(hand_res.handedness[i]) > 0:
                        handedness = hand_res.handedness[i][0].category_name

                    wrist = landmarks[0]
                    index_tip = (landmarks[8][0], landmarks[8][1])
                    thumb_tip = (landmarks[4][0], landmarks[4][1])
                    middle_tip = (landmarks[12][0], landmarks[12][1])
                    palm_center = (
                        (landmarks[0][0] + landmarks[5][0] + landmarks[17][0]) / 3.0,
                        (landmarks[0][1] + landmarks[5][1] + landmarks[17][1]) / 3.0
                    )

                    # Hand scale (wrist to middle MCP)
                    hand_scale = math.hypot(wrist[0] - landmarks[9][0], wrist[1] - landmarks[9][1])
                    h_scale_safe = max(hand_scale, 0.03)

                    # Distances
                    d_thumb_index = math.hypot(thumb_tip[0] - index_tip[0], thumb_tip[1] - index_tip[1]) / h_scale_safe
                    d_thumb_middle = math.hypot(thumb_tip[0] - middle_tip[0], thumb_tip[1] - middle_tip[1]) / h_scale_safe

                    # Finger extensions
                    def is_extended(tip_idx, pip_idx):
                        d_tip = math.hypot(wrist[0] - landmarks[tip_idx][0], wrist[1] - landmarks[tip_idx][1])
                        d_pip = math.hypot(wrist[0] - landmarks[pip_idx][0], wrist[1] - landmarks[pip_idx][1])
                        return d_tip > d_pip * 1.15

                    index_ext = is_extended(8, 6)
                    middle_ext = is_extended(12, 10)
                    ring_ext = is_extended(16, 14)
                    pinky_ext = is_extended(20, 18)
                    thumb_ext = math.hypot(wrist[0] - landmarks[4][0], wrist[1] - landmarks[4][1]) > math.hypot(wrist[0] - landmarks[2][0], wrist[1] - landmarks[2][1]) * 1.12

                    hand_info = {
                        "landmarks": landmarks,
                        "gesture": gesture_name,
                        "confidence": confidence,
                        "handedness": handedness,
                        "index_tip": index_tip,
                        "thumb_tip": thumb_tip,
                        "middle_tip": middle_tip,
                        "palm_center": palm_center,
                        "hand_scale": hand_scale,
                        "pinch_dist": d_thumb_index,
                        "pinch_middle_dist": d_thumb_middle,
                        "index_extended": index_ext,
                        "middle_extended": middle_ext,
                        "ring_extended": ring_ext,
                        "pinky_extended": pinky_ext,
                        "thumb_extended": thumb_ext,
                        "is_pointing": index_ext and not middle_ext and not ring_ext and not pinky_ext,
                        "is_two_finger": index_ext and middle_ext and not ring_ext and not pinky_ext,
                        "is_open_palm": index_ext and middle_ext and ring_ext and pinky_ext,
                    }
                    hands_list.append(hand_info)

                event["hands"] = hands_list

                # Primary hand (prefer Right hand or first detected hand)
                primary = next((h for h in hands_list if h["handedness"] == "Right"), hands_list[0])
                event["gesture"] = primary["gesture"]
                event["confidence"] = primary["confidence"]
                event["handedness"] = primary["handedness"]
                event["landmarks"] = primary["landmarks"]
                event["index_tip"] = primary["index_tip"]
                event["thumb_tip"] = primary["thumb_tip"]
                event["palm_center"] = primary["palm_center"]
                event["pinch_dist"] = primary["pinch_dist"]
                event["hand_scale"] = primary["hand_scale"]

        return frame, event if event else None
