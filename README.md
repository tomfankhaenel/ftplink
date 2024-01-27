# Origin
Imagine you have multiple surveillance cameras and want to know when something is moving or happening. 
The cameras only offer builtin push notification for an app you dont want to use and the only other options are smtp and ftp uploads.
All the cameras are connected via a raspberry to the internet. Your prefered way of notification is telegram (a chat app on the smartphone that supports bots).

# What ftplink does
- setup a ftp server in python
- upload of any picture/video will be forward to a specific telegram group using a bot token


## local docker example:
```
docker run -it --rm -e bot_token="xxx:xxx" -e group_chat_id="-123" -p21:2121 -p60000-60010:60000-60010 ftp
``` 

## docker-compose example:
```
version: '3'

services:
  awsdomain:
  image: tomfankhaenel/route53-dyndns:1.0.0
  restart: always
  environment:
    - ROUTE53_ZONE=$ZONEID
    - ROUTE53_RECORDS=record.,*.record2.
    - AWS_ACCESS_KEY_ID=$KEY
    - AWS_SECRET_ACCESS_KEY=$SECRET
```
