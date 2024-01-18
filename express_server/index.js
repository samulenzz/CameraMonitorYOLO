const express = require('express')
const path = require('path');
const fs = require('fs');

const app = express()

// 前端写完，打包在这里
app.use(express.static('./build'))

const BASE_PATH = '../yolo_detection/result/'

// 处理前端的get请求
app.get('/yolo', (req, res, next) => {
    fs.promises.readFile(path.join(BASE_PATH, 'results.json'), {
        encoding: 'utf-8'
    }).then(data => {
        // 获取到时间戳和图片
        const timeAndImg = JSON.parse(data);
        if (timeAndImg && timeAndImg.timestamp.length) {
            const imgPaths = timeAndImg.path.slice(-100).reverse()

            let imagesToFront = imgPaths.map(imagePath => {
                return imageToBase64(path.join(BASE_PATH, imagePath))
            });
            res.json({imagesToFront})

        } else {
            res.write('暂无人员检测')
            res.end();
        }

    }).catch(err => {
        console.log("发生了错误:", err)

        res.end();
    })
})

// 处理前端的get请求
app.get('/timeline', (req, res, next) => {
    fs.promises.readFile(path.join(BASE_PATH, 'timeline.json'), {
        encoding: 'utf-8'
    }).then(data => {
        // 获取到时间戳和图片
        const timeAndImg = JSON.parse(data);
        if (timeAndImg && timeAndImg.timestamp.length) {
            const imgPaths = timeAndImg.path.slice(-100).reverse()

            let imagesToFront = imgPaths.map(imagePath => {
                return imageToBase64(path.join(BASE_PATH, imagePath))
            });
            res.json({imagesToFront})

        } else {
            res.write('暂无人员检测')
            res.end();
        }

    }).catch(err => {
        console.log("发生了错误:", err)

        res.end();
    })
})

function imageToBase64(path) {
    const image = fs.readFileSync(path);
    return Buffer.from(image).toString('base64');
}

app.listen(9000, () => {
    console.log('express服务启动')
})