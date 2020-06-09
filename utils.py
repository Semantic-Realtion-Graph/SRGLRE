import json
import os
import random
import logging
import torch
import numpy as np
from transformers import BertTokenizer, BertConfig, AlbertConfig, AlbertTokenizer, RobertaConfig, RobertaTokenizer
from sklearn.metrics import matthews_corrcoef, f1_score, classification_report, accuracy_score,precision_recall_fscore_support

#from data_loader import InputFeatures


from model import RBERT
from collections import Counter

MODEL_CLASSES = {
    'bert': (BertConfig, RBERT, BertTokenizer),
    'roberta': (RobertaConfig, RBERT, RobertaTokenizer),
    'albert': (AlbertConfig, RBERT, AlbertTokenizer)
}

MODEL_PATH_MAP = {
    'bert': 'bert-base-uncased',
    'roberta': 'roberta-base',
    'albert': 'albert-xxlarge-v1'
}

ADDITIONAL_SPECIAL_TOKENS = ["<e1>", "</e1>", "<e2>", "</e2>"]


def get_label(args):
    # get labels of dataset
    label_list = []
    for i in range(80):
        label_list.append(i)
    return label_list


def load_tokenizer(args):
    # load tokenizer from ALBERT.tokenizer
    tokenizer = MODEL_CLASSES[args.model_type][2].from_pretrained(args.model_name_or_path)
    tokenizer.add_special_tokens({"additional_special_tokens": ADDITIONAL_SPECIAL_TOKENS})
    return tokenizer


def write_prediction(args, output_file, preds):
    """
    For official evaluation script
    :param output_file: prediction_file_path (e.g. eval/proposed_answers.txt)
    :param preds: [0,1,0,2,18,...]
    """
    relation_labels = get_label(args)
    with open(output_file, 'w', encoding='utf-8') as f:
        for idx, pred in enumerate(preds):
            f.write("{}\t{}\n".format(8001 + idx, relation_labels[pred]))


def init_logger():
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s -   %(message)s',
                        datefmt='%m/%d/%Y %H:%M:%S',
                        level=logging.INFO)


def set_seed(args):
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if not args.no_cuda and torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)


def compute_metrics(task, preds, labels):
    '''
       compute acc and f1 from acc_and_f1()
       :param task: task of dataset
       :param preds: prediction
       :param labels: label
       '''
    assert len(preds) == len(labels)
    return acc_and_f1(task, preds, labels)


def simple_accuracy(preds, labels):
    # acc
    return (preds == labels).mean()


def acc_and_f1( preds, labels):
    '''
    the process of computing acc and f1
    :param task,preds,labels:
    :return: acc and f1
    '''
    average_acc, whole_acc=score(labels,preds)
    return {
        "average_acc": average_acc,
        "whole_acc": whole_acc,
    }


def score(key, prediction):
    '''
    Detailed steps of computing f1
    :param key: true labels
    :param prediction: predict labels
    :param no_relation: the id of "no_relation" or "other"
    :param class_num: number of classes
    :return: pre ,recall and f1
    '''
    correct_by_relation = Counter()
    guessed_by_relation = Counter()
    gold_by_relation = Counter()
    num_samples=[1078,1080,1085,1132,1082,1077,1056,1099,1090,1123]

    # Loop over the data to compute a score
    for row in range(len(key)):
        gold = key[row]
        guess = prediction[row]


        guessed_by_relation[guess] += 1
        gold_by_relation[gold] += 1
        if gold == guess:
            correct_by_relation[guess] += 1

    whole_acc = float(sum(correct_by_relation.values())) / float(sum(guessed_by_relation.values()))

    correct_by_relation_task = Counter()
    guessed_by_relation_task = Counter()

    for item in correct_by_relation.keys():
        correct_by_relation_task[int(item/8)]+=correct_by_relation[item]
        guessed_by_relation_task[int(item/8)]+=guessed_by_relation[item]
    average_acc=0
    for item in correct_by_relation_task.keys(): 
        average_acc += (correct_by_relation_task[item]/num_samples[item])
        #average_acc += (correct_by_relation_task[item]/guessed_by_relation[item])
       
    average_acc=average_acc/10
           
   
    return average_acc, whole_acc

def split_data(dataset,batch_size):
    length = len(dataset)
    new_data=[]
    start=0
    for i in range(length):
        if i>0 and i%batch_size==0:
            new_data.append(dataset[start:i])
            start=i
    if start<length-1:
        new_data.append(dataset[start:length-1])
        #if i==length-1:
         #   new_data.append(dataset[start:i+1])
         #   start=i
    return new_data




