import mediapipe as mp

class module_detection():
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5,
                                 min_tracking_confidence=0.5)

    def process_images(self, frame, imagesRGB):
        result = self.pose.process(imagesRGB)
        
        if result.pose_landmarks:
            mp.solutions.drawing_utils.draw_landmarks(
                frame,
                result.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                mp.solutions.drawing_utils.DrawingSpec(color=(0,255,0), thickness=3, circle_radius=3),
                mp.solutions.drawing_utils.DrawingSpec(color=(0,0,255), thickness=2),
            )
            return True, result.pose_landmarks
        else:
            return False, imagesRGB

    
    
        