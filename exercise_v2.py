import numpy as np
import mediapipe as mp

mp_pose = mp.solutions.pose
vis_thresh = 0.6 # threshold for landmark detection

class Exercise:
    def __init__(self, config):
        self.name = config["name"]
        self.angle_points = config["angle_points"]
        self.sides = config["sides"]
        self.direction = config["direction"]
        # rest_thresh = Angle at limb start point (e.g., Standing for squat)
        # peak_thresh = Angle at limb end point (e.g., Deep squat)
        self.rest_thresh = config["thresholds"]["rest"]
        self.peak_thresh = config["thresholds"]["peak"]
        
        self.stage = "rest" # States: 'rest', 'peak'
        self.reps = 0

    def _get_point(self, landmarks, side, joint):
        landmark_name = f"{side.upper()}_{joint}"
        return landmarks[getattr(mp_pose.PoseLandmark, landmark_name).value]

    def _calculate_angle(self, a, b, c):
        a = np.array([a.x, a.y])
        b = np.array([b.x, b.y])
        c = np.array([c.x, c.y])

        radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - \
                  np.arctan2(a[1]-b[1], a[0]-b[0])
        angle = abs(radians * 180.0 / np.pi)
        
        if angle > 180.0:
            angle = 360 - angle
            
        return angle

    def get_angle(self, landmarks):
        angles = []
        for side in self.sides:
            try:
                p1 = self._get_point(landmarks, side, self.angle_points[0])
                p2 = self._get_point(landmarks, side, self.angle_points[1])
                p3 = self._get_point(landmarks, side, self.angle_points[2])

                # calc if landmarks pass threshold
                if min (p1.visibility, p2.visibility, p3.visibility) < vis_thresh:
                        continue

                angles.append(self._calculate_angle(p1, p2, p3))
            except (AttributeError, IndexError):
                pass # Landmark not visible
        
        if not angles:
            return None
        return max(angles)

    def update(self, landmarks):
        angle = self.get_angle(landmarks)

        if angle is None:
            return None
            
        #curl validation - check if wrist is above elbow at peak / skip other exercises
        if "curl" in self.name.lower():
                try:
                    side = self.sides[0] # left or right
                    elbow = self._get_point(landmarks, side, "ELBOW")
                    wrist = self._get_point(landmarks, side, "WRIST")
                    wrist_raised = wrist.y < elbow.y #cuz y increases downwards
                except:
                        wrist_raised = False # assume false if cant detect wrist
        else:
            wrist_raised = True # set true if its a non curl exercise so later ifs pass
            
        #lat raise validation - check wrist is above elbows when performing exercise
        if "lateral raise" in self.name.lower():
                try:
                    side = self.sides[0] # left or right
                    shoulder = self._get_point(landmarks, side, "SHOULDER")
                    elbow = self._get_point(landmarks, side, "ELBOW")
                    wrist = self._get_point(landmarks, side, "WRIST")
                    arm_raised = (
                        elbow.y <= shoulder.y and        # elbow must be at shoulder height
                        wrist.y >= elbow.y - 0.05     #check if wrist near the height of elbow
                        )
                except:
                    arm_raised = False # if cant detect elbow and wrist
        else:
            arm_raised = True # set true if non lateral raise exercise

        # State Machine: Rest -> Peak -> Rest
        # 0. check direction is increase
        if self.direction == "increase":
            # 1. check if angle above peak
            if angle > self.peak_thresh:
                if arm_raised:
                    self.stage = "peak"
            # 2. chcek angle returns to rest after
            if angle < self.rest_thresh and self.stage == "peak":
                self.stage = "rest"
                self.reps += 1
        
        #0. direction is decrease        
        else:        
            # 1. Check if we reached Peak
            if angle < self.peak_thresh:
                if wrist_raised and arm_raised: #check for curls/lat raise, wont affect other exercises
                    self.stage = "peak"
            
            # 2. Check if we returned to Rest AND were at peak before
            if angle > self.rest_thresh and self.stage == "peak":
                self.stage = "rest"
                self.reps += 1

        return angle
