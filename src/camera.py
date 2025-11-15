import cv2

class camera_module():

    def __init__(self):
        self.cap = None
        self.ret, self.frame = None, None

    def add_camera(self, camera):
        self.cap = cv2.VideoCapture(camera, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        return self.cap
    
    def chcel_camera(self):
        if not self.cap:
            return
        
        self.ret, self.frame = self.cap.read()

        if not self.ret:
            return
        
        return self.frame
        
    def color_images(self):
        bgr_t_rgb = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
        return bgr_t_rgb
    
    def isopen_cam(self):
        if self.cap.isOpened():
            return True
        else:
            return False
    def cap_release(self):
        self.cap.release()