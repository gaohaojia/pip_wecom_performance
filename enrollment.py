import requests
import yaml
import time
import pymysql
import sys

# 读取信息
with open('./key2.yml', 'r', encoding='utf-8') as f:
    key = yaml.load(f.read(), Loader=yaml.FullLoader)

# 获取access_token
def get_access_token(corpid, corpsecret):
    url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={}&corpsecret={}".format(corpid, corpsecret)
    response = requests.get(url)
    data = response.json()
    access_token = data['access_token']
    return access_token

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

# 插入数据
def insert_sql(connection, cursor, name_id, start_date, event, total_time):
    sql = 'INSERT INTO time_event (member_name, start_date, event, event_time) VALUES ({}, \'{}\', \'{}\', {});'.format(name_id, start_date, event, total_time)
    cursor.execute(sql)
    connection.commit()

def main():
    last_time = key['last_time']

    now_time = time.time()
    
    access_token = sys.argv[1]

    sp_no_list = get_sp_no_list(access_token, key['template_id'], last_time, now_time, "")
    if len(sp_no_list) == 0:
        print("无审批")
        return

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

    # 判断审批是否都处理
    all_data = []
    is_all_done = True
    for sp_no in sp_no_list:
        data = get_approval_data(access_token, sp_no)
        if data['sp_status'] == 1:
            is_all_done = False
            break
        if data['sp_status'] != 2:
            continue
        all_data.append(data)
    
    # 若存在未处理审批则退出
    if not is_all_done:
        print("存在未处理审批！")
        return

    # 遍历审批列表
    for data in all_data:
        user_name = get_name(access_token, data['applyer']['userid'])
        user_sql_id = get_sql_id(cursor, user_name)
        for content_data in data['apply_data']['contents'][1]['value']['children']:
            event = content_data['list'][0]['value']['text']
            start_time = content_data['list'][1]['value']['date_range']['new_begin']
            start_date = time.strftime("%Y/%m/%d", time.localtime(start_time))
            total_time = content_data['list'][1]['value']['date_range']['new_duration'] / 3600.0
            if total_time <= 0:
                continue
            insert_sql(connection, cursor, user_sql_id, start_date, event, total_time)

    # 写入当前时间
    key_data = {
        "template_id": key['template_id'],
        "last_time": int(now_time)
    }
    with open('./key2.yml', 'w', encoding='utf-8') as f:
        yaml.dump(data=key_data, stream=f, allow_unicode=True)
    last_time = now_time

if __name__ == "__main__":
    main()