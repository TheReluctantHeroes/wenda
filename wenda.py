import torch
import threading
import os
import json
import datetime
from bottle import route, response, request, static_file, hook
import bottle
import argparse
parser = argparse.ArgumentParser(description='Wenda config')
parser.add_argument('-c', type=str, dest="Config", default='config.xml', help="配置文件")
parser.add_argument('-p', type=int, dest="Port", help="使用端口号")
parser.add_argument('-l', type=bool, dest="Logging", help="是否开启日志")
parser.add_argument('-t', type=str, dest="LLM_Type", choices=["rwkv", "glm6b", "llama"], help="选择使用的大模型")
args = parser.parse_args()
print(args)
os.environ['wenda_'+'Config'] = args.Config 
os.environ['wenda_'+'Port'] = str(args.Port)
os.environ['wenda_'+'Logging'] = str(args.Logging)
os.environ['wenda_'+'LLM_Type'] = str(args.LLM_Type) 

from plugins.settings import settings 


def load_LLM():
    try:
        from importlib import import_module
        LLM = import_module('plugins.llm_'+settings.LLM_Type)
        return LLM
    except Exception as e:
        print("LLM模型加载失败，请阅读说明：https://github.com/l15y/wenda", e)


LLM = load_LLM()
Logging=bool(settings.Logging == 'True')
if Logging:
    from plugins.defineSQL import session_maker, 记录
mutex = threading.Lock()


@route('/static/<path:path>')
def staticjs(path='-'):
    return static_file(path, root="views/static/")


@route('/:name')
def static(name='-'):
    return static_file(name, root="views")
from plugins.settings import xml2json,json2xml
import json
@route('/readconfig')
def readconfig():
    with open(os.environ['wenda_'+'Config'],encoding = "utf-8") as f:
        j=xml2json(f.read(),True,1,1)
        # print(j)
        return json.dumps(j)
@route('/writeconfig', method='POST')
def readconfig():
    data = request.json
    s=json2xml(data).decode("utf-8")
    with open(os.environ['wenda_'+'Config']+"_",'w',encoding = "utf-8") as f:
        f.write(s)
        # print(j)
        return s
# @route('/readxml')
# def readxml():
#     with open(os.environ['wenda_'+'Config'],encoding = "utf-8") as f:
#         return f.read()
@route('/plugins')
def read_auto_plugins():
    response.set_header("Pragma", "no-cache")
    response.add_header("Cache-Control", "must-revalidate")
    response.add_header("Cache-Control", "no-cache")
    response.add_header("Cache-Control", "no-store")
    plugins=[]
    for root, dirs, files in os.walk("views/plugins"):
        for file in files:
            if(file.endswith(".js")):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding='utf-8') as f:
                    plugins.append( f.read())
    return "\n".join(plugins)
# @route('/writexml', method='POST')
# def writexml():
    # data = request.json
    # s=json2xml(data).decode("utf-8")
    # with open(os.environ['wenda_'+'Config']+"_",'w',encoding = "utf-8") as f:
    #     f.write(s)
    #     # print(j)
    #     return s


@route('/')
def index():
    response.set_header("Pragma", "no-cache")
    response.add_header("Cache-Control", "must-revalidate")
    response.add_header("Cache-Control", "no-cache")
    response.add_header("Cache-Control", "no-store")
    return static_file("index.html", root="views")


当前用户 = None

@route('/api/chat_now', method='GET')
def api_chat_now():
    response.set_header("Pragma", "no-cache")
    response.add_header("Cache-Control", "must-revalidate")
    response.add_header("Cache-Control", "no-cache")
    response.add_header("Cache-Control", "no-store")
    return '当前状态：'+当前用户[0]


@hook('before_request')
def validate():
    REQUEST_METHOD = request.environ.get('REQUEST_METHOD')
    HTTP_ACCESS_CONTROL_REQUEST_METHOD = request.environ.get(
        'HTTP_ACCESS_CONTROL_REQUEST_METHOD')
    if REQUEST_METHOD == 'OPTIONS' and HTTP_ACCESS_CONTROL_REQUEST_METHOD:
        request.environ['REQUEST_METHOD'] = HTTP_ACCESS_CONTROL_REQUEST_METHOD


@route('/api/save_news', method='OPTIONS')
@route('/api/save_news', method='POST')
def api_chat_stream():
    response.set_header('Access-Control-Allow-Origin', '*')
    response.add_header('Access-Control-Allow-Methods', 'POST,OPTIONS')
    response.add_header('Access-Control-Allow-Headers',
                        'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token')
    try:
        data = request.json
        if not data:
            return '0'
        title = data.get('title')
        txt = data.get('txt')
        cut_file = f"txt/{title}.txt"
        with open(cut_file, 'w', encoding='utf-8') as f:
            f.write(txt)
            f.close()
        return '1'
    except Exception as e:
        print(e)
    return '2'


@route('/api/find', method='POST')
def api_find():
    data = request.json
    prompt = data.get('prompt')
    return json.dumps(zhishiku.find(prompt))


