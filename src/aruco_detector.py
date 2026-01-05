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
        # 小さいマーカー向けに緩め＋コーナー精錬
        self.parameters.adaptiveThreshWinSizeMin = 3
        self.parameters.adaptiveThreshWinSizeMax = 53
        self.parameters.adaptiveThreshWinSizeStep = 4
        self.parameters.minMarkerPerimeterRate = 0.02
        self.parameters.maxMarkerPerimeterRate = 5.0
        try:
            self.parameters.cornerRefinementMethod = aruco.CORNER_REFINE_SUBPIX
        except Exception:
            pass

        # ArUcoDetector があればフォールバック用に保持
        try:
            self.detector = aruco.ArucoDetector(self.dictionary, self.parameters)
        except Exception:
            self.detector = None

    def process(self, frame, draw=True, draw_id=True):
        """
        フレームからマーカーを検出し、必要なら描画も行う。

        Returns:
            frame: 描画済みフレーム
            ids: 検出されたID (Noneのこともある)
            corners: マーカーの頂点座標
        """
        corners = ids = rejected = None

        def _detect(img, use_params=True):
            """
            detectMarkers → (必要なら) ArucoDetector での検出をラップ。
            use_params=False の場合は parameters を渡さず検出。
            """
            if use_params:
                try:
                    return aruco.detectMarkers(img, self.dictionary, parameters=self.parameters)
                except AttributeError:
                    pass
            else:
                try:
                    return aruco.detectMarkers(img, self.dictionary)
                except AttributeError:
                    pass

            if self.detector is not None:
                return self.detector.detectMarkers(img)
            raise AttributeError("No detectMarkers or ArucoDetector available")

        def _rescale_corners(c_list, scale):
            if c_list is None:
                return None
            try:
                return [c / float(scale) for c in c_list]
            except Exception:
                return c_list

        try:
            # 1) BGR + parameters
            corners, ids, rejected = _detect(frame, use_params=True)
        except Exception:
            corners = ids = rejected = None

        if ids is None or len(ids) == 0:
            try:
                # 2) BGR + without parameters
                corners, ids, rejected = _detect(frame, use_params=False)
            except Exception:
                pass

        if ids is None or len(ids) == 0:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # 3) GRAY + parameters
                corners, ids, rejected = _detect(gray, use_params=True)
            except Exception:
                pass

        if ids is None or len(ids) == 0:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # 4) GRAY + without parameters
                corners, ids, rejected = _detect(gray, use_params=False)
            except Exception:
                pass

        # スケーリングして再チャレンジ（Tello映像の小さなマーカー対策）
        if ids is None or len(ids) == 0:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                scale = 1.6
                resized = cv2.resize(gray, (int(gray.shape[1] * scale), int(gray.shape[0] * scale)), interpolation=cv2.INTER_LINEAR)
                corners2, ids2, rejected2 = _detect(resized, use_params=True)
                if ids2 is None or len(ids2) == 0:
                    corners2, ids2, rejected2 = _detect(resized, use_params=False)
                if ids2 is not None and len(ids2) > 0:
                    corners = _rescale_corners(corners2, scale)
                    ids = ids2
                    rejected = rejected2
            except Exception:
                pass

        if ids is not None and len(ids) > 0 and draw:
            # マーカー枠とIDを描画
            aruco.drawDetectedMarkers(frame, corners, ids)

            if draw_id:
                text = f"ID: {int(ids[0])}"
                cv2.putText(frame, text, (10, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        return frame, ids, corners
