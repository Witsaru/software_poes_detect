from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QSizePolicy

from collections import deque

import sys, os

import detention_module as dm
import camera
import cal


# Matplotlib (QtAgg backend)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ---------- Graph Canvas ----------
class AngleGraphCanvas(FigureCanvas):
    def __init__(self, maxlen=200, parent=None):
        fig = Figure(figsize=(5, 1.5), tight_layout=True)
        super().__init__(fig)
        self.setParent(parent)

        self.ax = fig.add_subplot(111)
        self.ax.set_ylim(0, 180)
        self.ax.set_xlim(0, maxlen)
        self.ax.grid(True, alpha=0.3)
        self.ax.set_ylabel("Angle (°)")
        self.ax.set_xlabel("Samples (new → right)")
        self.maxlen = maxlen

        # Buffers
        self.xdata = list(range(-maxlen + 1, 1))
        self.buf_neck = deque([0.0] * maxlen, maxlen=maxlen)
        self.buf_arm = deque([0.0] * maxlen, maxlen=maxlen)
        self.buf_body = deque([0.0] * maxlen, maxlen=maxlen)
        self.buf_leg = deque([0.0] * maxlen, maxlen=maxlen)

        # Lines
        (self.line_neck,) = self.ax.plot(self.xdata, list(self.buf_neck), label="Neck", linewidth=1.5)
        (self.line_arm,) = self.ax.plot(self.xdata, list(self.buf_arm), label="Arm", linewidth=1.5)
        (self.line_body,) = self.ax.plot(self.xdata, list(self.buf_body), label="Body", linewidth=1.5)
        (self.line_leg,) = self.ax.plot(self.xdata, list(self.buf_leg), label="Leg", linewidth=1.5)

        self.ax.legend(loc="upper right", fontsize='small')


    def update(self, neck, arm, body, leg):
        # append
        self.buf_neck.append(neck)
        self.buf_arm.append(arm)
        self.buf_body.append(body)
        self.buf_leg.append(leg)

        # update lines data (x stays same)
        x = self.xdata


