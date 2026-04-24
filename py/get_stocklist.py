# coding=utf-8
import requests
import json
import os
import pandas as pd
from datetime import datetime,date


def get_stocklist_dfcfw():
    #一次性获取所有股票清单信息，获取信息快，信息较全。
    url = "http://23.push2.eastmoney.com/api/qt/clist/get?cb=jQuery112403461296577881501_1600744555568&pn=1&pz=10000&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:13,m:0+t:80,m:1+t:2,m:1+t:23&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152&_=1600744555569"

    headers={
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.79 Safari/537.36'
    }


    # 循环执行，直至获取成功
    loop = True
    while loop == True:
        try:
            response=requests.get(url,headers=headers,timeout=3)
            response.encoding='utf-8'
        except Exception as e:
            loop = True
        else:
            if response.content:
                a = response.text.find('(',1)+1#从第一个左括号+1位置开始
                b = response.text.rfind(')')-len(response.text)#结束于右括号
                json_str=response.text[a:b]#截取字符串
                if len(json_str)>50: #获取行情信息长度如果小于50字符，则失败
                    kdata = json.loads(json_str)
                    if kdata['data']:
                        df_data = pd.DataFrame(kdata['data']['diff'])
                        df_data = df_data[['f1','f2','f3','f4','f5','f6','f7','f8','f9','f10','f11','f12','f13','f14','f15','f16','f17','f18','f20','f21','f22','f23','f24','f25','f62','f115','f152']] #'f128','f136','f140','f141',
                        df_data = df_data.replace('-', 0)
                        # # 中文字段名
                        # df_data = df_data[['f12','f14','f2','f15','f16','f17','f3','f4','f5','f6','f7','f8','f9','f10','f18','f20','f21','f23']].rename(index=str, columns={'f2':'最新价','f3':'涨跌幅','f4':'涨跌额','f5':'成交量(手)',
                         #'f6':'成交额','f7':'振幅','f8':'换手率','f9':'市盈率(动态)','f10':'量比','f12':'代码','f14':'名称','f15':'最高','f16':'最低','f17':'今开','f18':'昨收','f20':'总值','f21':'流通市值','f23':'市净率'})
                        # # 由于以下几列在后面使用英文引用，如果使用中文名调用则无需添加。
                        # df_data['code'] = df_data['代码']
                        # df_data['name'] = df_data['名称']
                        # df_data['close'] = df_data['最新价']
                        # df_data['volume'] = df_data['成交量(手)']
                        # 英文字段名
                        df_data = df_data[['f12','f14','f2','f15','f16','f17','f3','f4','f5','f6','f7','f8','f9','f10','f18','f20','f21','f23']].rename(index=str, columns={'f2':'close','f3':'zhangfu','f4':'zhangdie','f5':'volume','f6':'amount','f7':'zhenfu','f8':'hs_l','f9':'pe_d','f10':'liangbi','f12':'code','f14':'name','f15':'high','f16':'low','f17':'open','f18':'pre_close','f20':'z_value','f21':'lt_value','f23':'sj_l'})
                        # 增加交易时间，方便后期显示
                        df_data['trade_time'] = str(datetime.now().strftime('%Y-%m-%d'))
                        df_data = df_data.sort_values(by = 'code',ascending=True)
                        df_data = df_data.reset_index()
                        loop == False
                        return {
                            "success": True,
                            "df_data":df_data.round(2) #将数据里简化为2位小数，如果是基金则需要调整。
                        }

                    else:
                        return {
                            "success": False,
                            "msg": '获取行情信息结果为None'
                        }
            else:
                return {
                    "success": False,
                    "msg": '获取行情信息失败'
                }

# ===============表格美化输出===============
def df_table(df,index):
    import prettytable as pt
    #利用prettytable对输出结果进行美化,index为索引列名:df_table(df,'market')
    tb = pt.PrettyTable()
    df = df.reset_index(drop = True)
    tb.add_column(index,df.index)
    for col in df.columns.values:#df.columns.values的意思是获取列的名称
        tb.add_column(col, df[col])
    print(tb)


if __name__ == '__main__':
    
    # from KTstock import get_stocklist_dfcfw # 将文件保存为KTstock，同目录引用方法取消注释即可
    import time
    # 计时开始
    time1 = time.time()
    res = get_stocklist_dfcfw()
    if res['success']:
        df = res['df_data']
        time2 = time.time()
        print("get_stocklist_dfcfw耗时:",time2-time1,'秒')
        # print(df) # 显示所有数据
        # print(df['code']) # 只显示单个字段
        df_table(df.tail(10),'stock') # 格式化输出，只显示最后10行
        
        if 1:
            # 剔除交易量为0的股票
            df = df[df['volume']>0]
        if 1:
            # 名称中不包含
            not_contain=['ST|PT|退']
            if len(not_contain)>0:
                df = df[~ df['name'].str.contains('|'.join(str(v) for v in not_contain))]
                df_table(df.head(10),'stock') # 格式化输出，只显示最前10行
        if 1:
            # 名称中包含
            contain=['药|芯']
            if len(contain)>0:
                df = df[df['name'].str.contains('|'.join(str(v) for v in contain))]
                df_table(df,'stock')
        if 1:
            # 代码开头
            code_prefix = ("300","688")
            if len(code_prefix)>0:
                df = df[df['code'].str.startswith(code_prefix)]
                df_table(df,'stock')
        if 0:
            # 只筛选特定代码的数据
            lists = ['000001','300750','600259']
            if len(lists)>0:
                df = df[df['code'].isin(lists)]
                df_table(df,'stock')
        if 1:
            # 显示多个字段，注意[]嵌套
            print(df[['code','name','close']])
            df_table(df[['code','name','close']],'stock')
            # 只提取code列并转为list
            code_list = df['code'].tolist()
            print(code_list)

