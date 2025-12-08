import cv2

aruco = cv2.aruco
dictionary = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)

def arGenerator():
    fileName = "ar.png"
    # 0: ID番号，150x150ピクセル
    generator = aruco.generateImageMarker(dictionary, 0, 150)  # ←ここを変更
    cv2.imwrite(fileName, generator)
    img = cv2.imread(fileName)

arGenerator()
