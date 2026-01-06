import http.client
import json

conn = http.client.HTTPSConnection("www.runninghub.cn")
payload = json.dumps({
   "apiKey": "请输入自己的apiKey",
   "workflowId": "1904136902449209346",
   "nodeInfoList": [
      {
         "nodeId": "6",
         "fieldName": "text",
         "fieldValue": "1 girl in classroom"
      }
   ]
})
headers = {
   'Host': 'www.runninghub.cn',
   'Content-Type': 'application/json'
}
conn.request("POST", "/task/openapi/create", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))