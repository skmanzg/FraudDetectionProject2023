#!/usr/bin/env python
# coding: utf-8

# In[10]:


import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import RobustScaler
from tensorflow import keras
import datetime as dt


# In[1]:


def ColumnsExtractor_CNN(data, isLearn, reduced_data_CNN):
    if(not ("DAY" in data.columns)): #DAY컬럼이 없다면 추가
        list1 = []
        for i in range(data.shape[0]):
            list1.append(0)

        data["DAY"] = list1
        
        data = data.reset_index(drop=True)
        
        for i in range(data.shape[0]):
            dt1 = dt.datetime(2019, 1, 1)
            if(not isLearn):
                dt2 = dt.datetime(int(data.loc[0, "TRANS_YEAR"]), int(data.loc[0, "TRANS_MONTH"]), int(data.loc[0, "TRANS_DAY"]))
            else:
                dt2 = dt.datetime(int(data.loc[i, "TRANS_YEAR"]), int(data.loc[i, "TRANS_MONTH"]), int(data.loc[i, "TRANS_DAY"]))
            if(dt1 == dt2):
                td = 0
                data.loc[i, "DAY"] = td
            else:
                td = dt2 - dt1
                data.loc[i, "DAY"] = td
                list_temp = (str(data.loc[i, "DAY"]).split(" day"))
                data.loc[i, "DAY"] = list_temp[0]

        data["DAY"] = data["DAY"].astype(int)
        
    reduced_data_CNN = data[["TRANS_YEAR", "TRANS_MONTH", "TRANS_DAY", "CC_NUM", "DAY", "AMT", "IS_FRAUD"]]
    reduced_data_CNN["IS_FRAUD"] = reduced_data_CNN["IS_FRAUD"].astype("int")
    return reduced_data_CNN

def abs_value(val):
    if(val <= 0.0):
        return -val
    else:
        return val

def sigmoid_(x):
    return (1 / (1 + np.exp(-x)))

# In[6]:


def TableConverter(reduced_data, isLearn, gamma):
    #reduced_data는 데이터프레임이다
    #입력DF의 행은 4개의 열을 가졌고 하나의 행은 하나의 거래이다. (CC_NUM이 아니다)
    #출력DF의 행은 하나의 CC_NUM에 대한 정보이고 열은 CC_NUM, DAY1, DAY2, ..., FRAUD_TODAY1, FRAUD_TODAY2, ... 형식이다
    #DAY1, DAY2, ... 열에는 각 DAY의 AMT가 들어간다
    df_ccnum = pd.DataFrame(reduced_data["CC_NUM"].unique(), columns=["CC_NUM"])
    df_amt = np.full((df_ccnum.shape[0], reduced_data["CC_NUM"].value_counts().max()), -1) # -1로 채워진 array (밑에 df로 변환하게 됨)
    list_daycount = []
    for i in range(reduced_data["CC_NUM"].value_counts().max()):
        list_daycount.append("DAY%d" %(i+1))
    
    df_amt = pd.DataFrame(df_amt, columns=list_daycount)
    
    #df_fraudtoday는 열의 갯수가 df_amt의 열의 갯수에서 (gamma - 1)값을 뺀 것이다
    df_fraudtoday = np.full([df_ccnum.shape[0], len(list_daycount) - (gamma - 1)], -1)
    list_fraudtodaycount = []
    for i in range(df_fraudtoday.shape[1]):
        list_fraudtodaycount.append("FRAUD_TODAY%d" %(i+1))
        
    df_fraudtoday = pd.DataFrame(df_fraudtoday, columns=list_fraudtodaycount)
    #여기까지 오면 df 틀은 완성이다. 단 CC_NUM컬럼은 이미 값이 채워져 있는 상태
    #CC_NUM과 DAY순으로 정렬된 AMT들이 한 행으로 쭉 정렬된 모습
    
    idx_count = 0 #CC_NUM의 인덱스를 가리킨다
    num_count = 1 #DAY1, DAY2, ...를 가리킨다
    reduced_data.reset_index(drop=True, inplace=True)
    reduced_data2 = reduced_data.copy()
    reduced_data_ccnum_sorted = (reduced_data["CC_NUM"].unique()).tolist()
    reduced_data_ccnum_sorted = sorted(reduced_data_ccnum_sorted)
    for i in range(reduced_data.shape[0]):
        #idx_count로 요소 접근
        #ccnum_unique_list는 CC_NUM의 종류가 정렬되어 나열된 리스트이다.
        reduced_data = reduced_data.sort_values(by=["CC_NUM"] ,ascending=True)
        reduced_data_listform = reduced_data["CC_NUM"].tolist()
        reduced_data_listform = sorted(reduced_data_listform)
        if(reduced_data_ccnum_sorted[idx_count] != reduced_data_listform[i]):
            idx_count += 1
            num_count = 1
        
        df_amt.loc[idx_count, "DAY%d" %(num_count)] = reduced_data.loc[i, "AMT"]
        num_count += 1
    #여기까지 오면 df_ccnum과 df_amt가 채워졌다.
    
    ccnum_fraud = reduced_data[["CC_NUM", "IS_FRAUD"]]
    current_ccnum = ccnum_fraud.loc[gamma - 1, "CC_NUM"]
    
    df_fraudtoday_row = 0
    df_fraudtoday_col = 0
    
    reduced_data2 = reduced_data2.sort_values(by=["CC_NUM"] ,ascending=True)
    reduced_data2 = reduced_data2.reset_index(drop=True)
    
    for ccnum_fraud_row in range(gamma - 1,reduced_data2.shape[0]): #ccnum_fraud_row는 압축되지 않은 idx
        if(ccnum_fraud_row % 1000 == 0):
             print("ccnum_fraud_row :", ccnum_fraud_row)
        if(reduced_data2.loc[ccnum_fraud_row, "CC_NUM"] != current_ccnum.item()): #for문을 반복하게되면 현재 CC_NUM을 직전 CC_NUM과 비교한다
            df_fraudtoday_row += 1
            df_fraudtoday_col = 0
        df_fraudtoday.loc[df_fraudtoday_row, "FRAUD_TODAY%d" %(df_fraudtoday_col+1)] = reduced_data2.loc[ccnum_fraud_row, "IS_FRAUD"]

        df_fraudtoday_col = df_fraudtoday_col + 1
        if(df_fraudtoday_col + 1 > (reduced_data2["CC_NUM"].value_counts().max()) - (gamma - 1)):
            continue
        else:
            pass
        current_ccnum = reduced_data2.loc[ccnum_fraud_row, "CC_NUM"] # 현재 CC_NUM을 current_ccnum에 대입(for문 다시 돌아가면 ccnum_fraud_row는 1이 더해짐)
    
    data_converted = pd.concat([df_ccnum, df_amt, df_fraudtoday], axis = 1)
    data_converted = data_converted.fillna(-1)
    data_converted.drop(data_converted.index[-1], inplace=True)
    
    global data_conv_load
    data_conv_load = data_converted
    
    global data_converted_global
    data_converted_global = data_converted.copy()
    
    if(not isLearn):
        pass
    return data_converted
    


