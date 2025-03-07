from pyrogram.types import Message

from .base import Monitor


class BGKMonitor(Monitor):
    name = "不给看"
    chat_name = "Ephemeralemby"
    chat_keyword = r"(?:^|\s)([a-zA-Z0-9]{32})(?!\S)"
    bot_username = "UnknownEmbyBot"

    async def on_trigger(self, message: Message, keys, reply):
        await self.client.send_message(self.bot_username, "/invite")
        await self.client.send_message(self.bot_username, keys[0])
        self.log.bind(notify=True).info(f'已向Bot发送邀请码: "{keys[0]}", 请查看.')
