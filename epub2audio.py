import os
import sys
import shutil
from pathlib import Path
from rich.console import Console
from rich.prompt import IntPrompt
from rich.prompt import Prompt
from rich.prompt import Confirm
from tts import *
from epub2txt import *
from multiprocessing import Pool
import multiprocessing
import argparse
import ssl
import re
import glob
from pathlib import Path
from pydub import AudioSegment

# 关闭SSL证书验证
ssl._create_default_https_context = ssl._create_unverified_context

console = Console()

def main(原始TXT文件名, output):
    with open(原始TXT文件名,'r',encoding='utf-8') as f:
        原始TXT内容 = f.read()
    内容列表 = 原始TXT内容.split("\n\n")
    内容列表 = [x for x in 内容列表 if x]
    拆分内容列表 = []
    p = 0
    q = ""
    r = 0
    for i in 内容列表:
        if p <= 8:
            q = q + i + " <break time=\"600ms\" /> "
        else:
            q = q + i + " <break time=\"600ms\" /> "
            拆分内容列表.append(str(r) + "@--&" + q)
            p = 0
            q = ""
            r += 1
        p += 1
    
    if len(拆分内容列表) == 0:
        try:
            shutil.rmtree("output")
        except:
            pass
        return
    try:
        os.mkdir("output")
    except:
        pass
    进程池 = Pool(16)
    进程池.map(下载音频, 拆分内容列表)
    
    console.print("开始合并音频!")
    files = glob.glob("output/*.mp3")
    files.sort(key=lambda x: int(x[7:-4]))
    try:
        Path(os.path.dirname(output)).mkdir(parents=True, exist_ok=True)
    except Exception:
        raise Exception("Could not create output path.")
    merged = AudioSegment.empty()
    fConcat = list()
    for f in files:
        name = AudioSegment.from_mp3(f)
        fConcat.extend([name])
    for f in fConcat:
        merged += f
    merged.export(output, format="mp3")
    console.print("完成!")
    shutil.rmtree("output")

def 下载音频(text):
    tmp = text.split("@--&")
    编号 = tmp[0]
    内容 = tmp[1]
    try:
        内容 = 内容.replace(str(re.search( r'\!\[\]\(.*\)', 内容, re.M|re.I).group()), "")
    except:
        pass
    try:
        内容 = 内容.replace("\\\\", "")
    except:
        pass
    try:
        def 替换(repl):
            content = " <prosody pitch=\"high\"> "+str(repl.group(0))+" </prosody> "
            return content
        内容 = re.sub(r'「.*?」', 替换, 内容)
        try:
            内容 = re.sub(r'“.*?”', 替换, 内容)
        except:
            pass
        try:
            内容 = re.sub(r'【.*?】', 替换, 内容)
        except:
            pass
    except:
        pass

    try:
        def 替换(repl):
            content = " <break time=\"600ms\" /> <prosody pitch=\"low\"> "+str(repl.group(0))+" </prosody> "
            return content
        内容 = re.sub(r'（.*?）', 替换, 内容)
    except:
        pass

    console.print(内容)
    SSML文本 = f"""
<speak xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" xmlns:emo="http://www.w3.org/2009/10/emotionml" version="1.0" xml:lang="en-US">
    <voice name="zh-CN-XiaoxuanNeural">
    <mstts:express-as style="depressed">
        <prosody rate="-3%" pitch="0%">
        {内容}
        </prosody>
    </mstts:express-as>
    </voice>
</speak>
        """
    
    for i in range(11):
        if i >= 10:
            console.print("[red]错误次数过多!已终止运行!")
            os._exit(0)
        try:
            asyncio.get_event_loop().run_until_complete(mainSeq(SSML文本, "output/" + str(编号)))
        except:
            console.print(f"第{i + 1}次请求失败,编号{编号},正在重试...")
            time.sleep(3)
        else:
            break
    console.print(f"第{编号}个内容完成!")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        shutil.rmtree("chapters")
        shutil.rmtree("output")
    except:
        pass
    if len(sys.argv) == 2:
        path = sys.argv[1]
    else:
        if Confirm.ask("您未输入任何参数,请选择一个操作 进入交互模式[Y] 查看命令帮助[N] "):
            path = str(Prompt.ask("请输入Epub文件路径 "))
        else:
            console.print("\n1. 请于命令行中进入到本项目路径\n2. 执行 pip3 install -r requirements.txt\n3. 执行 python3 epub2audio.py EpubFilePath \n4. EpubFilePath替换为Epub文件路径")
            os._exit(0)
    文件名 = Path(path).name.replace("\'", "").replace("\"", "").replace("\\ ", " ").split(".")[-2]
    
    epub_to_txt(str(Path(path).name).replace("\'", "").replace("\"", "").replace("\\ ", " "),
                file_dir=str(Path(path).parent).replace("\'", "").replace("\"", "").replace("\\ ", " "),
                output_file_dir=".",
                chapter_files_dir=None,
                debug=False,
                dry_run=False)
    TXT文件 = glob.glob("chapters/*.txt")
    TXT文件.sort(key=lambda x: int(x[9:-4]))
    r = -1
    try:
        os.mkdir(文件名)
    except:
        pass
    for i in TXT文件:
        r += 1
        main(i, 文件名+"/"+str(r).zfill(3)+".mp3")
    os.remove(文件名+".txt")
    # os.remove(文件名+"/000.mp3")
    shutil.rmtree("chapters")