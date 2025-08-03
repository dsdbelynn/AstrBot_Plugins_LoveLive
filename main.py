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

@register("LoveLive", "Lynn", "一个简单的插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.check_api_key()
        self.context = context
        self.subscribers = []  # 存储从文件读取的订阅者列表
        # 启动定时任务
        #asyncio.create_task(self.start_scheduled_tasks())
        asyncio.create_task(self.start_scheduled_tasks_d())



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
        

    def build_sweet_nothing_prompt(self, gender_type: str, time_period: str, count: int) -> str:
        """构建针对不同时间段的提示词"""
        
        time_greetings = {
            "morning": "早安",
            "noon": "午安", 
            "evening": "晚安"
        }
        
        time_contexts = {
            "morning": "新的一天开始了，需要一些充满活力的鼓励话语",
            "noon": "中午休息时间，适合关怀体贴地询问吃饭和休息情况",
            "evening": "夜晚来临，该关心对方早点休息了"
        }
        
        time_specific = {
            "morning": "充满正能量，鼓励对方开启美好的一天",
            "noon": "温柔询问是否按时吃饭，提醒适当休息",
            "evening": "温馨提醒早点睡觉，关心对方的健康作息"
        }
        
        greeting = time_greetings.get(time_period, "你好")
        context = time_contexts.get(time_period, "日常聊天")
        specific_care = time_specific.get(time_period, "日常关怀")
        
        if gender_type == "F":  # 知心姐姐
            persona = "温柔体贴的知心姐姐"
        else:  # 暖男
            persona = "贴心温暖的暖男"
        
        prompt = f"""
        你是一个{persona}，现在是{time_period}时间段，{context}。
        请生成{count}句{greeting}问候语。
        
        **人设特点：**
        - 很会关心人，善于察觉对方的需要
        - 说话温柔亲切，让人感到被关爱
        - 懂得在合适的时候给予鼓励和关怀
        - 语气自然不做作，像真正的好朋友
        
        **语言风格：**
        - 称呼对方为宝宝
        - 温暖贴心，多用"呀"、"呢"、"哦"等亲切语气词
        - 适当使用emoji表情增加温暖感
        - 语言简洁明了，不过分甜腻
        - 体现真诚的关心和在意
        
        **针对{time_period}时段的要求：**
        - {specific_care}
        - 语气要符合{time_period}的氛围
        - 让人感受到被关心和温暖
        
        请生成一句温暖贴心的{greeting}话语，要自然真诚，不要过于夸张。
        """
        
        return prompt

    async def get_sweet_nothing_deepseek(self, gender_type: str, time_period: str, count: int = 1) -> str:
        """
        调用DeepSeek API生成温暖关怀的问候语
        gender_type: "M" 为暖男, "F" 为知心姐姐
        time_period: "morning" 早上, "noon" 中午, "evening" 晚上
        count: 获取数量，默认为1
        """
        
        # 构建提示词
        prompt = self.build_sweet_nothing_prompt(gender_type, time_period, count)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system", 
                    "content": "你是一个温暖贴心的知心姐姐，很会关心别人。说话自然亲切，像真正的好朋友一样。**每次回复都要用不同的表达方式，避免重复**。回复要简短温暖，一句话即可。"
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": 100,
            "temperature": 0.9,
            "top_p": 0.9,        # 添加这个参数
            "frequency_penalty": 0.3,  # 降低重复内容的概率
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
                            return "今天有点忙呢，待会再聊~"
                    else:
                        logger.error(f"DeepSeek API请求失败，状态码: {response.status}")
                        return "网络好像有点问题，稍后再试试~"
        except Exception as e:
            logger.error(f"DeepSeek API调用异常: {e}")
            return "哎呀，出了点小状况呢~"
    
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

    async def send_scheduled_message_d(self, time_period: str):
        """
        发送定时消息的函数（使用DeepSeek API）
        """
        try:
            # 调用deepseek获取问候语（已包含greeting）
            quote = await self.get_sweet_nothing_deepseek("F", time_period)
            
            # 发送前更新订阅者列表
            await self.load_subscribers()
            
            # 使用提供的消息发送接口
            if self.subscribers:
                message_chain = MessageChain().message(quote)
                for sub in self.subscribers:
                    await self.context.send_message(sub, message_chain)
                    await asyncio.sleep(1)  # 延时1秒钟
                
                logger.info(f"定时消息已发送给 {len(self.subscribers)} 个订阅者: {quote}")
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

    async def start_scheduled_tasks_d(self):
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
                if current_hour == 9:
                    await self.send_scheduled_message_d("morning")
                elif current_hour == 12:
                    await self.send_scheduled_message_d("noon")
                elif current_hour == 23:
                    await self.send_scheduled_message_d("evening")                
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
    async def sweetNothing_Hello_d(self, event: AstrMessageEvent, message: str):
        from datetime import datetime, timezone, timedelta
        
        # 检查参数是否正确
        valid_periods = ["morning", "noon", "evening"]
        if message not in valid_periods:
            ret = "参数错误"
            yield event.plain_result(ret)
            return
        
        # 获取当前UTC+8时间（北京时间）
        utc8_tz = timezone(timedelta(hours=8))
        current_time = datetime.now(utc8_tz)
        
        # 格式化时间为指定格式：2025/08/04 02:01:01
        time_str = current_time.strftime("%Y/%m/%d %H:%M:%S")
        
        # 获取渣女语录，传入时间段参数
        quote = await self.get_sweet_nothing_deepseek("F", message)
        
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
    async def test_scheduled_message_d(self, event: AstrMessageEvent, message: str):
        """
        测试定时消息功能（发送给所有订阅者）
        """
        # 检查参数是否正确
        valid_periods = ["morning", "noon", "evening"]
        if message not in valid_periods:
            ret = "参数错误"
            yield event.plain_result(ret)
            return
        try:
            # 获取当前UTC+8时间
            utc8_tz = timezone(timedelta(hours=8))
            current_time = datetime.now(utc8_tz)
            
            # 格式化时间
            time_str = current_time.strftime("%Y/%m/%d %H:%M:%S")
            
            # 获取渣女语录
            quote = await self.get_sweet_nothing_deepseek("F", message)
            
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

            

        
