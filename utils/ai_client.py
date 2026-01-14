#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JD Cloud AI API 客户端
替代 OpenAI SDK，使用 JD Cloud AI API
"""

import requests
import json
from typing import Dict, List, Optional


class AIClient:
    """JD Cloud AI API 客户端"""
    
    def __init__(self, api_url: str, api_key: str):
        """
        初始化客户端
        
        Args:
            api_url: API 地址
            api_key: API 密钥
        """
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Authorization": f"Bearer {self.api_key}",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "User-Agent": "JoyIP-3D-System/1.0"
        }
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gemini_flash",
        temperature: float = 0.3,
        max_tokens: int = 300
    ) -> Optional[str]:
        """
        调用聊天补全 API
        
        Args:
            messages: 消息列表，格式 [{"role": "system/user/assistant", "content": "..."}]
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            str: AI 返回的文本内容，失败返回 None
        """
        try:
            # 构建请求体
            payload = {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # 发送请求
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            # 检查响应
            if response.status_code == 200:
                result = response.json()
                
                # 解析响应格式（根据实际 API 返回格式调整）
                # 假设返回格式类似 OpenAI: {"choices": [{"message": {"content": "..."}}]}
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                elif "content" in result:
                    return result["content"]
                elif "text" in result:
                    return result["text"]
                else:
                    print(f"未知的响应格式: {result}")
                    return None
            else:
                print(f"API 请求失败: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print("API 请求超时")
            return None
        except requests.exceptions.RequestException as e:
            print(f"API 请求异常: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {str(e)}")
            return None
        except Exception as e:
            print(f"未知错误: {str(e)}")
            return None


# 兼容 OpenAI SDK 的包装类
class ChatCompletion:
    """兼容 OpenAI SDK 的聊天补全类"""
    
    def __init__(self, client: AIClient):
        self.client = client
    
    def create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 300
    ):
        """
        创建聊天补全（兼容 OpenAI SDK 接口）
        
        Returns:
            包含 choices 属性的对象
        """
        content = self.client.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # 返回兼容 OpenAI 格式的对象
        class Choice:
            def __init__(self, content):
                self.message = type('Message', (), {'content': content or ""})()
        
        class Response:
            def __init__(self, content):
                self.choices = [Choice(content)]
        
        return Response(content)


class Chat:
    """兼容 OpenAI SDK 的 Chat 类"""
    
    def __init__(self, client: AIClient):
        self.completions = ChatCompletion(client)


class OpenAICompatibleClient:
    """兼容 OpenAI SDK 的客户端（用于最小化代码修改）"""
    
    def __init__(self, api_url: str, api_key: str):
        """
        初始化兼容客户端
        
        Args:
            api_url: API 地址
            api_key: API 密钥
        """
        self.ai_client = AIClient(api_url, api_key)
        self.chat = Chat(self.ai_client)