# In[8]:


#isLearn이 True인 경우, 입력data는 data_converted이며 출력값은 2열로 이뤄진 sequence이름의 df이다
#isLearn이 False인 경우, 입력data는 1열로 이뤄진 gamma일 동안의 amt인 df이며 출력값은 diff값인 1요소 값이다.

def DifferenceGenerator(data_converted, isLearn, gamma, mu, reduced_data_CNN):
    differenceSequence = pd.DataFrame([], columns=["DIFF", "FRAUD_TODAY"])

    if(isLearn):
        reduced_data_CNN = reduced_data_CNN.reset_index(drop=True)
        day_col = gamma #day부분 column index 초깃값
        fraudtoday_col = 1 + reduced_data_CNN["CC_NUM"].value_counts().max() #FRAUD_TODAY부분 column index 초깃값
        
        for conv_row_idx in range(data_converted.shape[0]):
            if(conv_row_idx % 100 == 0):
                print("conv_row_idx : ", conv_row_idx)
            day_col = gamma + 1 #day부분 column index 초깃값
            fraudtoday_col = 1 + reduced_data_CNN["CC_NUM"].value_counts().max() #FRAUD_TODAY부분 column index 초깃값
            for k in range((reduced_data_CNN["CC_NUM"].value_counts().max()) - (gamma - 1) - 1): #k는 처음 위치로부터의 column의 변위
                diff_value = 0
                if(data_converted.loc[conv_row_idx, "DAY%d" %(day_col + k)] == -1): #현재 k가 가리키는 day의 amt값이 -1이면 다음 행으로
                    break
                for j in range(-gamma + 1, 0): # -gamma + 1, -gamma + 2, ..., -2, -1
                    if(j != -1): #k가 가리키고 있는 amt에 mu만큼의 가중치를 곱함. 
                        prev_value = data_converted.loc[conv_row_idx, "DAY%d" %(day_col + k + j)]
                        present_value = data_converted.loc[conv_row_idx, "DAY%d" %(day_col + k + j + 1)]
                        diff_value = diff_value + abs_value(present_value - prev_value)
                    elif (j == -1):
                        prev_value = data_converted.loc[conv_row_idx, "DAY%d" %(day_col + k + j)]
                        present_value = data_converted.loc[conv_row_idx, "DAY%d" %(day_col + k + j + 1)]
                        weighted = abs_value(present_value - prev_value)
                        weighted = weighted * mu
                        diff_value = diff_value + weighted
            # 하나의 subsequence에 대한 diff의 합이 구해졌다. (diff_value)
                one_sequence = pd.DataFrame({"DIFF": [diff_value], "FRAUD_TODAY":[data_converted.loc[conv_row_idx, "FRAUD_TODAY%d" %(fraudtoday_col + k - (reduced_data_CNN["CC_NUM"].value_counts().max()))]]})
                if(one_sequence["FRAUD_TODAY"].item() != -1):
                    differenceSequence = pd.concat([differenceSequence, one_sequence], axis=0)

        return differenceSequence
    else:
        #gamma -1 일 전부터 오늘까지 기록되었던 AMT들이 gamma행x1열 형태로 들어옴
        diff_value2 = 0
        for i in range(1, gamma):
            if(i != (gamma - 1)):
                prev_value2 = data_converted.loc[i - 1]
                present_value2 = data_converted.loc[i]
                diff_value2 += abs(present_value2 - prev_value2)
            elif(i == (gamma - 1)):
                prev_value2 = data_converted.loc[i - 1]
                present_value2 = data_converted.loc[i]
                weighted2 = abs(present_value2 - prev_value2)
                weighted2 = weighted2 * mu
                diff_value2 += weighted2
        
        return diff_value2 #이 때의 출력은 diff_value2라는 1요소 값이다
        


