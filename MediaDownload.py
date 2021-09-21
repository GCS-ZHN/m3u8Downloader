# License: Apache 2.0
# Author: Zhang.H.N
# Email: zhang.h.n@foxmail.com
# Created: 2021-09-21
# Version: 1.0

import os
import threading
import requests
import shutil
import time
import argparse
import urllib.parse as urlparse

from typing import Iterable
from concurrent.futures import ThreadPoolExecutor

from Crypto.Cipher import AES

def asyn(func):
    """异步方法的装饰器"""
    threadPool=ThreadPoolExecutor(20)
    def asynFunc(*args, **kwargs):
        threadPool.submit(func, *args, **kwargs)
    return asynFunc

class MediaDownloader(object):
    """通用媒体下载器的抽象实现，便于多种媒体扩展实现"""
    def download(self):
        pass

class M3u8MediaDownloader(MediaDownloader):
    """
    下载经过AES加密的m3u8视频，支持从文件或URL指定m2u8数据源，支持广告流过滤
    如果m3u8源自文件输入，要求ts的URL必须是完整URL而不是相对路径。
    如果m3u8源自网络URL，那么支持ts的相对路径
    """
    def __init__(self, m3u8Source:str, adFilter=True, headers:dict=None) -> None:
        """
        创建m3u8视频流下载器

        Args:
            m3u8File 要下载的m3u8视频流输入文件
            adFilter 是否过滤多视频流的广告
            headers  自定义请求头的字典
        """
        self.__mediaSeq=None
        self.__keyCache=dict()
        self.__adFilter=adFilter
        self.__aesList=list()
        self.__lock=threading.Lock()
        self.__process=0
        self.__running=0
        self.__targetList = []

        self.__headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests':'1'
        }
        if isinstance(headers, dict):
            self.__headers.update(headers)

        urlResult = urlparse.urlparse(m3u8Source)
        if urlResult.scheme:
            print("Load m3u8 from web...")
            self.__isUrl=True
            self.__m3u8Source=m3u8Source
            self.loadFromWeb(m3u8Source)
            path=urlResult.path
            tmp=urlResult.path.replace("/","_").replace(".m3u8","")
            if len(tmp)>30:
                tmp=tmp[:30]
            self.__tmpDir="_".join((
                urlResult.hostname,
                tmp,
                "tmp"))
        else:
            print("Load m3u8 from file...")
            self.__isUrl=False
            self.loadFromFile(m3u8Source)
            self.__tmpDir = m3u8Source.replace(".m3u8","")+"_tmp"
        
        if os.path.isdir(self.__tmpDir):
            shutil.rmtree(self.__tmpDir)
        os.mkdir(self.__tmpDir)

    def loadFromWeb(self, m3u8Url:str) -> None:
        """
        从web获取m3u8文件并解析

        Args:
            m3u8Url 目标视频的m3u8文件地址
        """
        response = self.__httpGet(m3u8Url, timeout=200)
        if response==None:
            print(f"Fail get {m3u8Url}")
            return
        self.__loadM3U8(response.text.splitlines(False))
        

    def loadFromFile(self, m3u8File:str) -> None:
        """
        加载指定的m3u8文件，若文件内视频流地址是相对地址，建议
        改用loadFromFile从网络加载，或者手动修改相对地址为完整url

        Args:
            m3u8File 要加载的m3u8文件
        """
        if not m3u8File.endswith(".m3u8"):
            m3u8File+=".m3u8"

        with open(m3u8File, mode="rt", encoding="UTF-8") as m3u8:
            self.__loadM3U8(m3u8)
    
    def __loadM3U8(self, m3u8:Iterable[str]):
        """
        从m3u8迭代对象加载m3u8配置

        Args:
            m3u8 可迭代的m3u8配置对象
        """
        isTarget=False  # 是否为数据流url
        isAd=False      # 是否为广告流
        firstAES=None   # 多数据流的第一个AES加密方式
        adCount=0      # 广告数量
        for line in m3u8:
            line = line.replace("\n","")

            # 该行是媒体序列ID
            if line.startswith("#EXT-X-MEDIA-SEQUENCE"):
                self.__mediaSeq=line.split(":")[1]
            
            # 该行是AES加密
            if line.startswith("#EXT-X-KEY"):
                if firstAES == None:
                    firstAES=line
                ## 根据加密方式变化判断是否为广告
                if line != firstAES and self.__adFilter:
                    isAd=True
                    adCount+=1
                    continue
                else:
                    isAd=False

                authDict = dict()
                for attrPair in line.replace("#EXT-X-KEY:","").split(","):
                    name,value=attrPair.split("=")
                    if name=="METHOD" and value=="NONE":
                        authDict.clear()
                        break
                    if name=="URI":
                        authDict["key"]=self.__getKey(eval(value))
                    if name=="IV":
                        authDict["iv"]=value
                self.__aesList.append(authDict)
                continue

            #下一行是视频流
            if line.startswith("#EXTINF"):
                isTarget=True
                continue

            #该行是视频流但不是广告
            if isTarget and not isAd:
                targetUrl=line
                if self.__isUrl:
                    targetUrl=urlparse.urljoin(self.__m3u8Source,line)
                # url 加密方式
                self.__targetList.append((targetUrl, len(self.__aesList)-1))
                isTarget=False
                continue
        
        print(f"m3u8 loaded with {len(self.__targetList)} ts fragment found and filter {adCount} advertisement")

    @asyn
    def __getTSFragment(self, idx:int)->None:
        """
        异步获取指定的ts碎片并缓存

        Args:
            idx      缓存索引
        """
        self.__running+=1
        times=3
        message=None
        while times>0:
            times-=1
            try:
                # TS数据获取
                url,aesIdx=self.__targetList[idx]
                response = self.__httpGet(url, timeout=100)
                if response==None:
                    raise requests.RequestException(f"Get ts fragment failed")
                data = response.content

                # 数据解密
                if aesIdx>=0 and self.__aesList[aesIdx]:
                    key = self.__aesList[aesIdx]["key"]
                    if "iv" in self.__aesList[aesIdx]:
                        iv=self.__aesList[aesIdx]["iv"]
                    else:
                        iv="{:0>16s}".format(self.__mediaSeq)
                    data = self.decrypt(key, iv, data)
                if data==None:
                    raise requests.RequestException("Invalid data")

                # 数据缓存，选择缓存而不选择合并是防止中途断网和内存过大
                with open(f"{self.__tmpDir}/{idx}.ts", mode="wb") as output:
                    output.write(data)

                self.__process+=1

                # 进度输出
                tmpUrl=url
                if len(tmpUrl)>80:
                    tmpUrl=url[:40]+"*****"+url[-20:]
                message="\rProcess: {:0>4d}/{:0>4d}  {:>100s}".format(
                    self.__process,
                    len(self.__targetList),
                    tmpUrl)
                break
            except requests.RequestException as e:
                message=f"\n{e}, idx: {idx} url: {url}\n"
                time.sleep(1)
        with self.__lock:
            print(message, end="")
        self.__running-=1

    def __joinTSFragment(self, filename:str)->None:
        """
        将缓存的TS碎片拼接为完整的视频

        Args:
            filename 保存的mp4文件名，相对或绝对路径
        """
        if not os.path.exists(self.__tmpDir):
            print("No fragment cache found!")
            return
        
        # 创建保存目录
        dirname = os.path.dirname(filename)
        if not dirname:
            dirname = "."
        if os.path.isfile(dirname):
            shutil.rmtree(dirname)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        # ts拼接后直接改尾缀为mp4就可以，或许道理同mol和sdf分子文件格式
        if not filename.endswith(".mp4"):
            filename += ".mp4"
        
        # 核验数量是否一致
        TSlist=os.listdir(self.__tmpDir)
        miss=len(self.__targetList)-len(TSlist)
        if miss>0:
            print(f"Warning: {miss} ts fragment missing...")

        # 开始合并转为mp4
        with open(filename, mode="wb") as outputfile:
            for idx in range(len(self.__targetList)):
                # 跳过缺失片段
                tmpFilename=f"{self.__tmpDir}/{idx}.ts"
                if not os.path.exists(tmpFilename):
                    continue

                with open(tmpFilename, mode="rb") as inputfile:
                    data=inputfile.read()
                    outputfile.write(data)
                    outputfile.flush()
        
        print(f"Saved to {filename}")

    def download(self, filename:str)->None:
        """
        开始下载视频流

        Args:
            filename 下载保存的mp4相对或绝对文件名
        """
        # 检查解析m3u8情况
        if not self.__targetList:
            print("m3u8 file not loaded, exit")
            return

        # 开始下载TS片段
        print("Try to get TS fragment...")
        for idx in range(len(self.__targetList)):
            self.__getTSFragment(idx)
        
        # 等待所有下载线程执行完毕
        while self.__running>0:
            time.sleep(1)

        # 开始合并转为mp4
        print("\nTry to join TS fragment...")
        self.__joinTSFragment(filename)

        # 清理缓存
        print("Clean cache file...")
        shutil.rmtree(self.__tmpDir)

    def __httpGet(self, url:str, **kwargs)->requests.Response:
        """
        内部通用的http GET请求，暂不支持自动重定向

        Args:
            url  请求的目标URL
        """
        response=requests.get(url, headers=self.__headers, **kwargs)
        if response.status_code>=300:
            print(f"Error, HTTP status code {response.status_code}")
            return
        return response

    def __getKey(self, url:str)->str:
        """
        获取m3u8指定的AES加密key值，一旦获取失败，会退出程序，因为后续解码必然错误而没必要运行

        Args:
            url   AES key的URL
        
        Returns:
            获得的key值
        """
        if url in self.__keyCache:
            return self.__keyCache[url]
        
        print(f"Try to get key from {url}")
        response=self.__httpGet(url)
        if response==None:
            print(f"Get key from {url} failed, exit.")
            exit(1)
        self.__keyCache[url]=response.text
        return response.text
    
    @staticmethod
    def decrypt(key:str, iv:str, data:bytes)->bytes:
        """
        进行AES解密

        Args:
            key   16/32/64字节的AES密钥字符串
            iv    16字节的AES的iv值
            data  待解码数据，必须是16字节的倍数

        Return:
            解码后的bytes数据
        """
        try:
            key = bytes(key, encoding="utf8")
            iv = bytes(iv, encoding="utf8")
            cryptor=AES.new(key, AES.MODE_CBC, iv)
            return cryptor.decrypt(data)
        except ValueError:
            return None

if __name__ == "__main__":
    try:
        parser  = argparse.ArgumentParser("该脚本用于下载m3u8视频流")  
        parser.add_argument("--input", default="index", type=str, help="m3u8输入文件或URL")
        parser.add_argument("--output", default="index", type=str, help="下载保存的mp4文件名")
        parser.add_argument("--referer", default=None, type=str, help="自定义Referer请求头，部分网站基于它反爬")
        parser.add_argument("--adfilter", action="store_true", help="是否过滤内插广告流")
        args = parser.parse_args()
        headers={"Referer":args.referer} if args.referer!=None else None
        md = M3u8MediaDownloader(args.input, headers=headers, adFilter=args.adfilter)
        md.download(args.output)
    except Exception as e:
        print(e)
