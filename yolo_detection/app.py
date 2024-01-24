from flask import Flask, jsonify, send_from_directory
import os
import json
import base64
from yolo_detect import *


app = Flask(__name__)
yolod = Yolo_detector()
yolod.set_start()

BASE_PATH = '../yolo_detection/result/'

def image_to_base64(path):
    with open(path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

@app.route('/')
def index():
    # 返回位于当前目录下的index.html文件
    return send_from_directory('./build', 'index.html')

@app.route('/yolo')
def yolo():
    try:
        data_json = yolod.json_dict
        # print(yolod)
        img_paths = [data_json['detected'][i] for i in data_json['detected']]
        if img_paths:
            images_to_front = [image_to_base64(img_path) for img_path in img_paths]
            return jsonify({'imagesToFront': images_to_front})
        else:
            return '暂无人员检测'
    except Exception as e:
        print("发生了错误:", e)
        return ''

@app.route('/timeline')
def timeline():
    try:
        data_json = yolod.json_dict
        img_paths = [data_json['timeline'][i] for i in data_json['timeline']]
        if img_paths:
            images_to_front = [image_to_base64(img_path) for img_path in img_paths]
            return jsonify({'imagesToFront': images_to_front})
        else:
            return '暂无人员检测'
    except Exception as e:
        print("发生了错误:", e)
        return ''


@app.route('/start')
def start():
    yolod.set_start()
    return 'ok'

@app.route('/stop')
def stop():
    yolod.set_stop()
    return 'ok'

@app.route('/status')
def get_status():
    return jsonify({'status':'true' if yolod.get_status() else 'false'})

@app.route('/snap')
def snap():
    path = yolod.cap_now()
    if path:
        img = image_to_base64(path)
        return jsonify({'img':img})
    else:
        return ''
    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000)