def load_entity_feature(entity_feature_file):
    '''
    load entity features from entity_feature_file
    :param entity_feature_file: path of entity feature file
    :return: entity features
    '''
    print("************* Loading entity_features ***************** ")
    entity_features={}
    try:
        file = open(entity_feature_file, "r")
        entity_features = json.load(file)
        file.close()
    except json.decoder.JSONDecodeError:
        print("%s is empty!"%entity_feature_file)
    except FileNotFoundError:
        open(entity_feature_file, mode='w')
        print("%s 文件创建成功！"%entity_feature_file)
    return entity_features



def write_entity_feature(entity_features, entity_feature_file):
    '''
        write entity features from entity_feature_file
        :param entity_feature_file: path of entity feature file
        :param: entity features: entity features
        '''
    print("************* Writing entity_features ***************** ")
    with open(entity_feature_file, 'w') as file:
        json.dump(entity_features, file)
    file.close()  # 关闭文件


def load_edge_feature(edge_feature_file):
    '''
    load edge features from edge_feature_file
    :param edge_feature_file: path of edge feature file
    :return: edge features
    '''
    print("************* Loading edge_features ***************** ")
    edge_feature={}
    try:
        file = open(edge_feature_file, "r")
        edge_feature = json.load(file)
        file.close()
    except json.decoder.JSONDecodeError:
        print("%s is empty!"%edge_feature_file)
    except FileNotFoundError:
        open(edge_feature_file, mode='w')
        print("%s 文件创建成功！"%edge_feature_file)
    return edge_feature


def write_edge_feature(edge_features, edge_feature_file):
    print("************* Writing edge_features ***************** ")
    with open(edge_feature_file, 'w') as file:
        json.dump(edge_features, file)
    file.close()  # 关闭文件


def load_graph(graph_file):
    '''
    load graph  from graph_file
    :param graph_file: path of graph file
    :return: graph (adjacency list for vertexs)
    '''
    print("************* Loading graph ***************** ")
    graph={}
    try:
        file = open(graph_file, "r")
        graph = json.load(file)
        file.close()
    except json.decoder.JSONDecodeError:
        print("%s is empty!"%graph_file)
    except FileNotFoundError:
        open(graph_file, mode='w')
        print("%s 文件创建成功！"%graph_file)
    return graph


def write_graph(graph, graph_file):
    '''
    write graph to graph_file
    :param graph,graph_file
    '''
    print("************* Writing graph ***************** ")
    with open(graph_file, 'w') as file:
        json.dump(graph, file)
    file.close()


def load_entity2id(entity2id_file):
    '''
    load the map of entity to id
    :param entity2id_file: entity to id file path
    :return:
    '''
    print("************* Loading entity2id ***************** ")
    entity2id={}
    try:
        file = open(entity2id_file, "r")
        entity2id = json.load(file)
        file.close()
    except json.decoder.JSONDecodeError:
        print("%s is empty!"%entity2id_file)
    except FileNotFoundError:
        open(entity2id_file, mode='w')
        print("%s 文件创建成功！"%entity2id_file)
    return entity2id


def write_entity2id(entity2id, dicts_file):
    print("************* Writing entity2id ***************** ")
    with open(dicts_file, 'w') as file:
        json.dump(entity2id, file)
    file.close()



def convert_inputs2InputFeatures(inputs, i):
    '''
    convert input(tensor) to InputFeatures
    '''
    import data_loader
    return data_loader.InputFeatures(input_ids=inputs["input_ids"][i].cpu().clone().detach().numpy().tolist(),
                          attention_mask=inputs["attention_mask"][i].cpu().clone().detach().numpy().tolist(),
                          token_type_ids=inputs["token_type_ids"][i].cpu().clone().detach().numpy().tolist(),
                          false_labels=inputs["false_labels"][i].cpu().clone().detach().numpy().tolist(),
                          label_id=inputs["labels"][i].cpu().clone().detach().numpy().tolist(),
                          e1_mask=inputs["e1_mask"][i].cpu().clone().detach().numpy().tolist(),
                          e2_mask=inputs["e2_mask"][i].cpu().clone().detach().numpy().tolist(),
                          e1_id=inputs["e1_ids"][i].cpu().clone().detach().numpy().tolist(),
                          e2_id=inputs["e2_ids"][i].cpu().clone().detach().numpy().tolist())

#memory_list [[{概率：数据}],[{概率：数据}]...]
def save_memory(memory,memory_list):
    '''
    save memory form memory list
    :param memory: memory of seen tasks
    :param memory_list: memory of current task
    '''
    import data_loader
    for dicts in memory_list:
        for i in list(dicts.values()):
            memory.append(i)
    #memory.extend(dicts.values() for dicts in memory_list)


