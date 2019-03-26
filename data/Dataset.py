'''
Created on Aug 8, 2016
Processing datasets. 

@author: Xiangnan He (xiangnanhe@gmail.com)
'''
import numpy as np
import os
from data.LeaveOneOutDataSplitter import LeaveOneOutDataSplitter
from data.HoldOutDataSplitter import HoldOutDataSplitter
from data.GivenData import GivenData
class Dataset(object):
    '''
    Loading the data file
        trainMatrix: load rating records as sparse matrix for class Data
        trianList: load rating records as list to speed up user's feature retrieval
        testRatings: load leave-one-out rating test for class Evaluate
        testNegatives: sample the items not rated by user
    '''

    def __init__(self,path,splitter,threshold,separator,evaluate_neg,dataset_name,splitterRatio=[0.8,0.2]):
        '''
        Constructor
        '''
        self.path = path
        self.dataset_name = dataset_name
        self.separator= separator
        self.threshold = threshold
        self.splitterRatio=splitterRatio
        self.evaluate_neg = evaluate_neg
        self.splitter=splitter
        self.num_users = 0
        self.num_items = 0
        self.trainMatrix = None
        self.trainDict =  None
        self.testMatrix =  None
        self.testNegatives =  None
        self.timeMatrix = None 
        self.userseq = None
        self.userids = None
        self.itemids = None
        if splitter == "loo" :
            loo = LeaveOneOutDataSplitter(self.path,self.separator, self.threshold)
            self.trainMatrix,self.trainDict,self.testMatrix,\
            self.userseq,self.userids,self.itemids,self.timeMatrix = loo.load_data_by_user_time()
            self.num_users = self.trainMatrix.shape[0]
            self.num_items = self.trainMatrix.shape[1]
            self.testNegatives = self.get_negatives()
        elif splitter == "ratio" :
            hold_out = HoldOutDataSplitter(self.path,self.separator, self.threshold, self.splitterRatio)
            self.trainMatrix,self.trainDict,self.testMatrix,\
            self.userseq,self.userids,self.itemids,self.timeMatrix =\
            hold_out.load_data_by_user_time()
            self.num_users = self.trainMatrix.shape[0]
            self.num_items = self.trainMatrix.shape[1]
            self.testNegatives = self.get_negatives()
        elif splitter == "given" : 
            given = GivenData(self.path,self.separator, self.threshold)
            self.trainMatrix = given.load_training_file_as_matrix()
            self.self.trainDict =given.load_training_file_as_list() 
            self.testMatrix = given.load_testrating_file_as_matrix()
            self.num_users = self.trainMatrix.shape[0]
            self.num_items = self.trainMatrix.shape[1]
            if os.path.exists(self.path+".negative"):
                self.testNegatives = hold_out.load_negative_file()
            else :
                self.testNegatives = self.get_negatives()      
        else :
            print("please choose a splitter")
        self.num_users = self.trainMatrix.shape[0]
        self.num_items = self.trainMatrix.shape[1]
               
    def get_negatives(self):
        negatives = {}
        for u in np.arange(self.num_users):
            negative_per_user =[]
            if(self.evaluate_neg>0):
                for _ in np.arange(self.evaluate_neg): #.....................
                    neg_item_id = np.random.randint(0,self.num_items)
                    while (u,neg_item_id) in self.trainMatrix.keys() or  (u,neg_item_id) in self.testMatrix.keys() \
                          or neg_item_id in negative_per_user:
                        neg_item_id = np.random.randint(0, self.num_items)
                    negative_per_user.append(neg_item_id)
                negatives[u] = negative_per_user
                negative_per_user =[]
            else :
                negatives=None
        return  negatives                