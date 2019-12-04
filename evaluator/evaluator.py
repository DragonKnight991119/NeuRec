"""
@author: Zhongchuan Sun
"""
from util import csr_to_user_dict
from scipy.sparse import csr_matrix
from util import DataIterator, typeassert
import numpy as np
import pandas as pd
from collections import OrderedDict
from evaluator.backend import eval_score_matrix_foldout, eval_score_matrix_loo


class AbstractEvaluator(object):
    """Basic class for evaluator.
    """
    def __init__(self):
        pass

    def metrics_info(self):
        raise NotImplementedError

    def evaluate(self, model):
        raise NotImplementedError


class FoldOutEvaluator(AbstractEvaluator):
    """Evaluator for generic ranking task.
    """
    @typeassert(train_matrix=csr_matrix, test_matrix=csr_matrix)
    def __init__(self, train_matrix, test_matrix, config):
        super(FoldOutEvaluator, self).__init__()
        top_k = config["topk"]
        self.batch_size = config["test_batch_size"]

        self.max_top = top_k if isinstance(top_k, int) else max(top_k)
        if isinstance(top_k, int):
            self.top_show = np.arange(top_k)+1
        else:
            self.top_show = np.sort(top_k)
        self.user_pos_train = csr_to_user_dict(train_matrix)
        self.user_pos_test = csr_to_user_dict(test_matrix)
        self.metrics_num = 5

    def metrics_info(self):
        Precision = '\t'.join([("Precision@"+str(k)).ljust(12) for k in self.top_show])
        Recall = '\t'.join([("Recall@" + str(k)).ljust(12) for k in self.top_show])
        MAP = '\t'.join([("MAP@" + str(k)).ljust(12) for k in self.top_show])
        NDCG = '\t'.join([("NDCG@" + str(k)).ljust(12) for k in self.top_show])
        MRR = '\t'.join([("MRR@" + str(k)).ljust(12) for k in self.top_show])
        metric = '\t'.join([Precision, Recall, MAP, NDCG, MRR])
        return "metrics:\t%s" % metric

    def evaluate(self, model):
        # B: batch size
        # N: the number of items
        test_users = DataIterator(list(self.user_pos_test.keys()), batch_size=self.batch_size, shuffle=False, drop_last=False)
        batch_result = []
        for batch_users in test_users:
            test_items = []
            for user in batch_users:
                test_items.append(self.user_pos_test[user])
            ranking_score = model.predict(batch_users, None)  # (B,N)
            ranking_score = np.array(ranking_score)

            # set the ranking scores of training items to -inf,
            # then the training items will be sorted at the end of the ranking list.
            for idx, user in enumerate(batch_users):
                train_items = self.user_pos_train[user]
                ranking_score[idx][train_items] = -np.inf

            result = eval_score_matrix_foldout(ranking_score, test_items, top_k=self.max_top, thread_num=None)  # (B,k*metric_num)
            batch_result.append(result)

        # concatenate the batch results to a matrix
        all_user_result = np.concatenate(batch_result, axis=0)
        final_result = np.mean(all_user_result, axis=0)  # mean

        final_result = np.reshape(final_result, newshape=[self.metrics_num, self.max_top])
        final_result = final_result[:, self.top_show-1]
        final_result = np.reshape(final_result, newshape=[-1])
        buf = '\t'.join([("%.8f" % x).ljust(12) for x in final_result])
        return buf


