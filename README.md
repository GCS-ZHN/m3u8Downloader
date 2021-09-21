
# 一、背景知识--HLS
HTTP Live Streaming（缩写是HLS）是一个由苹果公司提出的基于HTTP的流媒体网络传输协议。​是苹果公司QuickTime X和iPhone软件系统的一部分。 它的工作原理是把整个流分成一个个小的基于HTTP的文件来下载，每次只下载一些。当媒体流正在播放时，客户端可以选择从许多不同的备用源中以不同的速率下载同样的资源，允许流媒体会话适应不同的数据速率。

在开始一个流媒体会话时，客户端会下载一个包含元数据的extended M3U (m3u8)playlist文件，用于寻找可用的媒体流。HLS只请求基本的HTTP报文，与实时传输协议（RTP)不同，HLS可以穿过任何允许HTTP数据通过的防火墙或者代理服务器。​它也很容易使用内容分发网络来传输媒体流。

# 二、项目功能

基于提供的m3u8清单文件，将视频下载、解密并合成为mp4文件。适用于采用HLS的视频网站，在没有直接提供下载方式的免费视频进行下载。在网速较慢在线体验不佳，但又没下载按钮时，是否适用。

## 2.1 安装
克隆本项目到本地，`pip install -r requirements.txt`安装依赖包，最后

    python MediaDownload.py --input <你的m3u8清单文件> --output <你的mp4输出文件>

脚本提供了以下几个参数，可以`python MediaDownload.py --help`查看。

    usage: 该脚本用于下载m3u8视频流 [-h] [--input INPUT] [--output OUTPUT] [--referer REFERER] [--adfilter]

    optional arguments:
    -h, --help         show this help message and exit
    --input INPUT      m3u8输入文件或URL
    --output OUTPUT    下载保存的mp4文件名
    --referer REFERER  自定义Referer请求头，部分网站基于它反爬
    --adfilter         是否过滤内插广告流

其中加入`--adfilter`参数，会将视频里面其他解码方式的视频作为广告而过滤，因为广告与正文往往不同视频流。

例如：

    python MediaDownload.py --input https://***/v.m3u8 --output movie/test.mp4 --adfilter

## 2.2 m3u8文件来源
该文件的URL不是视频网页的地址URL，需要通过F12开发者工具的网络选项进行查看，相信爬虫学习者有这点网络知识基础。值得说的，--input参数默认是当前文件夹下的index.m3u8文件。该参数可以是URL也可以是本地文件地址，推荐使用URL，因为m3u8内部的视频地址可能是相对地址。

# 三、提醒
该工具属于爬虫工具，仅供学习交流使用，非法传播视频或构成侵权。不同网站或有不同的反爬机制，例如某网站会要求指定的“Referer”请求头来区分请求，需要--referer参数手动指定。因此对于不同网站，脚本可能不一定生效，有兴趣请自行修改脚本。