class WorkStudyCamera(QMainWindow):
    def __init__(self):
        super().__init__()

        loader = QUiLoader()
        self.ui = loader.load("main.ui", None)
        self.setCentralWidget(self.ui)

        self.cameraA = camera.camera_module()
        self.cameraB = camera.camera_module()
        self.detector = dm.module_detection()
        self.cal = cal.Cal_function()

        # UI
        self.labelCameraA
        self.labelCameraB
        self.comboCameraA
        self.comboCameraB
        self.graphWidgetA
        self.graphWidgetB
        self.lblActiveCamA
        self.lblActiveCamB

        self.label_cam = self.ui.labelCamera
        self.label_cam.setScaledContents(True)
        self.label_cam.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.combo_cam = self.ui.comboCamera
        self.lbl_active = self.ui.lblActiveCam

        self.btn_start = self.ui.btnStart
        self.btn_stop = self.ui.btnStop

        self.lbl_neck = self.ui.lblNeck
        self.lbl_arm = self.ui.lblArm
        self.lbl_body = self.ui.lblBody
        self.lbl_leg = self.ui.lblLeg

        # Mediapipe Pose model
        # self.pose = dm.module_detection().set_detection_conf()

        self.cap = None
        self.timerA = QTimer()
        self.timerB = QTimer()
        self.timer.timeout.connect(self.update_frame)

        # Camera functions
        self.detect_cameras()
        self.combo_cam.currentIndexChanged.connect(self.on_camera_changed)

        # ========= INSERT GRAPH INTO UI =========
        self.graph_container = self.ui.graphWidget

        # Create matplotlib Figure
        self.fig = Figure(figsize=(5, 2), tight_layout=True)
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)

        # initial graph setup
        self.ax.set_title("Angle Graph (Realtime)")
        self.ax.set_ylim(0, 180)
        self.ax.grid(True)
        self.ax.set_xlabel("Frame")
        self.ax.set_ylabel("Angle °")

        # Data buffers
        self.graph_maxlen = 200
        self.neck_data = deque([], maxlen=self.graph_maxlen)
        self.arm_data = deque([], maxlen=self.graph_maxlen)
        self.body_data = deque([], maxlen=self.graph_maxlen)
        self.leg_data = deque([], maxlen=self.graph_maxlen)

        # Attach canvas to UI widget
        lay = QVBoxLayout(self.graph_container)
        lay.setContentsMargins(0,0,0,0)
        lay.addWidget(self.canvas)
        self.graph_container.setLayout(lay)

        # Buttons
        self.btn_start.clicked.connect(self.start)
        self.btn_stop.clicked.connect(self.stop)

        self.show()

    # ------------------------------------------------------------
    # Scan available cameras
    # ------------------------------------------------------------
    def detect_cameras(self):
        self.combo_cam.clear()
        for index in range(10):
            self.cap = self.camera_m.add_camera(index)
            if self.camera_m.isopen_cam():
                self.combo_cam.addItem(f"Camera {index}", index)
                self.camera_m.cap_release()

        if self.combo_cam.count() == 0:
            self.combo_cam.addItem("No camera found", -1)

    # ------------------------------------------------------------
    def start(self):
        cam_index = self.combo_cam.currentData()
        if cam_index is None or cam_index < 0:
            return

        self.camera_m.add_camera(cam_index)
        if not self.camera_m.isopen_cam():
            self.lbl_active.setText("Active Camera: Failed")
            return

        self.lbl_active.setText(f"Active Camera: {cam_index}")
        self.timer.start(30)

    # ------------------------------------------------------------
    def stop(self):
        self.timer.stop()
        if self.cap:
            self.camera_m.cap_release()
            self.cap = None

        self.label_cam.clear()
        self.lbl_active.setText("Active Camera: None")

    # ------------------------------------------------------------
    def on_camera_changed(self):
        if self.timer.isActive():
            self.stop()
            self.start()

    # ------------------------------------------------------------
    # Main video loop
    # ------------------------------------------------------------
    def update_frame(self):
        frame = self.camera_m.chcel_camera()

        # BGR → RGB สำหรับ Mediapipe
        rgb = self.camera_m.color_images()
        # rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.detector.process_images(frame, rgb)

        # ถ้ามี pose ให้เราวาดโครงร่างลงบน BGR frame
        if result[0]:

            # อัปเดตองศา
            self.update_angles(result[1], frame)

        # Convert frame to QPixmap
        frame_rgb = self.camera_m.color_images()
        h, w, ch = frame_rgb.shape
        qimg = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)

        pix = QPixmap.fromImage(qimg)

        # Resize pixmap to fill black area while keeping aspect ratio
        pix = pix.scaled(self.label_cam.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.label_cam.setPixmap(pix)


    # ------------------------------------------------------------
    # Compute Neck / Arm / Body / Leg angles
    # ------------------------------------------------------------
    def update_angles(self, lm, frame):
        h, w, _ = frame.shape
        p = lm.landmark

        def get(i):
            return int(p[i].x * w), int(p[i].y * h)

        neck = get(self.detector.mp_pose.PoseLandmark.NOSE)
        left_shoulder = get(self.detector.mp_pose.PoseLandmark.LEFT_SHOULDER)
        right_shoulder = get(self.detector.mp_pose.PoseLandmark.RIGHT_SHOULDER)

        shoulder_center = (
            (left_shoulder[0] + right_shoulder[0]) // 2,
            (left_shoulder[1] + right_shoulder[1]) // 2
        )

        neck_angle = self.cal.angle_3pt(left_shoulder, shoulder_center, neck)
        self.lbl_neck.setText(f"Neck: {neck_angle:.1f}°")

        elbow = get(self.detector.mp_pose.PoseLandmark.LEFT_ELBOW)
        wrist = get(self.detector.mp_pose.PoseLandmark.LEFT_WRIST)
        arm_angle = self.cal.angle_3pt(left_shoulder, elbow, wrist)
        self.lbl_arm.setText(f"Arm: {arm_angle:.1f}°")

        hip = get(self.detector.mp_pose.PoseLandmark.LEFT_HIP)
        body_angle = self.cal.degrees(hip, shoulder_center)
        self.lbl_body.setText(f"Body: {abs(body_angle):.1f}°")

        knee = get(self.detector.mp_pose.PoseLandmark.LEFT_KNEE)
        ankle = get(self.detector.mp_pose.PoseLandmark.LEFT_ANKLE)
        leg_angle = self.cal.angle_3pt(hip, knee, ankle)
        self.lbl_leg.setText(f"Leg: {leg_angle:.1f}°")

        # push angles into graph buffers
        self.neck_data.append(neck_angle)
        self.arm_data.append(arm_angle)
        self.body_data.append(body_angle)
        self.leg_data.append(leg_angle)

        # update graph
        self.update_graph()

    def update_graph(self):
        self.ax.clear()
        self.ax.set_ylim(0, 180)
        self.ax.grid(True)
        self.ax.set_title("Angle Graph (Realtime)")
        self.ax.set_xlabel("Frame")
        self.ax.set_ylabel("Angle °")

        self.ax.plot(list(self.neck_data), label="Neck")
        self.ax.plot(list(self.arm_data), label="Arm")
        self.ax.plot(list(self.body_data), label="Body")
        self.ax.plot(list(self.leg_data), label="Leg")

        self.ax.legend(loc="upper right", fontsize=8)
        self.canvas.draw()

def run_ui():
    app = QApplication(sys.argv)
    w = WorkStudyCamera()
    sys.exit(app.exec())