class LeaveOneOutEvaluator(AbstractEvaluator):
    """Evaluator for leave one out ranking task.
    """
    @typeassert(train_matrix=csr_matrix, test_matrix=csr_matrix)
    def __init__(self, train_matrix, test_matrix, config):
        super(LeaveOneOutEvaluator, self).__init__()
        top_k = config["topk"]
        self.batch_size = config["test_batch_size"]

        self.max_top = top_k if isinstance(top_k, int) else max(top_k)
        if isinstance(top_k, int):
            self.top_show = np.arange(top_k)+1
        else:
            self.top_show = np.sort(top_k)
        self.user_pos_train = csr_to_user_dict(train_matrix)
        self.user_pos_test = csr_to_user_dict(test_matrix)
        self.metrics_num = 3

    def metrics_info(self):
        HR = '\t'.join([("HitRatio@"+str(k)).ljust(12) for k in self.top_show])
        NDCG = '\t'.join([("NDCG@" + str(k)).ljust(12) for k in self.top_show])
        MRR = '\t'.join([("MRR@" + str(k)).ljust(12) for k in self.top_show])
        metric = '\t'.join([HR, NDCG, MRR])
        return "metrics:\t%s" % metric

    def evaluate(self, model):
        # B: batch size
        # N: the number of items
        test_users = DataIterator(list(self.user_pos_test.keys()), batch_size=self.batch_size, shuffle=False, drop_last=False)
        batch_result = []
        for batch_users in test_users:
            test_items = []
            for user in batch_users:
                num_item = len(self.user_pos_test[user])
                if num_item != 1:
                    raise ValueError("the number of test item of user %d is %d" % (user, num_item))
                test_items.append(self.user_pos_test[user][0])
            ranking_score = model.predict(batch_users, None)  # (B,N)
            ranking_score = np.array(ranking_score)

            # set the ranking scores of training items to -inf,
            # then the training items will be sorted at the end of the ranking list.
            for idx, user in enumerate(batch_users):
                train_items = self.user_pos_train[user]
                ranking_score[idx][train_items] = -np.inf

            result = eval_score_matrix_loo(ranking_score, test_items, top_k=self.max_top, thread_num=None)  # (B,k*metric_num)
            batch_result.append(result)

        # concatenate the batch results to a matrix
        all_user_result = np.concatenate(batch_result, axis=0)
        final_result = np.mean(all_user_result, axis=0)  # mean

        final_result = np.reshape(final_result, newshape=[self.metrics_num, self.max_top])
        final_result = final_result[:, self.top_show-1]
        final_result = np.reshape(final_result, newshape=[-1])
        buf = '\t'.join([("%.8f" % x).ljust(12) for x in final_result])
        return buf


class SparsityEvaluator(AbstractEvaluator):
    @typeassert(train_matrix=csr_matrix, test_matrix=csr_matrix)
    def __init__(self, train_matrix, test_matrix, config):
        super(SparsityEvaluator, self).__init__()
        if config["evaluator"] == "ratio":
            self.evaluator = FoldOutEvaluator(train_matrix, test_matrix, config)
        elif config["evaluator"] == "loo":
            self.evaluator = LeaveOneOutEvaluator(train_matrix, test_matrix, config)
        else:
            raise ValueError("There is not evaluator named '%s'" % config["evaluator"])

        self.user_pos_train = self.evaluator.user_pos_train
        self.user_pos_test = self.evaluator.user_pos_test

        group_list = config["group_list"]
        all_test_user = list(self.user_pos_test.keys())
        num_interaction = [len(self.user_pos_train[u]) for u in all_test_user]
        group_idx = np.searchsorted(group_list, num_interaction)
        user_group = pd.DataFrame(zip(all_test_user, group_idx), columns=["user", "group"])
        grouped = user_group.groupby(by=["group"])
        group_list = [0] + group_list
        group_list = ["(%d,%d]" % (g_l, g_h) for g_l, g_h in zip(group_list[:-1], group_list[1:])]

        self.grouped_user = OrderedDict()
        for idx, users in grouped:
            if idx < len(group_list):
                self.grouped_user[group_list[idx]] = users["user"].tolist()

    def metrics_info(self):
        return self.evaluator.metrics_info()

    def evaluate(self, model):
        if not self.grouped_user:
            return "The group of user split is not suitable!"

        result_to_show = ""
        for group, users in self.grouped_user.items():
            self.evaluator.user_pos_test = {u: self.user_pos_test[u] for u in users}
            tmp_result = self.evaluator.evaluate(model)
            result_to_show = "%s\n%s:\t%s" % (result_to_show, group, tmp_result)

        return result_to_show
