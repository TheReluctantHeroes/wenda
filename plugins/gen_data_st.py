
from langchain.embeddings import HuggingFaceEmbeddings
import re
import os,sys
os.chdir(sys.path[0][:-8])
from langchain.vectorstores.faiss import FAISS
from langchain.document_loaders import DirectoryLoader
from langchain.text_splitter import TokenTextSplitter, CharacterTextSplitter
import sentence_transformers

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


from settings import settings
source_folder = settings.library.st.Path
target_folder = source_folder + '_out'
source_folder_path = os.path.join(os.getcwd(), source_folder)
target_folder_path = os.path.join(os.getcwd(), target_folder)

if not os.path.exists(target_folder_path):
    os.mkdir(target_folder_path)

root_path_list = source_folder_path.split(os.sep)

print("预处理数据")
for root, dirs, files in os.walk(source_folder_path):
    path_list = root.split(os.sep)
    for file in files:
        try:
            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding='utf-16') as f:
                data = f.read()
        except:
            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding='utf-8') as f:
                data = f.read()
        data = re.sub(r'！', "！\n", data)
        data = re.sub(r'：', "：\n", data)
        data = re.sub(r'。', "。\n", data)
        data = re.sub(r'\n+', "\n", data)
        filename_prefix_list = [
            item for item in path_list if item not in root_path_list]
        file_name_prefix = '_'.join(x for x in filename_prefix_list if x)
        cut_file_name = file_name_prefix + '_' + file if file_name_prefix else file
        cut_file_path = os.path.join(target_folder_path, cut_file_name)
        with open(cut_file_path, 'w', encoding='utf-8') as f:
            f.write(data)
            f.close()

loader = DirectoryLoader(target_folder, glob='**/*.txt')
docs = loader.load()
# text_splitter = TokenTextSplitter(chunk_size=500, chunk_overlap=15)
text_splitter = CharacterTextSplitter(
    chunk_size=int(settings.library.st.Size), chunk_overlap=int(settings.library.st.Overlap), separator='\n')
doc_texts = text_splitter.split_documents(docs)
# print(doc_texts)
embeddings = HuggingFaceEmbeddings(model_name='')
embeddings.client = sentence_transformers.SentenceTransformer('model/text2vec-large-chinese',
                                                                           device='cuda')
print("开始处理数据")
vectorstore = FAISS.from_documents(doc_texts, embeddings)
print("处理完成")
vectorstore.save_local('vectorstore_path')
print("保存完成")