# In[9]:


def Multiplier(differenceSequence, omega):
    if(differenceSequence.shape[1] == 2):
        temp = differenceSequence["DIFF"]
        temp = temp * omega
        temp2 = differenceSequence["DIFF2"]
        temp2 = temp2 * omega
        differenceSequence["DIFF"] = temp
        differenceSequence["DIFF2"] = temp2
        return differenceSequence
    
    temp0 = differenceSequence["DIFF"]
    temp0 = temp0 * omega
    differenceSequence["DIFF"] = temp0
    return differenceSequence


# In[3]:


def DifferenceforFraud(data, isLearn, gamma, delta2, omega, mu): #추론시의 data는 1행이다
    conserved_data = pd.read_csv("../data/ordered_by_ccnum_and_day.csv", index_col=0) #TRANS_YEAR, MONTH, DAY 열을 포함하고 있는 conserved_data 데이터프레임
    reduced_data = ColumnsExtractor_CNN(data, isLearn, conserved_data.copy()) #"CC_NUM", "DAY", "AMT", "IS_FRAUD" 열들만 가지는 reduced_data 데이터프레임
    global lr
    
    if(isLearn):
        data_converted = TableConverter(reduced_data, isLearn, gamma)
        
        global differenceSequence_
        differenceSequence_ = DifferenceGenerator(data_converted, isLearn, gamma, mu, conserved_data)
        differenceSequence_temp_stored = differenceSequence_.copy()
        Rscaler3 = RobustScaler()
        differenceSequence_duplicated = differenceSequence_["DIFF"].to_frame()
        differenceSequence_duplicated.rename(columns={"DIFF":"DIFF2"}, inplace=True)
        
        differenceSequence_ = pd.concat([differenceSequence_, differenceSequence_duplicated], axis=1)
        differenceSequence_fraud = differenceSequence_["FRAUD_TODAY"].to_frame().copy()
        arr_temp = differenceSequence_[["DIFF", "DIFF2"]].__array__()
        Rscaler3.fit(arr_temp)
        differenceSequence_scaled_diff = Rscaler3.transform(arr_temp)
        differenceSequence_scaled_diff = pd.DataFrame(differenceSequence_scaled_diff, columns=["DIFF", "DIFF2"])
        differenceSequence_ = differenceSequence_scaled_diff
        
        differenceSequence_ = Multiplier(differenceSequence_, omega)
        lr = LogisticRegression()
        differenceSequence_fraud = differenceSequence_fraud.astype("int")
        differenceSequence_fraud.reset_index(drop=True, inplace=True)
        lr.fit(differenceSequence_[["DIFF", "DIFF2"]], np.ravel(differenceSequence_fraud, order='C'))
        differenceSequence_ = differenceSequence_temp_stored.copy() #전역변수는 값을 바꿨으면 다시 되돌려놓기
        return 2
    
    else:
        whats_ccnum = np.nan
        for ccnum_for in (data_conv_load["CC_NUM"]): #기존 훈련 자료에 있는 CC_NUM들 중에서 일치하는 CC_NUM찾기
            if(data["CC_NUM"].item() == ccnum_for):
                whats_ccnum = ccnum_for
        
        #입력된 1행의 DAY값 구하기 시작
        dt1 = dt.datetime(2019, 1, 1)
        dt2 = dt.datetime(reduced_data.loc[0, "TRANS_YEAR"], reduced_data.loc[0, "TRANS_MONTH"], reduced_data.loc[0, "TRANS_DAY"])
        if(dt1 == dt2):
            td = 0
            reduced_data.loc[0, "DAY"] = td
        else:
            td = dt2 - dt1
            reduced_data.loc[0, "DAY"] = td
            list_temp = (str(reduced_data.loc[0, "DAY"]).split(" day"))
            reduced_data.loc[0, "DAY"] = list_temp[0]
        reduced_data["DAY"] = reduced_data["DAY"].astype(int)
        #입력된 1행의 DAY값 구하기 끝
        
        #입력된 1행이 동일한 CC_NUM 데이터들 중 어느 위치에 있는지 판별
        ccnum_conserved_data = pd.DataFrame([], columns=["CC_NUM", "DAY", "AMT"])
        ccnum_conserved_data_temp = pd.DataFrame({"CC_NUM":[0], "DAY":[0], "AMT":[0]})
        for index, row in conserved_data.iterrows(): #index는 인덱스값, row는 Series를 얻는다
            if(whats_ccnum == row["CC_NUM"]):
                ccnum_conserved_data_temp.loc[0, "CC_num"] = whats_ccnum
                ccnum_conserved_data_temp.loc[0, "DAY"] = row["DAY"]
                ccnum_conserved_data_temp.loc[0, "AMT"] = row["AMT"]
                ccnum_conserved_data = pd.concat([ccnum_conserved_data, ccnum_conserved_data_temp], axis = 0)
        #ok
        
        idx_order = 0
        ccnum_conserved_data = ccnum_conserved_data.reset_index(drop=True)
        day_ = reduced_data.loc[0, "DAY"]
        for i in  range(len(ccnum_conserved_data["DAY"])):
            if(ccnum_conserved_data.loc[i, "DAY"] < day_):
                idx_order += 1
            else:
                break
        list_order = []
        for i in range(idx_order):
            list_order.append(ccnum_conserved_data.loc[i,"AMT"])
        list_order.append(reduced_data.loc[0, "AMT"])
        
        #list_order는 현재 들어온 AMT값까지 해서 "모든"날짜수 만큼 가지고 있다. gamma 날짜수로 맞추는 작업이 필요!
        if(len(list_order) > gamma): #맨 과거의 데이터를 while문을 통해 하나씩 없앰
            while(len(list_order) > gamma):
                del list_order[0]
        elif(len(list_order) < gamma): #가장 오래된 데이터를 이어붙임. e.g.) [2,3,4,4] -> [2,2,2,2,3,4,4]
            oldest_day = list_order[0]
            while(len(list_order) < gamma):
                list_order.insert(0, oldest_day)
        df_order = pd.DataFrame({"AMT:":list_order})
        diff_scalar = DifferenceGenerator(df_order, isLearn, gamma, mu, conserved_data)
        fraud_of_diff_scalar = reduced_data["IS_FRAUD"] #데이터에 기록된 시점에서의 fraud여부
        diff_scalar = diff_scalar[0]
        fraud_of_diff_scalar = fraud_of_diff_scalar[0]
        
        #스케일러를 위해 differenceSequence_에 diff_scalar를 붙이고 scaling
        
        data_for_scaling = pd.DataFrame({"DIFF":[diff_scalar], "FRAUD_TODAY":[fraud_of_diff_scalar]})
        differenceSequence_temp = pd.concat([differenceSequence_, data_for_scaling], axis=0)
        
        Rscaler4 = RobustScaler()
        differenceSequence_temp2 = differenceSequence_temp["DIFF"].copy()
        differenceSequence_temp2 = differenceSequence_temp2.rename("DIFF2")
        differenceSequence_temp["DIFF2"] = differenceSequence_temp2
        
        Rscaler4.fit(differenceSequence_temp[["DIFF", "DIFF2"]])
        differenceSequence_scaled_temp = Rscaler4.transform(differenceSequence_temp[["DIFF", "DIFF2"]])
        differenceSequence_scaled_temp = pd.DataFrame(differenceSequence_scaled_temp, columns=["DIFF", "DIFF2"])

        input_data = differenceSequence_scaled_temp.tail(1) # AMT가 스케일링 됐고 2열에는 FRAUD여부
        
        input_data = Multiplier(input_data, omega)
        
        #print("lr will be exectued......@@")

        predict_proba = sigmoid_(input_data["DIFF"])
        
        if(predict_proba.item() >= delta2): # FRAUD
            return 1
        else: # NOT FRAUD
            return 0
        
        


# %%
