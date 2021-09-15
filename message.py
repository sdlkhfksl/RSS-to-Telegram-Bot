import telegram.error
import time
import logging
from typing import List, Union, Optional, Tuple

from medium import Medium
import env


class Message:
    retry_after: Union[float, int] = 0.0

    def __init__(self,
                 text: Optional[str] = None,
                 media: Optional[Union[List[Medium], Tuple[Medium], Medium]] = None,
                 parse_mode: Optional[str] = 'HTML'):
        self.text = text
        self.media = media
        self.parse_mode = parse_mode
        self.retries = 0

    def send(self, chat_id: Union[str, int]):
        if self.retries >= 3:
            logging.warning('Retried too many times! Message dropped!')
            raise OverflowError
        sleep_time = Message.retry_after - time.time()
        if sleep_time > 0:
            time.sleep(sleep_time + 1)
        try:
            self._send(chat_id)
            self.retries = 0
        except telegram.error.RetryAfter as e:  # exceed flood control
            logging.debug(e.message)
            self.retries += 1
            Message.retry_after = time.time() + e.retry_after
            self.send(chat_id)
        except telegram.error.BadRequest as e:
            raise e
        except telegram.error.NetworkError as e:
            logging.warning(f'Network error({e.message}). Retrying...')
            self.retries += 1
            time.sleep(1)
            self.send(chat_id)

    def _send(self, chat_id: Union[str, int]):
        pass


class TextMsg(Message):
    def _send(self, chat_id: Union[str, int]):
        env.bot.send_message(chat_id, self.text, parse_mode=self.parse_mode, disable_web_page_preview=True)


class PhotoMsg(Message):
    def _send(self, chat_id: Union[str, int]):
        env.bot.send_photo(chat_id, self.media.get_url(), caption=self.text, parse_mode=self.parse_mode)


class VideoMsg(Message):
    def _send(self, chat_id: Union[str, int]):
        env.bot.send_video(chat_id, self.media.get_url(), caption=self.text, parse_mode=self.parse_mode)


class AnimationMsg(Message):
    def _send(self, chat_id: Union[str, int]):
        env.bot.send_animation(chat_id, self.media.get_url(), caption=self.text, parse_mode=self.parse_mode)


class MediaGroupMsg(Message):
    def _send(self, chat_id: Union[str, int]):
        media_list = list(map(lambda m: m.telegramize(), self.media))
        media_list[0].caption = self.text
        media_list[0].parse_mode = self.parse_mode
        env.bot.send_media_group(chat_id, media_list)
