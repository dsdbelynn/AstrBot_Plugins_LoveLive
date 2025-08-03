from astrbot.api.event import MessageChain
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import aiohttp
import json
import asyncio
import os
from datetime import datetime, timezone, timedelta

# 全局变量
API_KEY = None
API_KEY_PATH = "/AstrBot/data/API_KEY"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

SUBSCRIBERS_FILE_PATH = "/AstrBot/data/subscribers.json"

@register("LoveLive", "Lynn", "一个简单的插件", "1.0.9")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.check_api_key()
        self.context = context
        self.subscribers = []  # 存储从文件读取的订阅者列表
        # 启动定时任务
        asyncio.create_task(self.start_scheduled_tasks())



    def check_api_key(self):
        """检查API_KEY文件，读取到全局变量中，没有则创建并填入123"""
        global API_KEY  # 添加这行
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(API_KEY_PATH), exist_ok=True)
            
            if os.path.exists(API_KEY_PATH):
                # 文件存在，读取内容
                with open(API_KEY_PATH, 'r', encoding='utf-8') as f:
                    API_KEY = f.read().strip() or "123"
            else:
                # 文件不存在，创建并填入默认值
                with open(API_KEY_PATH, 'w', encoding='utf-8') as f:
                    f.write("123")
                API_KEY = "123"
            
        except Exception:
            # 异常时使用默认值
            API_KEY = "123"
        

    def build_sweet_nothing_prompt(gender_type: str, time_period: str, count: int) -> str:
        """构建针对不同时间段的提示词"""
        
        time_greetings = {
            "morning": "早安",
            "noon": "午安", 
            "evening": "晚安"
        }
        
        time_contexts = {
            "morning": "刚起床，想要一些温暖甜蜜的话语开始新的一天",
            "noon": "中午休息时间，需要一些关怀和调情的话语",
            "evening": "夜晚来临，想要一些浪漫暧昧的晚安话语"
        }
        
        greeting = time_greetings.get(time_period, "你好")
        context = time_contexts.get(time_period, "日常聊天")
        
        if gender_type == "F":  # 渣女/绿茶
            persona = "作为一个很会撩人的海王渣女"
        else:  # 渣男
            persona = "作为一个油嘴滑舌的渣男"
        
        prompt = f"""
        {persona}，现在是{time_period}时间段，{context}。
        请生成{count}句适合发给暧昧对象的{greeting}语录。
        要求：
        1. 语言要甜腻、暧昧、有套路感
        2. 要体现出海王/渣的特质（暧昧但不承诺）
        3. 符合{time_period}的时间氛围
        4. 每句话控制在20字以内
        5. 只返回语录内容，不需要其他解释
        """
        
        return prompt
    async def get_sweet_nothing_deepseek(self, gender_type: str, time_period: str, count: int = 1) -> str:
        """
        调用DeepSeek API生成渣男/渣女语录
        gender_type: "M" 为渣男, "F" 为绿茶/渣女  
        time_period: "morning" 早上, "noon" 中午, "evening" 晚上
        count: 获取数量，默认为1
        """
        
        # 构建提示词
        prompt = build_sweet_nothing_prompt(gender_type, time_period, count)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system", 
                    "content": "你是一个很会说话的海王渣女，擅长用各种甜言蜜语和套路。回复要简短精炼，一句话即可。"
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": 100,
            "temperature": 0.8
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    DEEPSEEK_API_URL, 
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'choices' in data and len(data['choices']) > 0:
                            content = data['choices'][0]['message']['content'].strip()
                            return content
                        else:
                            return "今天心情不好，不想说话~"
                    else:
                        logger.error(f"DeepSeek API请求失败，状态码: {response.status}")
                        return "网络有点问题呢，待会再撩你~"
        except Exception as e:
            logger.error(f"DeepSeek API调用异常: {e}")
            return "哎呀，出了点小状况~"
    
    async def get_sweet_nothing(self, gender_type: str, count: int = 1) -> str:
        """
        调用API获取渣男/渣女语录
        gender_type: "M" 为渣男, "F" 为绿茶/渣女
        count: 获取数量，默认为1
        """
        url = f"https://api.lovelive.tools/api/SweetNothings/{count}/Serialization/Json?genderType={gender_type}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'returnObj' in data and isinstance(data['returnObj'], list) and len(data['returnObj']) > 0:
                            return data['returnObj'][0]
                        else:
                            return "发生错误"
                    else:
                        logger.error(f"API请求失败，状态码: {response.status}")
                        return "发生错误"
        except Exception as e:
            logger.error(f"API调用异常: {e}")
            return "发生错误"
    
    async def load_subscribers(self):
        """
        从JSON文件加载订阅者列表
        """
        try:
            if os.path.exists(SUBSCRIBERS_FILE_PATH):
                with open(SUBSCRIBERS_FILE_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 假设JSON文件格式为 {"subscribers": ["user1", "user2", ...]} 或者直接是数组
                    if isinstance(data, dict) and 'subscribers' in data:
                        self.subscribers = data['subscribers']
                    elif isinstance(data, list):
                        self.subscribers = data
                    else:
                        self.subscribers = []
                    logger.info(f"已加载 {len(self.subscribers)} 个订阅者")
            else:
                self.subscribers = []
                logger.info(f"订阅者文件不存在: {SUBSCRIBERS_FILE_PATH}")
        except Exception as e:
            logger.error(f"加载订阅者列表失败: {e}")
            self.subscribers = []
    
    async def send_scheduled_message(self, greeting: str):
        """
        发送定时消息的函数
        """
        try:
            # 获取渣女语录
            quote = await self.get_sweet_nothing("F")
            # 修改格式：同一行显示，用逗号分隔
            message_text = f"{greeting}，{quote}"
            
            # 发送前更新订阅者列表
            await self.load_subscribers()
            
            # 使用提供的消息发送接口
            if self.subscribers:
                message_chain = MessageChain().message(message_text)
                for sub in self.subscribers:
                    await self.context.send_message(sub, message_chain)
                    await asyncio.sleep(1)  # 延时1秒钟
                
                logger.info(f"定时消息已发送给 {len(self.subscribers)} 个订阅者: {message_text}")
            else:
                logger.info("没有订阅者，跳过发送定时消息")
            
        except Exception as e:
            logger.error(f"发送定时消息失败: {e}")
    
    async def start_scheduled_tasks(self):
        """
        启动定时任务
        """
        logger.info("定时任务已启动")
        
        while True:
            try:
                # 获取当前UTC+8时间
                utc8_tz = timezone(timedelta(hours=8))
                current_time = datetime.now(utc8_tz)
                current_hour = current_time.hour
                current_minute = current_time.minute
                
                # 检查是否为指定时间点（精确到分钟）
                if current_minute == 0:  # 整点时执行
                    if current_hour == 9:
                        await self.send_scheduled_message("早上好")
                    elif current_hour == 12:
                        await self.send_scheduled_message("中午好")
                    elif current_hour == 23:
                        await self.send_scheduled_message("晚上好")
                
                # 等待60秒后再次检查
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"定时任务执行错误: {e}")
                await asyncio.sleep(60)
    
    @filter.command("渣男语录")
    async def sweetNothing_F(self, event: AstrMessageEvent):
        ret = await self.get_sweet_nothing("M")
        yield event.plain_result(ret)

    @filter.command("渣女语录")
    async def sweetNothing_m(self, event: AstrMessageEvent):
        ret = await self.get_sweet_nothing("F")
        yield event.plain_result(ret)
        
    @filter.command("测试")
    async def sweetNothing_Hello(self, event: AstrMessageEvent):
        from datetime import datetime, timezone, timedelta
        
        # 获取当前UTC+8时间（北京时间）
        utc8_tz = timezone(timedelta(hours=8))
        current_time = datetime.now(utc8_tz)
        
        # 格式化时间为指定格式：2025/08/04 02:01:01
        time_str = current_time.strftime("%Y/%m/%d %H:%M:%S")
        
        # 获取渣女语录
        quote = await self.get_sweet_nothing("F")
        
        # 组合当前时间和渣女语录
        ret = f"{time_str}\n{quote}"
        yield event.plain_result(ret)

    @filter.command("测试d")
    async def sweetNothing_Hello(self, event: AstrMessageEvent):
        from datetime import datetime, timezone, timedelta
        
        # 获取当前UTC+8时间（北京时间）
        utc8_tz = timezone(timedelta(hours=8))
        current_time = datetime.now(utc8_tz)
        
        # 格式化时间为指定格式：2025/08/04 02:01:01
        time_str = current_time.strftime("%Y/%m/%d %H:%M:%S")
        
        # 获取渣女语录
        quote = await self.get_sweet_nothing_deepseek("F")
        
        # 组合当前时间和渣女语录
        ret = f"{time_str}\n{quote}"
        yield event.plain_result(ret)

    @filter.command("测试定时消息")
    async def test_scheduled_message(self, event: AstrMessageEvent):
        """
        测试定时消息功能（发送给所有订阅者）
        """
        try:
            # 获取当前UTC+8时间
            utc8_tz = timezone(timedelta(hours=8))
            current_time = datetime.now(utc8_tz)
            
            # 格式化时间
            time_str = current_time.strftime("%Y/%m/%d %H:%M:%S")
            
            # 获取渣女语录
            quote = await self.get_sweet_nothing("F")
            
            # 组合消息：时间 + 早上好中午好晚上好 + 【渣女语录】
            message_text = f"{time_str} 早上好中午好晚上好，【{quote}】"
            
            # 发送前更新订阅者列表
            await self.load_subscribers()
            
            # 发送给所有订阅者
            if self.subscribers:
                message_chain = MessageChain().message(message_text)
                for sub in self.subscribers:
                    await self.context.send_message(sub, message_chain)
                    await asyncio.sleep(1)  # 延时1秒钟
                
                ret = f"测试消息已发送给 {len(self.subscribers)} 个订阅者\n内容: {message_text}"
            else:
                ret = "没有订阅者，无法发送测试消息"
            
            yield event.plain_result(ret)
            
        except Exception as e:
            logger.error(f"发送测试消息失败: {e}")
            yield event.plain_result(f"发送测试消息失败: {e}")
            
    @filter.command("测试定时消息d")
    async def test_scheduled_message(self, event: AstrMessageEvent):
        """
        测试定时消息功能（发送给所有订阅者）
        """
        try:
            # 获取当前UTC+8时间
            utc8_tz = timezone(timedelta(hours=8))
            current_time = datetime.now(utc8_tz)
            
            # 格式化时间
            time_str = current_time.strftime("%Y/%m/%d %H:%M:%S")
            
            # 获取渣女语录
            quote = await self.get_sweet_nothing_deepseek("F")
            
            # 组合消息：时间 + 早上好中午好晚上好 + 【渣女语录】
            message_text = f"{time_str} 早上好中午好晚上好，【{quote}】"
            
            # 发送前更新订阅者列表
            await self.load_subscribers()
            
            # 发送给所有订阅者
            if self.subscribers:
                message_chain = MessageChain().message(message_text)
                for sub in self.subscribers:
                    await self.context.send_message(sub, message_chain)
                    await asyncio.sleep(1)  # 延时1秒钟
                
                ret = f"测试消息已发送给 {len(self.subscribers)} 个订阅者\n内容: {message_text}"
            else:
                ret = "没有订阅者，无法发送测试消息"
            
            yield event.plain_result(ret)
            
        except Exception as e:
            logger.error(f"发送测试消息失败: {e}")
            yield event.plain_result(f"发送测试消息失败: {e}")

            

        
