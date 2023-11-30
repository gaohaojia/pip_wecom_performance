import os
import time
import requests
import yaml

# 读取信息
with open('./key.yml', 'r', encoding='utf-8') as f:
    key = yaml.load(f.read(), Loader=yaml.FullLoader)

# 获取access_token
def get_access_token(corpid, corpsecret):
    url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={}&corpsecret={}".format(corpid, corpsecret)
    response = requests.get(url)
    data = response.json()
    access_token = data['access_token']
    return access_token

def main():
    cnt = 0
    # 获取access_token
    app_access_token = get_access_token(key['corpid'], key['AppSecret'])
    access_token = get_access_token(key['corpid'], key['corpsecret'])
    while True:
        time.sleep(5)
        cnt += 1
        
        # 点击回复脚本
        try:
            os.system("python3 reply.py {} {}".format(app_access_token, access_token))
            print("[{}]审批回复脚本执行成功。".format(round(time.time())))
        except:
            print("[{}]审批回复脚本执行失败！".format(round(time.time())))
            
        if cnt >= 1000:
            # 获取access_token
            app_access_token = get_access_token(key['corpid'], key['AppSecret'])
            access_token = get_access_token(key['corpid'], key['corpsecret'])
            cnt = 0
        

if __name__ == "__main__":
    main()