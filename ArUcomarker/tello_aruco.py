import cv2
from cv2 import aruco
from djitellopy import Tello
import numpy as np
import time


def make_params():
    """検出パラメータ（やや緩め + コーナー精錬）。"""
    try:
        params = aruco.DetectorParameters()
    except AttributeError:
        params = aruco.DetectorParameters_create()
    params.adaptiveThreshWinSizeMin = 3
    params.adaptiveThreshWinSizeMax = 53
    params.adaptiveThreshWinSizeStep = 4
    params.minMarkerPerimeterRate = 0.02
    params.maxMarkerPerimeterRate = 5.0
    try:
        params.cornerRefinementMethod = aruco.CORNER_REFINE_SUBPIX
    except Exception:
        pass
    return params


def detect_markers(img, dictionary, params):
    """
    BGR → detectMarkers → 見つからなければグレースケールで再トライ。
    ArUcoDetector があれば使い、なければ detectMarkers だけで動かす。
    """
    detector = None
    if hasattr(aruco, "ArucoDetector"):
        try:
            detector = aruco.ArucoDetector(dictionary, params)
        except Exception:
            detector = None

    def _run(src):
        try:
            return aruco.detectMarkers(src, dictionary, parameters=params)
        except AttributeError:
            if detector is not None:
                return detector.detectMarkers(src)
            raise

    try:
        corners, ids, rejected = _run(img)
    except Exception:
        corners = ids = rejected = None

    if ids is None or len(ids) == 0:
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            corners, ids, rejected = _run(gray)
        except Exception:
            pass

    return corners, ids, rejected


def main():
    print("Connecting to Tello...")
    tello = Tello()
    tello.connect()
    try:
        print(f"Battery: {tello.get_battery()}%")
    except Exception:
        pass

    tello.streamon()
    frame_read = tello.get_frame_read()

    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
    aruco_params = make_params()

    print("Started. Press 'q' to quit.")

    try:
        while True:
            frame = frame_read.frame
            if frame is None:
                time.sleep(0.01)
                continue
            # OpenCV が受け付けるように連続メモリにしておく
            frame = np.ascontiguousarray(frame)

            # djitellopy はRGBのことがあるのでBGRに揃える
            if frame.ndim == 3 and frame.shape[2] == 3:
                frame = frame[:, :, ::-1]

            corners, ids, _ = detect_markers(frame, aruco_dict, aruco_params)

            if ids is not None and len(ids) > 0:
                try:
                    aruco.drawDetectedMarkers(frame, corners, ids)
                except Exception:
                    # まれに型が合わない場合があるので再度連続化して描画
                    frame = np.ascontiguousarray(frame)
                    aruco.drawDetectedMarkers(frame, corners, ids)
                print(f"Detected IDs: {ids.flatten().tolist()}")

            cv2.imshow("Tello ArUco", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
    finally:
        tello.streamoff()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
