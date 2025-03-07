from pathlib import Path
from loguru import logger

import tomli as tomllib


def check_config(config):
    from schema import And, Optional, Or, Regex, Schema, SchemaError, Use

    PositiveInt = lambda: And(Use(int), lambda n: n > 0)
    schema = Schema(
        {
            Optional("timeout"): PositiveInt(),
            Optional("retries"): PositiveInt(),
            Optional("concurrent"): PositiveInt(),
            Optional("random"): PositiveInt(),
            Optional("notifier"): Or(str, bool),
            Optional("nofail"): bool,
            Optional("proxy"): Schema(
                {
                    Optional("hostname"): Regex(
                        r"^(?=.{1,255}$)[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?(?:\.[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?)*\.?$"
                    ),
                    Optional("port"): And(Use(int), lambda n: n > 1024 and n < 65536),
                    Optional("scheme"): Schema(Or("socks5", "http")),
                }
            ),
            Optional("service"): Schema(
                {
                    Optional("checkiner"): [Use(str)],
                    Optional("monitor"): [Use(str)],
                    Optional("messager"): [Use(str)],
                }
            ),
            Optional("telegram"): [
                Schema(
                    {
                        "api_id": Regex(r"^\d+$"),
                        "api_hash": Regex(r"^[a-z0-9]+$"),
                        "phone": Use(str),
                        Optional("monitor"): bool,
                        Optional("send"): bool,
                    }
                )
            ],
            Optional("emby"): [
                Schema(
                    {
                        "url": Regex(
                            r"(http|https):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])"
                        ),
                        "username": Use(str),
                        "password": Use(str),
                        Optional("time"): PositiveInt(),
                        Optional("progress"): PositiveInt(),
                    }
                )
            ],
        }
    )
    try:
        schema.validate(config)
    except SchemaError as e:
        logger.error(f"配置文件错误, 请检查配置文件:\n{e}.")
        return False
    return True


def write_faked_config(path):
    import uuid

    from tomlkit import document, nl, comment, item, dump, table
    from faker import Faker
    from faker.providers import internet, profile

    from .telechecker.main import get_names
    from . import __name__, __version__

    fake = Faker()
    fake.add_provider(internet)
    fake.add_provider(profile)

    doc = document()
    doc.add(comment("This is an example config file."))
    doc.add(comment("Please fill in your account information."))
    doc.add(comment("See details: https://github.com/embykeeper/embykeeper#安装与使用"))
    doc.add(nl())
    doc.add(comment("每个 Telegram Bot 签到的最大尝试时间."))
    doc["timeout"] = 120
    doc.add(nl())
    doc.add(comment("每个 Telegram Bot 签到的最大尝试次数."))
    doc["retries"] = 10
    doc.add(nl())
    doc.add(comment("最大可同时进行的 Telegram Bot 签到."))
    doc["concurrent"] = 1
    doc.add(nl())
    doc.add(comment("计划任务时, 各签到器启动前等待的随机时间 (分钟)."))
    doc["random"] = 15
    doc["proxy"] = {
        "hostname": "127.0.0.1",
        "port": "1080",
        "scheme": "socks5",
    }
    doc["proxy"]["scheme"].comment("可选: http / socks5")
    doc.add(nl())
    doc.add(comment(f"服务设置, 当您需要禁用某些站点时, 请将该段取消注释并修改."))
    doc.add(comment(f"该部分内容是根据 {__name__.capitalize()} {__version__} 生成的."))
    service = item(
        {
            "service": {
                "checkiner": get_names("checkiner"),
                "monitor": get_names("monitor"),
                "messager": get_names("messager"),
            }
        }
    )
    for line in service.as_string().strip().split("\n"):
        doc.add(comment(line))
    doc.add(nl())
    doc.add(comment("Telegram 账号设置, 您可以重复该片段多次以增加多个账号."))
    telegram = []
    for _ in range(2):
        t = item(
            {
                "api_id": fake.numerify(text="########"),
                "api_hash": uuid.uuid4().hex,
                "phone": f'+861{fake.numerify(text="##########")}',
                "send": False,
                "monitor": False,
            }
        )
        t["api_id"].comment("通过 Telegram 官网申请 API: https://my.telegram.org/")
        t["api_hash"].comment("通过 Telegram 官网申请 API: https://my.telegram.org/")
        telegram.append(t)
    doc["telegram"] = telegram
    for t in doc["telegram"]:
        t.value.item("send").comment("启用该账号的自动水群功能 (需要高级账号)")
        t.value.item("monitor").comment("启用该账号的自动监控功能 (需要高级账号)")
    doc.add(nl())
    doc.add(comment("Emby 账号设置, 您可以重复该片段多次以增加多个账号."))
    emby = []
    for _ in range(2):
        t = item(
            {
                "url": fake.url(["https"]),
                "username": fake.profile()["username"],
                "password": fake.password(),
                "time": 800,
                "progress": 1000,
            }
        )
        t["time"].comment("模拟观看的时长 (秒)")
        t["progress"].comment("模拟观看后设置的时间进度 (秒)")
        emby.append(t)
    doc["emby"] = emby
    with open(path, "w+") as f:
        dump(doc, f)


def prepare_config(config=None):
    if not config:
        logger.warning("需要输入一个toml格式的config文件.")
        default_config = "config.toml"
        if not Path(default_config).exists():
            write_faked_config(default_config)
            logger.warning(f'您可以根据生成的参考配置文件 "{default_config}" 进行配置')
        return
    with open(config, "rb") as f:
        config = tomllib.load(f)
    if not check_config(config):
        return
    proxy = config.get("proxy", None)
    if proxy:
        proxy.setdefault("scheme", "socks5")
        proxy.setdefault("hostname", "127.0.0.1")
        proxy.setdefault("port", "1080")
    return config
