import cv2
import numpy as np
import time
import json
import os
from datetime import datetime, timedelta
import threading
import queue

import urllib.parse
import urllib.request

weights_path = "./path/yolov3.weights"
cfg_path = "./path/yolov3.cfg"
result_path = "result"

# 需要配置，工作时间，以小时为单位，例如[8, 10]代表8点开始，10点结束
work_time = [[6, 10], [12, 15]]
# 抓拍时间间隔，默认工作期间开始抓拍
snap_gap = 10 * 60 

KEY = ''  # server酱的key

class Yolo_detector:
    def __init__(self) -> None:
        # 初始化变量
        self.date = None
        self.new_day = False
        '''
            {
                'timeline':{
                    'timestamp':'file/path'
                },
                'detected':{
                    'timestamp':'file/path'
                }
            }
        '''
        self.json_dict = {}
        self.is_started = False
        self.mutex = threading.Lock()
        self.thread = None
        self.main_loop_running = False
        # 上次状态更新时间, 开始默认为0点
        self.last_time = self._get_timestamp_hour(0)
        # 上次抓拍时间
        self.last_snap_time = self._get_timestamp_hour(0)


        # 加载模型并创建文件夹
        self._load_model()
        self._create_result_dir()

        self._date_check()
        self._run()

    # 设置开启
    def set_start(self):
        self._set_status(True)

    # 设置关闭
    def set_stop(self):
        self._set_status(False)

    # 状态查询
    def get_status(self):
        return self.is_started

    def cap_now(self):
        if not self.is_started:
            self._start()
        ret, img = self.cap_once()
        if type(img) == type(None):
            return None
        p = self.save_img(img, jsonSavePath='timeline')
        if not self.is_started:
            self._stop()
        return p

    # 程序启动,创建线程执行主循环
    def _run(self):
        if self.thread == None:
            self._update_status()
            self.main_loop_running = True
            self.thread = threading.Thread(target=self._main_loop)
            self.thread.daemon = True
            self.thread.start()
    
    # 终止主循环
    def _exit(self):
        self.main_loop_running = False

    def _load_model(self):
        self.net = cv2.dnn.readNet(weights_path, cfg_path)

        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL)
        self.layer_names = self.net.getLayerNames()
        self.output_layers = [self.layer_names[i-1] for i in self.net.getUnconnectedOutLayers()]   

        # 加载coco.names类别文件
        with open("./path/coco.names", "r") as f:
            self.classes = [line.strip() for line in f.readlines()]
        self.colors = np.random.uniform(0, 255, size=(len(self.classes), 3))

    
    def _create_result_dir(self):
        # 如果文件夹不存在，创建
        os.makedirs(result_path, exist_ok=True)

    # 检查是否是新的一天
    def _date_check(self):
        # 获取当前时间
        current_time = datetime.now()

        # 获取月份和日期，并转换为指定的字符串形式
        month_day_string = current_time.strftime("%m-%d")

        if month_day_string != self.date:
            self.date = month_day_string
            self.new_day = True
            os.makedirs(os.path.join(result_path, self.date), exist_ok=True)
            # 新的一天，新的数据结构
            self.json_dict = {
                'timeline':dict(),
                'detected':dict()
            }
            # 重新计算工作时间，并转换为时间戳
            self.work_time = []
            for start_hour, end_hour in work_time:
                self.work_time.append([self._get_timestamp_hour(start_hour),
                                       self._get_timestamp_hour(end_hour)])
    
    # 开始检测，内部成员函数，如果需要开启服务请调用set_start()
    # 主要用于申请资源
    def _start(self):
        self.cap = cv2.VideoCapture(0)
    
    def _stop(self):
        self.cap.release()
        cv2.destroyAllWindows()

    # 自动更新当前状态, 多线程下需要互斥运行
    def _update_status(self):
        self.mutex.acquire()
        try:
            next_status = self.is_started
            t = time.time()
            for start_time, end_time in self.work_time:
                if start_time > self.last_time and start_time < t:
                    next_status = True
                
                if end_time > self.last_time and end_time < t:
                    next_status = False
            if next_status != self.is_started:
                if next_status:
                    self._start()
                else:
                    self._stop()
                
                self.is_started = next_status
            self.last_time = t
        finally:
            self.mutex.release()
    
    # 直接设置状态，多线程下互斥运行
    def _set_status(self, status):
        self.mutex.acquire()
        try:
            if self.is_started != status:
                if status:
                    self._start()
                else:
                    self._stop()
                self.is_started = status
        finally:
            self.mutex.release()


    def _main_loop(self):
        que = queue.Queue()
        while self.main_loop_running:
            try:
                self._date_check()
                self._update_status()

                if self.is_started:
                    ret, img = self.cap_once()
                    if type(img) == type(None):
                        return
                    
                    if time.time() - self.last_snap_time > snap_gap:
                        self.save_img(img, jsonSavePath='timeline')
                        self.last_snap_time = time.time()
                    
                    t = time.time()
                    # 抓拍到了
                    if ret:
                        if self.new_day and KEY:
                            # 先设置标志位再尝试
                            self.new_day = False
                            self.sc_send(key=KEY)

                        if que.qsize() < 10 or que.queue[0] < t - 60:
                            self.save_img(img)

                        que.put(t)
                        if que.qsize() > 10:
                            que.get()

                time.sleep(0.1)
            except Exception as e:
                print(e)
            
            
                    
        self._set_status(False)

    # 返回今天指定小时整点的时间戳
    def _get_timestamp_hour(self, hour):
        current_date = datetime.now().date()

        # 设置时间为8点
        target_time = datetime.combine(current_date, datetime.strptime("{}:00".format(hour), "%H:%M").time())

        # 获取时间戳
        timestamp = int(target_time.timestamp())
        return timestamp

    # 第三方服务server酱推送
    def sc_send(text, desp='', key='[SENDKEY]'):
        postdata = urllib.parse.urlencode({'text': text, 'desp': desp}).encode('utf-8')
        url = f'https://sctapi.ftqq.com/{key}.send'
        req = urllib.request.Request(url, data=postdata, method='POST')
        with urllib.request.urlopen(req) as response:
            result = response.read().decode('utf-8')
        return result
    
    def cap_once(self):
        if self.cap.isOpened():
            ret, img = self.cap.read()
            if not ret:
                return False, None
            
            height, width, channels = img.shape
            blob = cv2.dnn.blobFromImage(
                img, 0.00392, (416, 416), (0, 0, 0), True, crop=True)
            self.net.setInput(blob)
            outs = self.net.forward(self.output_layers)

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
                    label = str(self.classes[class_ids[i]])
                    if label == 'person':
                        detected = True
                        x, y, w, h = boxes[i]
                        confidence = confidences[i]
                        color = (0, 255, 0)
                        cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
                        cv2.putText(img, label + " " + str(round(confidence, 2)),
                                    (x, y + 30), cv2.FONT_HERSHEY_PLAIN, 2, color, 2)

            return detected, img

        

    # 保存图片，将时间戳保存在缩放后的图片上
    def save_img(self, img, jsonSavePath='detected'):
        # 获取当前时间戳，用作图片名称
        timestamp = time.time()
        pic_path = str(timestamp)+'.jpg'
        # 将时间戳转换为可阅读的形式
        readable_time = time.strftime('%H:%M:%S', time.localtime(timestamp))
        
        # 缩放
        scaled_image = cv2.resize(img, (img.shape[1] // 4, img.shape[0] // 4))
        
        # 在矩阵上添加文字
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_size = 0.5
        font_thickness = 2
        text_position = (0, 20)
        text_color = (255, 255, 0)

        cv2.putText(scaled_image, readable_time, text_position, font, font_size, text_color, font_thickness)
        
        # 保存图片
        jpeg_quality = 50
        cv2.imwrite(os.path.join('./result', self.date, pic_path), scaled_image, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])
        self.json_dict[jsonSavePath][timestamp] = os.path.join('./result', self.date, pic_path)
        return os.path.join('./result', self.date, pic_path)



if __name__ == '__main__':
    yolo = Yolo_detector()
    # print(yolo.get_status())
    yolo.set_start()
    # print(yolo.get_status())
    time.sleep(5)
    yolo.set_stop()
    time.sleep(10)
    while True:
        time.sleep(1)
        print(yolo.is_started)
    yolo._exit()
    exit()

        
