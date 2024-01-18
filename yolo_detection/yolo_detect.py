import cv2
import numpy as np
import time
import json
import os
from datetime import datetime, timedelta

import urllib.parse
import urllib.request

# 第三方服务server酱推送
KEY = ''  # server酱的key
def sc_send(text, desp='', key='[SENDKEY]'):
    postdata = urllib.parse.urlencode({'text': text, 'desp': desp}).encode('utf-8')
    url = f'https://sctapi.ftqq.com/{key}.send'
    req = urllib.request.Request(url, data=postdata, method='POST')
    with urllib.request.urlopen(req) as response:
        result = response.read().decode('utf-8')
    return result


# 保存图片，将时间戳保存在缩放后的图片上
def save_img(img, jsonSavePath):
    # 获取当前时间戳，用作图片名称
    timestamp = time.time()
    pic_path = str(timestamp)+'.jpg'
    # 将时间戳转换为可阅读的形式
    readable_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
    
    # 缩放
    scaled_image = cv2.resize(img, (width // 4, height // 4))
    
    # 在矩阵上添加文字
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_size = 0.5
    font_thickness = 2
    text_position = (0, 20)
    text_color = (255, 255, 0)

    cv2.putText(scaled_image, readable_time, text_position, font, font_size, text_color, font_thickness)
    
    # 保存图片
    jpeg_quality = 50
    cv2.imwrite(os.path.join('./result', pic_path), scaled_image, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])
    with open(jsonSavePath, 'r') as f:
        data = json.load(f)
    
    with open(jsonSavePath, 'w+') as f:
        data['timestamp'].append(timestamp)
        data['path'].append(pic_path)
        f.write(json.dumps(data, indent=2))

# 加载YOLO模型
net = cv2.dnn.readNet("./path/yolov3.weights", "./path/yolov3.cfg")
layer_names = net.getLayerNames()
output_layers = [layer_names[i[0]-1] for i in net.getUnconnectedOutLayers()]

# 加载coco.names类别文件
with open("./path/coco.names", "r") as f:
    classes = [line.strip() for line in f.readlines()]
colors = np.random.uniform(0, 255, size=(len(classes), 3))

# 初始化json
with open('./result/results.json', 'w+') as f:
    data = {"timestamp":[],"path": []}
    f.write(json.dumps(data, indent=2))
    
with open('./result/timeline.json', 'w+') as f:
    data = {"timestamp":[],"path": []}
    f.write(json.dumps(data, indent=2))
    
# 早上6点才执行后续代码
# 获取当前时间
current_time = datetime.now()
# 设置目标时间为晚上九点
target_time = datetime(current_time.year, current_time.month, current_time.day, 6, 0, 0)
# 如果当前时间已经晚于目标时间，则将目标时间设置为第二天的九点
if current_time > target_time:
    target_time += timedelta(days=1)
# 计算需要等待的时间
# wait_time = (target_time - current_time).total_seconds()
# 在目标时间之前循环等待
while datetime.now() < target_time:
    pass
# 目标时间到达后继续执行以下代码
print("已经等待到早上6点，现在继续执行后续代码")


# 8点之后，每20分钟存一次图像，存到9点，验证程序是否工作。
current_time = datetime.now()
time_to_save_start = datetime(current_time.year, current_time.month, current_time.day, 8, 0, 0)
time_to_save_end = datetime(current_time.year, current_time.month, current_time.day, 9, 10, 0)

# 只有第一次目标检测，向第三方推送提醒
is_first_visted = True

# 从摄像头获取视频流
cap = cv2.VideoCapture(0)
while cap.isOpened():
    ret, img = cap.read()
    if not ret:
        break
    
    now_time = datetime.now()
    if (now_time > time_to_save_start and now_time < time_to_save_end):
        time_to_save_start += timedelta(minutes=20)
        save_img(img, './result/timeline.json')

    height, width, channels = img.shape
    blob = cv2.dnn.blobFromImage(
        img, 0.00392, (416, 416), (0, 0, 0), True, crop=True)
    net.setInput(blob)
    outs = net.forward(output_layers)

    class_ids = []
    confidences = []
    boxes = []

    for output in outs:
        for detection in output:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.5:
                # 物体坐标
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)

                # 矩形坐标
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)
                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    # 应用非极大值抑制
    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)

    # 显示图片和bbox
    detected = False
    for i in range(len(boxes)):
        if i in indexes:
            label = str(classes[class_ids[i]])
            if label == 'person':
                detected = True
                x, y, w, h = boxes[i]
                confidence = confidences[i]
                color = (0, 255, 0)
                cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
                cv2.putText(img, label + " " + str(round(confidence, 2)),
                            (x, y + 30), cv2.FONT_HERSHEY_PLAIN, 2, color, 2)

    if detected:
        save_img(img, './result/results.json')
        if is_first_visted:
            is_first_visted = False
            sc_send('检测提醒', '仅提醒6点后第一次响应', KEY)

    cv2.imshow("Image", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()