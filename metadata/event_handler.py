
import re
import asyncio
import functools

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from taskweaver.module.event_emitter import (
    SessionEventHandlerBase,
    PostEventType,
)

from taskweaver.memory.attachment import AttachmentType
from taskweaver.memory.type_vars import RoleName
from taskweaver.module.event_emitter import PostEventType, RoundEventType, SessionEventHandlerBase


def elem(name: str, cls: str = "", attr: Dict[str, str] = {}, **attr_dic: str):
    all_attr = {**attr, **attr_dic}
    if cls:
        all_attr.update({"class": cls})

    attr_str = ""
    if len(all_attr) > 0:
        attr_str += "".join(f' {k}="{v}"' for k, v in all_attr.items())

    def inner(*children: str):
        children_str = "".join(children)
        return f"<{name}{attr_str}>{children_str}</{name}>"

    return inner

def txt(content: str, br: bool = True):
    content = content.replace("<", "&lt;").replace(">", "&gt;")
    if br:
        content = content.replace("\n", "<br>")
    else:
        content = content.replace("\n", "&#10;")
    return content

div = functools.partial(elem, "div")
span = functools.partial(elem, "span")
blinking_cursor = span("tw-end-cursor")()

class CustomSessionEventHandler(SessionEventHandlerBase):
    def __init__(self, websocket):
        self.websocket = websocket
        self.message_queue = asyncio.Queue()
        self.reset_current_state()

    def reset_current_state(self):
        self.cur_attachment_list: List[Tuple[str, AttachmentType, str, bool]] = []
        self.cur_post_status: str = "Updating"
        self.cur_send_to: RoleName = "Unknown"
        self.cur_message: str = ""
        self.cur_message_is_end: bool = False
        self.cur_message_sent: bool = False

    def handle_session(self, type, msg, extra, **kwargs):
        self.queue_message("session", type, msg, extra)

    def handle_round(self, type, msg, extra, round_id, **kwargs):
        self.current_round_id = round_id
        self.queue_message("round", type, msg, extra)

    def handle_post(self, type, msg, extra, post_id, round_id, **kwargs):
        if type == PostEventType.post_start:
            self.reset_current_state()
        elif type == PostEventType.post_end:
            self.cur_message += msg
            self.queue_message("post", type, self.format_post_body(True), extra)
            self.reset_current_state()
        elif type == PostEventType.post_attachment_update:
            id: str = extra["id"]
            a_type: AttachmentType = extra["type"]
            is_end: bool = extra["is_end"]
            if len(self.cur_attachment_list) == 0 or id != self.cur_attachment_list[-1][0]:
                self.cur_attachment_list.append((id, a_type, msg, is_end))
            else:
                prev_msg = self.cur_attachment_list[-1][2]
                self.cur_attachment_list[-1] = (id, a_type, prev_msg + msg, is_end)
        elif type == PostEventType.post_send_to_update:
            self.cur_send_to = extra["role"]
        elif type == PostEventType.post_message_update:
            self.cur_message += msg
            if extra["is_end"]:
                self.cur_message_is_end = True
        elif type == PostEventType.post_status_update:
            self.cur_post_status = msg

        if not self.cur_message_is_end or not self.cur_message_sent:
            self.queue_message("post", type, self.format_post_body(False), extra)
            if self.cur_message_is_end and not self.cur_message_sent:
                self.cur_message_sent = True
                formatted_message = self.format_message(self.cur_message, True)
                self.queue_message("post", PostEventType.post_message_update, formatted_message, {"is_end": True})

    def format_post_body(self, is_end: bool) -> str:
        content_chunks: List[str] = []

        for attachment in self.cur_attachment_list:
            a_type = attachment[1]

            # skip artifact paths always
            if a_type in [AttachmentType.artifact_paths]:
                continue

            # skip Python in final result
            if is_end and a_type in [AttachmentType.python]:
                continue

            content_chunks.append(self.format_attachment(attachment))

        if self.cur_message != "":
            if self.cur_send_to == "Unknown":
                content_chunks.append("**Message**:")
            else:
                content_chunks.append(f"**Message To {self.cur_send_to}**:")

            if not self.cur_message_sent:
                content_chunks.append(
                    self.format_message(self.cur_message, self.cur_message_is_end),
                )

        if not is_end:
            content_chunks.append(
                div("tw-status")(
                    span("tw-status-updating")(
                        elem("svg", viewBox="22 22 44 44")(elem("circle")()),
                    ),
                    span("tw-status-msg")(txt(self.cur_post_status + "...")),
                ),
            )

        return "\n\n".join(content_chunks)

    
    def format_attachment(
        self,
        attachment: Tuple[str, AttachmentType, str, bool],
    ) -> str:
        id, a_type, msg, is_end = attachment
        header = div("tw-atta-header")(
            div("tw-atta-key")(
                " ".join([item.capitalize() for item in a_type.value.split("_")]),
            ),
            div("tw-atta-id")(id),
        )
        atta_cnt: List[str] = []

        if a_type in [AttachmentType.plan, AttachmentType.init_plan]:
            items: List[str] = []
            lines = msg.split("\n")
            for idx, row in enumerate(lines):
                item = row
                if "." in row and row.split(".")[0].isdigit():
                    item = row.split(".", 1)[1].strip()
                items.append(
                    div("tw-plan-item")(
                        div("tw-plan-idx")(str(idx + 1)),
                        div("tw-plan-cnt")(
                            txt(item),
                            blinking_cursor if not is_end and idx == len(lines) - 1 else "",
                        ),
                    ),
                )
            atta_cnt.append(div("tw-plan")(*items))
        elif a_type in [AttachmentType.execution_result]:
            atta_cnt.append(
                elem("pre", "tw-execution-result")(
                    elem("code")(txt(msg)),
                ),
            )
        elif a_type in [AttachmentType.python, AttachmentType.sample]:
            atta_cnt.append(
                elem("pre", "tw-python", {"data-lang": "python"})(
                    elem("code", "language-python")(txt(msg, br=False)),
                ),
            )
        else:
            atta_cnt.append(txt(msg))
            if not is_end:
                atta_cnt.append(blinking_cursor)

        return div("tw-atta")(
            header,
            div("tw-atta-cnt")(*atta_cnt),
        )
    
    def format_message(self, message: str, is_end: bool) -> str:
        content = txt(message, br=False)
        begin_regex = re.compile(r"^```(\w*)$\n", re.MULTILINE)
        end_regex = re.compile(r"^```$\n?", re.MULTILINE)

        if not is_end:
            end_tag = " " + blinking_cursor
        else:
            end_tag = ""

        while True:
            start_label = begin_regex.search(content)
            if not start_label:
                break
            start_pos = content.index(start_label[0])
            lang_tag = start_label[1]
            content = "".join(
                [
                    content[:start_pos],
                    f'<pre data-lang="{lang_tag}"><code class="language-{lang_tag}">',
                    content[start_pos + len(start_label[0]) :],
                ],
            )

            end_pos = end_regex.search(content)
            if not end_pos:
                content += end_tag + "</code></pre>"
                end_tag = ""
                break
            end_pos_pos = content.index(end_pos[0])
            content = f"{content[:end_pos_pos]}</code></pre>{content[end_pos_pos + len(end_pos[0]):]}"

        content += end_tag
        return content

    def queue_message(self, event_category, event_type, message, details):
        # Convert event_type and other non-serializable objects
        event = {
            "type": "chat_message",
            "event_category": event_category,
            "event_type": self.serialize_event_type(event_type),
            "message": message,
            "details": self.serialize_details(details)
        }
        self.message_queue.put_nowait(event)

    def serialize_event_type(self, event_type):
        # Assuming event_type is an enum or has a similar interface
        if isinstance(event_type, Enum):
            return {"name": event_type.name, "value": event_type.value}
        return {attr: self.serialize_value(getattr(event_type, attr)) for attr in dir(event_type) if not attr.startswith('_')}

    def serialize_details(self, details):
        # Similar to how Chainlit handles attachments and complex structures
        if isinstance(details, dict):
            return {k: self.serialize_value(v) for k, v in details.items()}
        return details

    def serialize_value(self, value):
        if isinstance(value, Enum):
            return value.name  # or value.value based on your needs
        if isinstance(value, dict):
            return {k: self.serialize_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.serialize_value(v) for v in value]
        if hasattr(value, '__dict__'):
            return {k: self.serialize_value(v) for k, v in value.__dict__.items() if not callable(v) and not k.startswith('_')}
        return value  # Fallback for basic types
