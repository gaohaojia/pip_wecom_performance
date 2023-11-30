import requests
import yaml
import time
import pymysql
import sys
import csv

# 读取信息
with open('./key3.yml', 'r', encoding='utf-8') as f:
    key = yaml.load(f.read(), Loader=yaml.FullLoader)

# 获取所有审批id
def get_sp_no_list(access_token, template_id, last_time, now_time, new_cursor):
    url = "https://qyapi.weixin.qq.com/cgi-bin/oa/getapprovalinfo?access_token={}".format(access_token)
    sp_no_list = []
    while True:
        data = {
            "starttime" : last_time,
            "endtime" : now_time,
            "new_cursor" : new_cursor,
            "size" : 100 ,
            "filters" : [
                {
                    "key": "template_id",
                    "value": template_id
                } 
            ]
        }
        response = requests.post(url, json=data)
        data = response.json()
        sp_no_list.extend(data['sp_no_list'])
        try:
            new_cursor = data['new_next_cursor']
        except:
            break

    return sp_no_list

# 根据审批id获取具体内容
def get_approval_data(access_token, sp_no):
    url = "https://qyapi.weixin.qq.com/cgi-bin/oa/getapprovaldetail?access_token={}".format(access_token)
    data = {
        "sp_no" : sp_no
    }
    response = requests.post(url, json=data)
    data = response.json()
    return data['info']

# 根据user_id获取员工姓名
def get_name(access_token, user_id):
    url = "https://qyapi.weixin.qq.com/cgi-bin/user/get?access_token={}&userid={}".format(access_token, user_id)
    response = requests.get(url)
    name = response.json()['name']
    return name

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

# 发送自定义消息
def send_message(access_token, user_id, agent_id, msg):
    url = "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={}&debug=1".format(access_token)
    data = {
        "touser" : str(user_id),
        "msgtype": "markdown",
        "agentid" : agent_id,
        "markdown": {
            "content": msg
        }
    }
    response = requests.post(url, json=data)
    return response.json()

def main():

    app_access_token = sys.argv[1]
    access_token = sys.argv[2]

    last_time1 = key['last_time1']
    last_time2 = key['last_time2']
        
    now_time = time.time()

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



    # 获取审批内容
    sp_no_list = get_sp_no_list(access_token, key['detail_template_id'], last_time1, int(now_time), "")
    if len(sp_no_list) == 0:
        print("无审批")
    else:
        last_time1 = now_time

    # 判断审批是否都处理
    all_sp_data = []
    for sp_no in sp_no_list:
        sp_data = get_approval_data(access_token, sp_no)
        all_sp_data.append(sp_data)
    
    # 遍历审批列表
    for sp_data in all_sp_data:
        user_name = get_name(access_token, sp_data['applyer']['userid'])
        
        # 判断数据库中是否存在该name
        try:
            user_sql_id = get_sql_id(cursor, user_name)
        except:
            send_message(app_access_token, sp_data['applyer']['userid'], key['AgentId'], "### 工作量细则查询 \n[{}]\n>暂无您的工作量，有任何疑问请联系队长或填写[意见反馈]()。".format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())))
            continue

        # 判断是否有工作量
        user_data = get_info_from_id(cursor, user_sql_id)
        if len(user_data) == 0:
            send_message(app_access_token, sp_data['applyer']['userid'], key['AgentId'], "### 工作量细则查询 \n[{}]\n>暂无您的工作量，有任何疑问请联系队长或填写[意见反馈]()。".format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())))
            continue

        msg = "### 工作量细则查询 \n[{}]\n".format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
        cnt = 0
        for i in user_data:
            cnt += 1
            msg += ">时间：<font color=\"info\">{}</font>  \n内容：{}  \n  \n工作量：<font color=\"warning\">{}</font>  \n".format(*i)
            if cnt >= 10:
                send_message(app_access_token, sp_data['applyer']['userid'], key['AgentId'], msg)
                cnt = 0
                msg = ""
        msg += "如有疑问，请填写[意见反馈]()。"
        send_message(app_access_token, sp_data['applyer']['userid'], key['AgentId'], msg)
        



    # 获取审批内容
    sp_no_list = get_sp_no_list(access_token, key['news_template_id'], last_time2, int(now_time), "")
    if len(sp_no_list) == 0:
        print("无审批")
    else:
        last_time2 = now_time

    # 判断审批是否都处理
    all_sp_data = []
    for sp_no in sp_no_list:
        sp_data = get_approval_data(access_token, sp_no)
        all_sp_data.append(sp_data)
    
    # 遍历审批列表
    for sp_data in all_sp_data:
        member_data_list = []
        with open("info.csv") as csvfile:
            csv_data = csv.reader(csvfile)
            for row in csv_data:
                member_data_list.append(row)
        msg = "### 战队周报 \n[{}]\n".format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
        for member_data in member_data_list:
            msg += ">{} {} {} {}\n".format(member_data[0], member_data[1], member_data[2], member_data[3])
        send_message(app_access_token, sp_data['applyer']['userid'], key['AgentId'], msg)

            

        
    # 写入当前时间
    key_data = {
        "detail_template_id": key['detail_template_id'],
        "last_time1": int(last_time1),
        "last_time2": int(last_time2),
        "AgentId": key['AgentId'],
        "news_template_id": key['news_template_id']
    }
    with open('./key3.yml', 'w', encoding='utf-8') as f:
        yaml.dump(data=key_data, stream=f, allow_unicode=True)

if __name__ == "__main__":
    main()