import cv2
from cv2 import aruco

def main():
    dictionary = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
    # OpenCV 4.7 以降は DetectorParameters() をそのまま使う
    parameters = aruco.DetectorParameters()

    # 2. カメラを開く（0 は内蔵 or 1台目のUSBカメラ）
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("カメラが開けませんでした")
        return

    print("カメラ起動中：マーカーを映してみてね。q キーで終了。")

    while True:
        # 3. 1フレーム取得
        ret, frame = cap.read()
        if not ret:
            print("フレームが取得できませんでした")
            break

        # 4. マーカーを検出
        #   corners: マーカーの四隅の座標
        #   ids:     検出された ID の配列
        corners, ids, rejected = aruco.detectMarkers(
            frame,
            dictionary,
            parameters=parameters
        )

        # 5. 見つかったら枠とIDを描画
        if ids is not None and len(ids) > 0:
            # 画像上に枠とIDを描く
            aruco.drawDetectedMarkers(frame, corners, ids)
            # ID をコンソールに出す
            print("検出されたID:", ids.flatten())

        # 6. 画面に表示
        cv2.imshow("ArUco Camera", frame)

        # 7. q キーで終了
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()