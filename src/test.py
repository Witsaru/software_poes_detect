# active_ui.py
import sys
import cv2
import math

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QSizePolicy, QLabel, QWidget
)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap

from collections import deque

import detention_module as dm
import camera
import cal

# Matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

mp_pose = dm.module_detection().mp_pose  # use same namespace as detention_module


# ----------------- Angle helper (kept simple) -----------------
def angle_3pt(a, b, c):
    ax, ay = a
    bx, by = b
    cx, cy = c
    ab = (ax - bx, ay - by)
    cb = (cx - bx, cy - by)
    dot = ab[0] * cb[0] + ab[1] * cb[1]
    mag_ab = (ab[0] ** 2 + ab[1] ** 2) ** 0.5
    mag_cb = (cb[0] ** 2 + cb[1] ** 2) ** 0.5
    if mag_ab * mag_cb == 0:
        return 0.0
    cos_angle = dot / (mag_ab * mag_cb)
    cos_angle = max(min(cos_angle, 1.0), -1.0)
    return math.degrees(math.acos(cos_angle))


# ----------------- Graph helper -----------------
class AngleGraph:
    def __init__(self, container_widget, maxlen=200):
        self.fig = Figure(figsize=(4, 2), tight_layout=True)
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_ylim(0, 180)
        self.ax.grid(True, alpha=0.3)

        self.maxlen = maxlen
        self.n = deque([0.0] * maxlen, maxlen=maxlen)
        self.a = deque([0.0] * maxlen, maxlen=maxlen)
        self.b = deque([0.0] * maxlen, maxlen=maxlen)
        self.l = deque([0.0] * maxlen, maxlen=maxlen)

        layout = QVBoxLayout(container_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        container_widget.setLayout(layout)

    def push(self, neck, arm, body, leg):
        self.n.append(neck)
        self.a.append(arm)
        self.b.append(body)
        self.l.append(leg)
        self.redraw()

    def redraw(self):
        self.ax.clear()
        self.ax.set_ylim(0, 180)
        self.ax.grid(True, alpha=0.3)
        self.ax.plot(list(self.n), label="Neck")
        self.ax.plot(list(self.a), label="Arm")
        self.ax.plot(list(self.b), label="Body")
        self.ax.plot(list(self.l), label="Leg")
        self.ax.legend(loc="upper right", fontsize=8)
        self.canvas.draw()


# ----------------- Main UI -----------------
class WorkStudyCamera(QMainWindow):
    def __init__(self, ui_path="src\main.ui"):
        super().__init__()

        loader = QUiLoader()
        self.ui = loader.load(ui_path, None)
        if self.ui is None:
            raise FileNotFoundError(f"UI file not found or failed to load: {ui_path}")
        self.setCentralWidget(self.ui)

        # modules
        self.cameraA = camera.camera_module()
        self.cameraB = camera.camera_module()
        # use separate mediapipe instances via detention_module
        self.detectorA = dm.module_detection()
        self.detectorB = dm.module_detection()
        self.cal = cal.Cal_function()

        # UI references (must exist in your main.ui)
        self.labelA = self.ui.findChild(QLabel, "labelCameraA")
        self.labelB = self.ui.findChild(QLabel, "labelCameraB")

        self.comboA = self.ui.comboCameraA
        self.comboB = self.ui.comboCameraB

        self.lblActiveA = self.ui.lblActiveCamA
        self.lblActiveB = self.ui.lblActiveCamB

        self.btnStart = self.ui.btnStart
        self.btnStop = self.ui.btnStop

        # set scaled contents
        for lbl in (self.labelA, self.labelB):
            lbl.setScaledContents(True)
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Graphs
        self.graphA = self.ui.findChild(QWidget, "graphWidgetA")
        self.graphB = self.ui.findChild(QWidget, "graphWidgetB")

        # Camera handles (cv2.VideoCapture) will be in camera_modules via add_camera()
        self.capA = None
        self.capB = None

        # timers
        self.timerA = QTimer(self)
        self.timerB = QTimer(self)
        self.timerA.timeout.connect(self.update_frameA)
        self.timerB.timeout.connect(self.update_frameB)

        # populate camera lists
        self.detect_cameras()

        # connect buttons
        self.btnStart.clicked.connect(self.start_both)
        self.btnStop.clicked.connect(self.stop_both)

        # show
        self.show()

    # ---------------- detect available camera indices ----------------
    def detect_cameras(self, max_scan=6):
        # fill both combos with the same detected devices
        self.comboA.clear()
        self.comboB.clear()
        for i in range(max_scan):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                self.comboA.addItem(f"Camera {i}", i)
                self.comboB.addItem(f"Camera {i}", i)
                cap.release()
        if self.comboA.count() == 0:
            self.comboA.addItem("No camera", -1)
            self.comboB.addItem("No camera", -1)

    # ---------------- start/stop both ----------------
    def start_both(self):
        # camera A
        idxA = self.comboA.currentData()
        if idxA is None or idxA < 0:
            self.lblActiveA.setText("Active: None")
        else:
            # if already opened release first
            try:
                if self.cameraA.cap and self.cameraA.cap.isOpened():
                    self.cameraA.cap_release()
            except Exception:
                pass
            self.cameraA.add_camera(idxA)
            if self.cameraA.isopen_cam():
                self.lblActiveA.setText(f"Active: Camera {idxA}")
                self.timerA.start(30)
            else:
                self.lblActiveA.setText("Active: Failed")

        # camera B
        idxB = self.comboB.currentData()
        if idxB is None or idxB < 0:
            self.lblActiveB.setText("Active: None")
        else:
            try:
                if self.cameraB.cap and self.cameraB.cap.isOpened():
                    self.cameraB.cap_release()
            except Exception:
                pass
            self.cameraB.add_camera(idxB)
            if self.cameraB.isopen_cam():
                self.lblActiveB.setText(f"Active: Camera {idxB}")
                self.timerB.start(30)
            else:
                self.lblActiveB.setText("Active: Failed")

    def stop_both(self):
        self.timerA.stop()
        self.timerB.stop()
        try:
            if self.cameraA.cap and self.cameraA.cap.isOpened():
                self.cameraA.cap_release()
        except Exception:
            pass
        try:
            if self.cameraB.cap and self.cameraB.cap.isOpened():
                self.cameraB.cap_release()
        except Exception:
            pass

        self.labelA.clear()
        self.labelB.clear()
        self.lblActiveA.setText("Active: None")
        self.lblActiveB.setText("Active: None")

    # ---------------- frame loop A ----------------
    def update_frameA(self):
        frame = self.cameraA.chcel_camera()
        if frame is None:
            return

        rgb = self.cameraA.color_images()  # returns RGB ndarray
        ok, lm = self.detectorA.process_images(frame, rgb)
        # detector returns (True, landmarks) or (False, imagesRGB)
        if ok:
            # process landmarks -> detector draws on frame already
            self.update_anglesA(lm, frame)

        self._display_frame(self.labelA, frame)

    # ---------------- frame loop B ----------------
    def update_frameB(self):
        frame = self.cameraB.chcel_camera()
        if frame is None:
            return

        rgb = self.cameraB.color_images()
        ok, lm = self.detectorB.process_images(frame, rgb)
        if ok:
            self.update_anglesB(lm, frame)

        self._display_frame(self.labelB, frame)

    # ---------------- display helper ----------------
    def _display_frame(self, label, frame):
        # frame assumed BGR with landmarks drawn by detector
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except Exception:
            return
        h, w, ch = frame_rgb.shape
        qimg = QImage(frame_rgb.data, w, h, w * ch, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)
        pix = pix.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(pix)

    # ---------------- angle calc A ----------------
    def update_anglesA(self, lm, frame):
        h, w, _ = frame.shape
        p = lm.landmark

        def g(i): return int(p[i].x * w), int(p[i].y * h)

        neck = g(mp_pose.PoseLandmark.NOSE)
        ls = g(mp_pose.PoseLandmark.LEFT_SHOULDER)
        rs = g(mp_pose.PoseLandmark.RIGHT_SHOULDER)
        center = ((ls[0] + rs[0]) // 2, (ls[1] + rs[1]) // 2)
        neck_angle = self.cal.angle_3pt(ls, center, neck)

        elbow = g(mp_pose.PoseLandmark.LEFT_ELBOW)
        wrist = g(mp_pose.PoseLandmark.LEFT_WRIST)
        arm_angle = self.cal.angle_3pt(ls, elbow, wrist)

        hip = g(mp_pose.PoseLandmark.LEFT_HIP)
        body_angle = abs(math.degrees(math.atan2(center[0] - hip[0], center[1] - hip[1])))

        knee = g(mp_pose.PoseLandmark.LEFT_KNEE)
        ankle = g(mp_pose.PoseLandmark.LEFT_ANKLE)
        leg_angle = self.cal.angle_3pt(hip, knee, ankle)

        # update UI labels (optional: you can add separate label group for each camera)
        try:
            self.ui.lblNeckA.setText(f"Neck A: {neck_angle:.1f}°")
            self.ui.lblArmA.setText(f"Arm A: {arm_angle:.1f}°")
            self.ui.lblBodyA.setText(f"Body A: {body_angle:.1f}°")
            self.ui.lblLegA.setText(f"Leg A: {leg_angle:.1f}°")
        except Exception:
            pass

        # push to graph A
        self.graphA.push(neck_angle, arm_angle, body_angle, leg_angle)

    # ---------------- angle calc B ----------------
    def update_anglesB(self, lm, frame):
        h, w, _ = frame.shape
        p = lm.landmark

        def g(i): return int(p[i].x * w), int(p[i].y * h)

        neck = g(mp_pose.PoseLandmark.NOSE)
        ls = g(mp_pose.PoseLandmark.LEFT_SHOULDER)
        rs = g(mp_pose.PoseLandmark.RIGHT_SHOULDER)
        center = ((ls[0] + rs[0]) // 2, (ls[1] + rs[1]) // 2)
        neck_angle = self.cal.angle_3pt(ls, center, neck)

        elbow = g(mp_pose.PoseLandmark.LEFT_ELBOW)
        wrist = g(mp_pose.PoseLandmark.LEFT_WRIST)
        arm_angle = self.cal.angle_3pt(ls, elbow, wrist)

        hip = g(mp_pose.PoseLandmark.LEFT_HIP)
        body_angle = abs(math.degrees(math.atan2(center[0] - hip[0], center[1] - hip[1])))

        knee = g(mp_pose.PoseLandmark.LEFT_KNEE)
        ankle = g(mp_pose.PoseLandmark.LEFT_ANKLE)
        leg_angle = self.cal.angle_3pt(hip, knee, ankle)

        # update UI labels (optional)
        try:
            self.ui.lblNeckB.setText(f"Neck B: {neck_angle:.1f}°")
            self.ui.lblArmB.setText(f"Arm B: {arm_angle:.1f}°")
            self.ui.lblBodyB.setText(f"Body B: {body_angle:.1f}°")
            self.ui.lblLegB.setText(f"Leg B: {leg_angle:.1f}°")
        except Exception:
            pass

        # push to graph B
        self.graphB.push(neck_angle, arm_angle, body_angle, leg_angle)


# ---------------- run ----------------
def run_ui():
    app = QApplication(sys.argv)
    w = WorkStudyCamera()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_ui()
