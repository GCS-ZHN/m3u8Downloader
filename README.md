<h1 style="text-align: center">HLS --M3U8流媒体视频下载</h1>
<div style="text-align: center">

![AUR](https://img.shields.io/badge/license-Apache%20License%202.0-blue.svg)
![star](https://gitee.com/GCSZHN/m3u8Downloader/badge/star.svg?theme=white)
![GitHub stars](https://img.shields.io/github/stars/GCS-ZHN/m3u8Downloader.svg?style=social&label=Stars)
![GitHub forks](https://img.shields.io/github/forks/GCS-ZHN/m3u8Downloader.svg?style=social&label=Fork)

</div>

# 一、背景知识--HLS
HTTP Live Streaming（缩写是HLS）是一个由苹果公司提出的基于HTTP的流媒体网络传输协议。​是苹果公司QuickTime X和iPhone软件系统的一部分。 它的工作原理是把整个流分成一个个小的基于HTTP的文件来下载，每次只下载一些。当媒体流正在播放时，客户端可以选择从许多不同的备用源中以不同的速率下载同样的资源，允许流媒体会话适应不同的数据速率。

在开始一个流媒体会话时，客户端会下载一个包含元数据的extended M3U (m3u8)playlist文件，用于寻找可用的媒体流。HLS只请求基本的HTTP报文，与实时传输协议（RTP)不同，HLS可以穿过任何允许HTTP数据通过的防火墙或者代理服务器。​它也很容易使用内容分发网络来传输媒体流。例如项目中附带的index.m3u8就是一个清单文件示例。

# 二、项目功能

基于指定的m3u8清单文件，将视频下载、解密并合成单一的ts视频文件。适用于采用HLS的视频网站，在没有直接提供下载方式的免费视频进行下载。在网速较慢在线体验不佳，但又没下载按钮时，是否适用。

## 2.1 安装与使用
克隆本项目到本地，`pip install -r requirements.txt`安装依赖包，最后
```shell
python MediaDownload.py <你的m3u8清单文件> <你的ts输出文件>
```
脚本提供了以下几个参数，可以`python MediaDownload.py --help`查看。
```
usage: 该脚本用于下载m3u8视频流 [-h] [--referer REFERER] [--adfilter] input output

positional arguments:
  input                       m3u8输入文件或URL
  output                    下载保存的mp4文件名

optional arguments:
  -h, --help                show this help message and exit
  --referer REFERER   自定义Referer请求头，部分网站基于它反爬
  --adfilter                 是否过滤内插广告流
```
其中加入`--adfilter`参数，会将视频里面其他解码方式的视频作为广告而过滤，因为广告与正文往往不同视频流。

例如：
```shell
python MediaDownload.py https://***/v.m3u8 movie/test.ts --adfilter
```

## 2.2 m3u8文件来源
m3u8可以从本地文件或URL来输入

## 2.3 视频格式转码
推荐使用ffmpeg工具进行视频格式转码，本项目提供了windows版本的ffmpeg工具，以及linux和windows下将文件夹下ts视频转码为mp4的示例脚本`ts2mp4`。linux下需要事先安装ffmpeg工具。
```shell
sudo apt-get install ffmpeg
```
脚本使用方法：
- ts2mp4.bat： windows下，双击会将当前目录的ts格式文件转换为mp4格式文件
- ts2mp4.sh ：linux下，bash运行它，会将当前目录的ts转换。或者指定目录在命令后面。

### 指定本地文件输入
```shell
python MediaDownload.py /your/path/of/target.m3u8 /your/path/of/target.ts
```
本地输入的局限性在于，要求m3u8内的ts地址必须是完整的URL，因为本地路径不是URL，解析相对URL。

### 指定URL输入
```shell
python MediaDownload.py https://your/url/of/target.m3u8  /your/path/of/target.ts
```
推荐使用URL指定输入。 
# 三、提醒
该工具属于爬虫工具，仅供学习交流使用，非法传播视频或构成侵权。不同网站或有不同的反爬机制，例如某网站会要求指定的“Referer”请求头来区分请求，需要--referer参数手动指定。因此对于不同网站，脚本可能不一定生效，有兴趣请自行修改脚本。