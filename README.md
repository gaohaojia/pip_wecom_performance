# pip_wecom_performance
PIP战队通过在ubuntu服务器上部署mysql并通过本仓库代码实现工作量自动化处理。\
PIP战队工作量管理代码。\
该代码通过调用企业微信API实现对队员工作量进行管理。\
使用需创建三个文件\
key.yml
```
corpid: 
corpsecret:
AppSecret:
AddressSecret:
AgentId:
```
key2.yml
```
last_time: 
template_id: 
```
key3.yml
```
AgentId: 
detail_template_id: 
news_template_id: 
last_time1: 
last_time2: 
```
然后在enrollment.py，push.py，reply.py文件中填写mysql数据库的账号、密码、数据库名称等信息，详情位置请自行查看代码。
