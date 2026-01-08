curl --request POST \
  --url http://ai-api.jdcloud.com/v1/images/gemini_flash/generations \
  --header 'Accept: */*' \
  --header 'Accept-Encoding: gzip, deflate, br' \
  --header 'Authorization: Bearer pk*****' \
  --header 'Connection: keep-alive' \
  --header 'Content-Type: application/json' \
  --header 'Trace-id: test-gemini-23' \
  --data '{
    "model": "Gemini 3-Pro-Image-Preview",
    "contents": {
        "role": "USER",
        "parts": [
            {
                "file_data": {
                    "mime_type": "image/png",
                    "file_uri": "https://maas.s3.cn-north-1.jdcloud-oss.com/ERNIE-4.5-turbo-128K/baidu.png"
                }
            },
            {
                "text": "Convert this photo to black and white, in a cartoonish style."
            }
        ]
    },
    "generation_config": {
        "response_modalities": [
            "TEXT",
            "IMAGE"
        ]
    },
    "safety_settings": {
        "method": "PROBABILITY",
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    "stream": true
}'