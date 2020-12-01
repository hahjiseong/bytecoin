# system packages

from bs4 import BeautifulSoup
import numpy as np
import requests
import pandas as pd
from fake_useragent import UserAgent
import json
from multiprocessing import Process,Pool
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
import time
import csv
import torch
from transformers import BertTokenizer
from transformers import BertForSequenceClassification, AdamW, BertConfig
from transformers import get_linear_schedule_with_warmup
from torch.utils.data import TensorDataset,DataLoader,RandomSampler,SequentialSampler
from keras_preprocessing.sequence import pad_sequences
from sklearn.model_selection import train_test_split
import tensorflow as tf
import pandas as pd
import numpy as np
import random
import time
import datetime
import os
import argparse
import matplotlib.pyplot as plt
import random
# crawler packages
from urltools import get_query
from mongodb import get_db
from stock_sources import NAVER
from errors import DateNotInRangeException, HTMLElementNotFoundException
import os
from stocks_crawler import get_stocks
from posts_crawler_Hahversion1 import NaverCrawler
# constants

from bert_classificaion_main import Bert_classification

how_old = 10

class multicrawl_and_return():
    def __init__(self,num_pages=1,days=0,hours=0,minutes=10,num_process=multiprocessing.cpu_count(),multiprocessing_flag=True,num_thread=5,MAX_LEN=65,epoch=1,batch_size=32):

        self.date = datetime.datetime.now() - datetime.timedelta(days=days,hours=hours,minutes=minutes)
        self.MAX_LEN = MAX_LEN
        self.epoch = epoch
        self.batch_size = batch_size

        self.num_process = num_process
        self.num_pages = num_pages
        self.num_thread = num_thread
        self.multiprocessing_flag = multiprocessing_flag

        self.stock_code_lst = get_stocks()
        self.crawl_lst = self.make_crawl_lst()

        self.model = NaverCrawler()
    def make_crawl_lst(self):
        temp_crawl_lst = []
        for i in range(len(self.stock_code_lst)):
            temp_crawl_lst.append(self.stock_code_lst[i]['code'])

        crawl_lst = []
        for i in temp_crawl_lst:
            crawl_lst += [[i,self.num_pages,self.date,self.multiprocessing_flag,self.num_thread]]

        return crawl_lst

    def multi_crawl_and_filter2longsent(self):
        print('start crawling...')
        g = time.time()
        p = Pool()
        p.starmap(self.model.crawl, self.crawl_lst[:])
        p.close()
        p.join()
        gr = time.time()
        print('lengh of nc.result is :       ', len(self.model.result))
        # for i in nc.result:
        # print('title is :',type(i['title']),'content is : ',type(i['content']))
        print(f'time spent when {self.num_process} proceesse and {self.num_thread} thread per process for '
              f'{len(self.stock_code_lst)} jobs and {self.num_pages} pages per job : {gr - g}')

        filtered_data = self.model.remove_2longsent()

        #flush result
        self.model.flush_result()

        self.model.result = filtered_data

        return self.model.result

    def content_extraction(self):
        contents_extracted_lst = []
        total_content_data = self.multi_crawl_and_filter2longsent()
        for id_x, i in enumerate(total_content_data):
            contents_extracted_lst.append(i['title'] + ' ' + i['content'])

        return contents_extracted_lst

    def get_label_lst(self):
        contents_extracted_lst = self.content_extraction()

        # BERT의 입력 형식에 맞게 변환
        sentences = ["[CLS] " + str(sentence) + " [SEP]" for sentence in contents_extracted_lst]
        # BERT의 토크나이저로 문장을 토큰으로 분리
        tokenizer = BertTokenizer.from_pretrained('bert-base-multilingual-cased', do_lower_case=False)
        tokenized_texts = [tokenizer.tokenize(sent) for sent in sentences]
        print(sentences[0])
        print(tokenized_texts[0])
        # 토큰을 숫자 인덱스로 변환
        input_ids = [tokenizer.convert_tokens_to_ids(x) for x in tokenized_texts]

        # 문장을 MAX_LEN 길이에 맞게 자르고, 모자란 부분을 패딩 0으로 채움
        input_ids = pad_sequences(input_ids, maxlen=self.MAX_LEN, dtype="long", truncating="post",
                                  padding="post")
        bert = Bert_classification(self.epoch, self.batch_size)
        label_lst = bert.work(input_ids)

        return label_lst

    def combine_label_and_contents_lst(self):
        label_lst = self.get_label_lst()
        contents_lst = self.model.result
        for id_x,contents in enumerate(contents_lst):
            contents['label'] = label_lst[id_x]

        return contents_lst

    def save_result2db(self):
        contents_lst = self.combine_label_and_contents_lst()
        db = get_db()
        coll = db.stock
        coll.insert_many(contents_lst)

        self.model.flush_result()
        print('Saving files Completed!')
        doc = coll.find()
        for i in doc:
            print('is is : ',i)

a = multicrawl_and_return(batch_size=4)
b = a.save_result2db()
print(a.model.result)