@route('/chat/completions', method='POST')
def api_chat_box():
    response.content_type = "text/event-stream"
    response.add_header("Connection", "keep-alive")
    response.add_header("Cache-Control", "no-cache")
    data = request.json
    max_length = data.get('max_tokens')
    if max_length is None:
        max_length = 2048
    top_p = data.get('top_p')
    if top_p is None:
        top_p = 0.2
    temperature = data.get('temperature')
    if temperature is None:
        temperature = 0.8
    use_zhishiku = data.get('zhishiku')
    if use_zhishiku is None:
        use_zhishiku = False
    messages = data.get('messages')
    prompt = messages[-1]['content']
    # print(messages)
    history_formatted = LLM.chat_init(messages)
    response_text = ''
    # print(request.environ)
    IP = request.environ.get(
        'HTTP_X_REAL_IP') or request.environ.get('REMOTE_ADDR')
    global 当前用户
    error = ""
    with mutex:
        yield "data: %s\n\n" %json.dumps({"response": (str(len(prompt))+'字正在计算')})

        print("\033[1;32m"+IP+":\033[1;31m"+prompt+"\033[1;37m")
        try:
            for response_text in LLM.chat_one(prompt, history_formatted, max_length, top_p, temperature, zhishiku=use_zhishiku):
                if (response_text):
                    # yield "data: %s\n\n" %response_text
                    yield "data: %s\n\n" %json.dumps({"response": response_text})
            
            yield "data: %s\n\n" %"[DONE]"
        except Exception as e:
            error = str(e)
            print("错误", settings.red, error, settings.white)
            response_text = ''
        torch.cuda.empty_cache()
    if response_text == '':
        yield "data: %s\n\n" %json.dumps({"response": ("发生错误，正在重新加载模型"+error)})
        os._exit(0)
@route('/api/chat_stream', method='POST')
def api_chat_stream():
    data = request.json
    prompt = data.get('prompt')
    max_length = data.get('max_length')
    if max_length is None:
        max_length = 2048
    top_p = data.get('top_p')
    if top_p is None:
        top_p = 0.7
    temperature = data.get('temperature')
    if temperature is None:
        temperature = 0.9
    use_zhishiku = data.get('zhishiku')
    if use_zhishiku is None:
        use_zhishiku = False
    keyword = data.get('keyword')
    if keyword is None:
        keyword = prompt
    history = data.get('history')
    history_formatted = LLM.chat_init(history)
    response = ''
    # print(request.environ)
    IP = request.environ.get(
        'HTTP_X_REAL_IP') or request.environ.get('REMOTE_ADDR')
    global 当前用户
    error = ""
    footer = '///'
    yield str(len(prompt))+'字正在计算'
    if use_zhishiku:
        # print(keyword)
        response_d = zhishiku.find(keyword)
        output_sources = [i['title'] for i in response_d]
        results = '\n---\n'.join([i['content'] for i in response_d])
        prompt = 'system:学习以下文段, 用中文回答用户问题。如果无法从中得到答案，忽略文段内容并用中文回答用户问题。\n\n' + \
            results+'\nuser:'+prompt
        if bool(settings.library.Show_Soucre == 'True'):
            footer = "\n### 来源：\n"+('\n').join(output_sources)+'///'
    with mutex:

        yield footer

        print("\033[1;32m"+IP+":\033[1;31m"+prompt+"\033[1;37m")
        try:
            for response in LLM.chat_one(prompt, history_formatted, max_length, top_p, temperature, zhishiku=use_zhishiku):
                if (response):
                    yield response+footer
        except Exception as e:
            error = str(e)
            print("错误", settings.red, error, settings.white)
            response = ''
        torch.cuda.empty_cache()
    if response == '':
        yield "发生错误，正在重新加载模型"+error+'///'
        os._exit(0)
    if Logging:
        with session_maker() as session:
            jl = 记录(时间=datetime.datetime.now(), IP=IP, 问=prompt, 答=response)
            session.add(jl)
            session.commit()
    print(response)
    yield "/././"


model = None
tokenizer = None


def load_model():
    global 当前用户
    mutex.acquire()
    当前用户 = ['模型加载中', '', '']
    LLM.load_model()
    mutex.release()
    torch.cuda.empty_cache()
    print(settings.green, "模型加载完成", settings.white)


thread_load_model = threading.Thread(target=load_model)
thread_load_model.start()
zhishiku = None

def load_zsk():
    try:
        from importlib import import_module
        global zhishiku
        zhishiku = import_module('plugins.zhishiku_'+settings.library.Type)
        print(settings.green, "知识库加载完成", settings.white)
    except Exception as e:
        print("知识库加载失败，请阅读说明：https://github.com/l15y/wenda",e)

thread_load_zsk = threading.Thread(target=load_zsk)
thread_load_zsk.start()
bottle.debug(True)
bottle.run(server='paste', host="0.0.0.0", port=settings.Port, quiet=True)
