# CameraMonitorYOLO
用于本地摄像头调用的yolo算法检测，检测到person时，保存图片和对应时间戳到本地。
由python脚本执行目标检测，并保存为`results.json`和`timeline.json`。
服务器端和前端有node框架实现，静态下发html文件。
`yolo_detection/path`中缺乏`yolov3.weights`，下载地址<https://pjreddie.com/darknet/yolo/>

## 执行
`yolo_detection`中执行，`python yolo_detec.py`
`express_server`中执行，`npm install`安装依赖，`node index.js`启动服务器。


## toDo
服务端在python实现