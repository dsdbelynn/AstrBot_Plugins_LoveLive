from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import aiohttp
import json

@register("LoveLive", "Lynn", "一个简单的插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    
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
                        # 根据API文档，Json格式会在returnObj中包含Array<string>
                        if 'returnObj' in data and isinstance(data['returnObj'], list) and len(data['returnObj']) > 0:
                            return data['returnObj'][0]  # 返回第一个结果
                        else:
                            return "发生错误"
                    else:
                        logger.error(f"API请求失败，状态码: {response.status}")
                        return "发生错误"
        except Exception as e:
            logger.error(f"API调用异常: {e}")
            return "发生错误"
            
    @filter.command("渣男语录")
    async def sweetNothing_F(self, event: AstrMessageEvent):
        ret = await self.get_sweet_nothing("M")  # M代表渣男
        yield event.plain_result(ret)

    @filter.command("渣女语录")
    async def sweetNothing_m(self, event: AstrMessageEvent):
        ret = await self.get_sweet_nothing("F")  # F代表绿茶/渣女
        yield event.plain_result(ret)
