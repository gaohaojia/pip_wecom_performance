import requests
import yaml
import pymysql
import datetime
import sys
import csv
import shutil

# 读取信息
with open('./key.yml', 'r', encoding='utf-8') as f:
    key = yaml.load(f.read(), Loader=yaml.FullLoader)

leader_name = []

# 获取所有user_id
def get_all_user_id(access_token):
    url = "https://qyapi.weixin.qq.com/cgi-bin/user/list_id?access_token={}".format(access_token)
    response = requests.get(url)
    user_id = response.json()
    return user_id['dept_user']

# 根据user_id获取员工姓名
def get_name(access_token, user_id):
    url = "https://qyapi.weixin.qq.com/cgi-bin/user/get?access_token={}&userid={}".format(access_token, user_id)
    response = requests.get(url)
    name = response.json()['name']
    return name

# 设置应用在工作台展示的模版
def set_template(access_token, agentid):
    url = "https://qyapi.weixin.qq.com/cgi-bin/agent/set_workbench_template?access_token={}".format(access_token)
    data = {
        "agentid":agentid,
        "type":"keydata"
    }
    response = requests.post(url, json=data)
    data = response.json()
    return data

# 为队员添加数据
def push_member_data(access_token, agentid, user_id, last_90day_time, total_time, rank):
    url = "https://qyapi.weixin.qq.com/cgi-bin/agent/set_workbench_data?access_token={}".format(access_token)
    data = {
        "agentid": agentid,
        "userid": user_id,
        "type":"keydata",
        "keydata":{
            "items":[
                {
                    "key":"最近90天工作量",
                    "data":str(last_90day_time),
                },
                {
                    "key":"本赛季总工作量",
                    "data":str(total_time),
                },
                {
                    "key":"本赛季队内排名",
                    "data":rank,
                }
            ]
        }
    }
    response = requests.post(url, json=data)
    data = response.json()
    return data

# 为队长、项管添加数据
def push_leader_data(access_token, agentid, user_id, last_week_cnt, average_time, max_time):
    url = "https://qyapi.weixin.qq.com/cgi-bin/agent/set_workbench_data?access_token={}".format(access_token)
    data = {
        "agentid": agentid,
        "userid": user_id,
        "type":"keydata",
        "keydata":{
            "items":[
                {
                    "key":"上周工作人数",
                    "data":str(last_week_cnt),
                },
                {
                    "key":"全队平均工作量",
                    "data":str(average_time),
                },
                {
                    "key":"最高工作量",
                    "data":str(max_time),
                }
            ]
        }
    }
    response = requests.post(url, json=data)
    data = response.json()
    return data

# 获取队员在sql中的id
def get_sql_id(cursor, name):
    sql = 'SELECT ID FROM member WHERE member_name=\'{}\''.format(name)
    cursor.execute(sql)
    return cursor.fetchall()[0][0]

# 获取队员工作量
def get_info_from_id(cursor, name_id):
    sql = 'SELECT start_date, event, event_time FROM time_event WHERE member_name={}'.format(name_id)
    cursor.execute(sql)
    return cursor.fetchall()

# 获取上周日期
def get_last_wek_weekday(n):
    today_info = datetime.date.today()

    one_day = datetime.timedelta(days=1)
    seven_day = datetime.timedelta(days=7)

    last_week_day = today_info - seven_day
    last_week_day_n = last_week_day.weekday()

    if last_week_day_n < n:
        while last_week_day.weekday() != n:
            last_week_day += one_day
    else:
        while last_week_day.weekday() != n:
            last_week_day -= one_day

    return last_week_day

def main():

    member_list = []

    # 连接access数据库
    connection = pymysql.connect(
        host='',
        port=3306,
        user='',
        passwd='',
        db='',
        charset='utf8mb4'
    )
    cursor = connection.cursor()

    # 获取token
    app_access_token = sys.argv[1]
    address_access_token = sys.argv[2]

    # 设置数据类型
    set_template(app_access_token, key['AgentId'])
    
    # 获取所有user_id
    user_id = get_all_user_id(address_access_token)
    now_date = datetime.date.today()

    # 获取所有队员工作量
    result_list = [] # 结果列表
    leader_user_id = [] # 队长和项管的user_id
    last_week_cnt = 0 # 上周工作人数
    for user in user_id:

        # 判断是否已处理过
        if user['userid'] in member_list:
            continue
        member_list.append(user['userid'])

        # 根据userid获取name
        name = get_name(app_access_token, user['userid'])
        
        # 判断是否为队长或项管
        if name in leader_name:
            leader_user_id.append(user['userid'])
            continue

        # 判断数据库中是否存在该name
        try:
            name_id = get_sql_id(cursor, name)
        except:
            continue
        data = get_info_from_id(cursor, name_id)

        # 计算各项数据
        last_week_time, last_90day_time, total_time = 0, 0, 0
        has_last_week = False
        for i in data:
            total_time += i[2]
            if (now_date - i[0]).days <= 90:
                last_90day_time += i[2]
            if (i[0] - get_last_wek_weekday(0)).days >= 0:
                last_week_time += i[2]
                has_last_week = True
        if has_last_week:
            last_week_cnt += 1
        result_list.append([name, round(last_week_time, 1), round(last_90day_time, 1), round(total_time, 1), user['userid']])

    # 按工作量排序
    result_list.sort(key=lambda result:result[3], reverse=True)

    # 写入工作量信息
    f = open('writing', 'w')
    csv_writer = csv.writer(f)
    csv_writer.writerow(["姓名", "上周工作量", "最近90天工作量", "总工作量", "排名"])

    # 给队友添加数据
    for idx in range(len(result_list)):

        # 计算排名
        rank_rate = (idx + 1) / len(result_list)
        if rank_rate <= 0.05:
            rank = "前5%"
        elif rank_rate <= 0.1:
            rank = "前10%"
        elif rank_rate <= 0.2:
            rank = "前20%"
        elif rank_rate <= 0.3:
            rank = "前30%"
        elif rank_rate <= 0.5:
            rank = "前50%"
        else:
            rank = "后50%"
        
        # 写入csv
        csv_writer.writerow([*result_list[idx], rank])

        # 添加数据
        push_info = push_member_data(app_access_token, key['AgentId'], result_list[idx][4], result_list[idx][2], result_list[idx][3], rank)
        if push_info['errcode'] != 0:
            print(push_info)

    f.close()

    # 将写完的结果保存，防止被覆盖
    shutil.copy('writing', r'info.csv')

    for user_id in leader_user_id:
        push_leader_data(app_access_token, key['AgentId'], user_id, last_week_cnt, round(sum(i[3] for i in result_list) / len(result_list), 1), max(i[3] for i in result_list))

if __name__ == "__main__":
    main()