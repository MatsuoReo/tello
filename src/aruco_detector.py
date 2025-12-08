# aruco_detector.py
import cv2
from cv2 import aruco


class ArUcoDetector:
    """ArUcoマーカー検出クラス"""

    def __init__(self, dictionary_name=aruco.DICT_4X4_50):
        # 辞書を用意
        self.dictionary = aruco.getPredefinedDictionary(dictionary_name)
        # OpenCVのバージョン差分対応
        try:
            self.parameters = aruco.DetectorParameters()
        except AttributeError:
            self.parameters = aruco.DetectorParameters_create()

    def process(self, frame, draw=True, draw_id=True):
        """
        フレームからマーカーを検出し、必要なら描画も行う。

        Returns:
            frame: 描画済みフレーム
            ids: 検出されたID (Noneのこともある)
            corners: マーカーの頂点座標
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        corners, ids, rejected = aruco.detectMarkers(
            gray,
            self.dictionary,
            parameters=self.parameters
        )

        if ids is not None and len(ids) > 0 and draw:
            # マーカー枠とIDを描画
            aruco.drawDetectedMarkers(frame, corners, ids)

            if draw_id:
                text = f"ID: {int(ids[0])}"
                cv2.putText(frame, text, (10, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        return frame, ids, corners