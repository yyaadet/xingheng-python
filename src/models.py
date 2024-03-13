from dataclasses import dataclass


@dataclass
class Task:
    id: int = -1
    title: str = ""
    status: int = 0
    tomato_minute: int = 25
    project: str = ""
    opening_tomato_id: int = -1
    opening_tomato_left_seconds: int = 0
    last_update_datetime: str = ''
    dead_datetime: str = ""
    expect_tomato_number: int = 0
    tomato_number: int = 0


@dataclass
class User:
    uid: int = 0
    username: str = ''
    sex_name: str = ''
    left_tomato_number: int = 0
    email: str = ''
    upload_header_url: str = ''
    is_vip: bool = False
    today_tomato_count: int =0

    