import aiohttp
import asyncio
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import quote, unquote, urlparse
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.star import Context, Star
from astrbot.api import logger

# 东八区时区
CST = timezone(timedelta(hours=8))

# HTML 模板用于文转图渲染
ELECT_HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,1,0" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Google Sans', 'Noto Sans SC', 'PingFang SC', -apple-system, 'Microsoft YaHei', sans-serif;
            background: #EDF5F7;
            padding: 24px;
            min-height: 100vh;
            width: fit-content;  /* 宽度适应内容 */
            display: flex;
            align-items: flex-start;
            justify-content: flex-start;
        }

        .container {
            background: #FEFEFE;
            border-radius: 36px;
            padding: 0;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05),
                        0 4px 12px rgba(0, 0, 0, 0.06);
            width: 630px;
            min-height: 870px;
            overflow: hidden;
            margin: 0;
        }

        .header {
            background: #C5DDE8;
            padding: 36px 36px 30px;
            text-align: center;
        }

        .title {
            font-size: 48px;
            font-weight: 500;
            color: #2D4356;
            letter-spacing: -0.75px;
            margin-bottom: 9px;
        }

        .subtitle {
            font-size: 24px;
            font-weight: 400;
            color: #5A6C7D;
            letter-spacing: 0.375px;
        }

        .content {
            padding: 30px 36px 36px;
        }

        .balance-card {
            background: #E8F3F8;
            border-radius: 27px;
            padding: 33px;
            margin-bottom: 24px;
        }

        .balance-label {
            font-size: 22.5px;
            font-weight: 500;
            color: #5A6C7D;
            letter-spacing: 0.75px;
            text-transform: uppercase;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 9px;
        }

        .balance-value {
            font-size: 96px;
            font-weight: 700;
            color: {% if remaining < threshold %}#D89B9B{% else %}#9BC4BC{% endif %};
            letter-spacing: -3px;
            line-height: 1;
        }

        .balance-unit {
            font-size: 36px;
            font-weight: 500;
            color: {% if remaining < threshold %}#B08080{% else %}#7FA9A3{% endif %};
            margin-left: 6px;
        }

        .info-grid {
            display: grid;
            gap: 18px;
            margin-bottom: 24px;
        }

        .info-item {
            background: #F8FAFB;
            border-radius: 21px;
            padding: 27px;
            border-left: 4.5px solid #C9DAE8;
        }

        .info-label {
            font-size: 21px;
            font-weight: 500;
            color: #7A8A99;
            letter-spacing: 0.6px;
            text-transform: uppercase;
            margin-bottom: 9px;
            display: flex;
            align-items: center;
            gap: 7.5px;
        }

        .info-value {
            font-size: 27px;
            font-weight: 500;
            color: #2D4356;
            letter-spacing: -0.3px;
            line-height: 1.3;
        }

        .material-symbols-rounded {
            font-size: 27px;
            vertical-align: middle;
        }

        {% if remaining < threshold %}
        .alert {
            background: #F5DDE0;
            border-radius: 21px;
            padding: 27px 30px;
            margin-bottom: 24px;
            border-left: 4.5px solid #D89B9B;
        }

        .alert-title {
            font-size: 25.5px;
            font-weight: 600;
            color: #7A5555;
            margin-bottom: 12px;
            letter-spacing: -0.3px;
            display: flex;
            align-items: center;
            gap: 9px;
        }

        .alert-text {
            font-size: 22.5px;
            font-weight: 400;
            color: #95686B;
            line-height: 1.5;
            letter-spacing: 0.15px;
        }
        {% endif %}

        .footer {
            background: #F8FAFB;
            padding: 21px 36px;
            text-align: center;
            border-top: 1px solid #E8EBED;
        }

        .footer-text {
            font-size: 19.5px;
            font-weight: 400;
            color: #9AA5B1;
            letter-spacing: 0.45px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title">电费详情</div>
            {% if prefix %}
            <div class="subtitle">{{ prefix }}</div>
            {% endif %}
        </div>

        <div class="content">
            <div class="balance-card">
                <div class="balance-label">
                    <span class="material-symbols-rounded">account_balance_wallet</span>
                    当前余额
                </div>
                <div class="balance-value">{{ remaining }}<span class="balance-unit">元</span></div>
            </div>

            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">
                        <span class="material-symbols-rounded">location_on</span>
                        位置信息
                    </div>
                    <div class="info-value">{{ campus }} {{ building_name }} {{ pid }}室</div>
                </div>

                <div class="info-item">
                    <div class="info-label">
                        <span class="material-symbols-rounded">bar_chart</span>
                        累计消耗
                    </div>
                    <div class="info-value">{{ total_used }} 元</div>
                </div>

                <div class="info-item">
                    <div class="info-label">
                        <span class="material-symbols-rounded">schedule</span>
                        结算时间
                    </div>
                    <div class="info-value">{{ update_time }}</div>
                </div>
            </div>

            {% if remaining < threshold %}
            <div class="alert">
                <div class="alert-title">
                    <span class="material-symbols-rounded">warning</span>
                    余额不足提醒
                </div>
                <div class="alert-text">当前余额低于 {{ threshold }} 元，建议尽快充值</div>
            </div>
            {% endif %}
        </div>

        <div class="footer">
            <div class="footer-text">ASTRBOT-PLUGIN-CTBU-ELECT</div>
        </div>
    </div>
</body>
</html>
'''
class CTBUElectPlugin(Star):
    '''CTBU 电费小助手插件'''

    def __init__(self, context: Context, config: dict = None):
        super().__init__(context, config)
        # 从配置读取文转图渲染模式
        self.render_mode = config.get("render_mode", False) if config else False
        # 校区前缀映射
        self.CAMPUS_PREFIX = {
            "cy": ("茶园校区", "茶园{building}栋"),      # 茶园10-19栋
            "lhh": ("兰花湖校区", "兰花湖{building}舍"),  # 兰花湖1-16舍
            "bq": ("南岸校区", "北区{building}舍"),       # 北区1-24舍
            "nq": ("南岸校区", "南区{building}舍"),       # 南区1-3,5-12,13A,13B,13C,14,15,16A,16B舍
            "yjs": ("南岸校区", "研究生公寓"),            # 研究生公寓
        }
        # 电费查询 URL 基础地址
        self.base_url = "https://hqpay.ctbu.edu.cn/weixin/ashx/frmuser.ashx"
        # 自助查询缴费系统 URL
        self.pay_url = "https://hqpay.ctbu.edu.cn/weixin/index.html"
        # 存储订阅用户: {unified_msg_origin: {"room_id": str, "threshold": float, "push_enabled": bool, "push_time": int, "low_balance_push_enabled": bool}}
        self.subscribers: dict[str, dict] = {}
        # 定时任务
        self._task = None
        # 默认低电量提醒阈值（元）
        self.default_threshold = 10.0
        # 默认推送时间（小时，东八区）
        self.default_push_time = 10
        # 订阅轮询间隔（分钟），0 = 对齐整点（默认）
        self.poll_interval = 0

    async def initialize(self):
        """插件初始化，加载订阅数据并启动定时推送任务"""
        logger.info("CTBU 电费插件初始化中...")
        logger.info(f"渲染模式: {'文转图' if self.render_mode else '纯文本'}")
        # 从 KV 存储加载订阅数据
        self.subscribers = await self.get_kv_data("subscribers", {})
        logger.info(f"已加载 {len(self.subscribers)} 个订阅")
        # 从 KV 存储加载轮询间隔
        self.poll_interval = await self.get_kv_data("poll_interval", 0)
        interval_desc = f"{self.poll_interval} 分钟" if self.poll_interval > 0 else "每小时整点"
        logger.info(f"轮询间隔: {interval_desc} (时区: UTC+8)")
        # 启动定时推送任务
        self._task = asyncio.create_task(self._auto_push_task())
        logger.info("CTBU 电费插件初始化完成")

    async def terminate(self):
        """插件卸载时取消定时任务"""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("CTBU 电费插件已卸载")

    def _parse_room_id(self, room_id: str) -> tuple[str, str, str, str] | None:
        """
        解析房间号，返回 (校区, 楼栋名称, pid, 原始房间号)

        支持的格式：
        - cy10-101: 茶园校区 茶园10栋 101室 -> pid=10-101
        - lhh1-101: 兰花湖校区 兰花湖1舍 101室 -> pid=101
        - bq1-101: 南岸校区 北区1舍 A1001室 -> pid=A1001
        - nq1-101: 南岸校区 南区1舍 101室 -> pid=101
        - yjs-101: 南岸校区 研究生公寓 1101室 -> pid=1101
        """
        room_id = room_id.strip()

        # 匹配格式: 前缀 + 楼栋号 + - + 房间号（房间号允许字母、中文等，如 A1001、102值班室）
        match = re.match(r'^([a-zA-Z]+)(\d+[a-zA-Z]?)?-(\w+)$', room_id, re.IGNORECASE | re.UNICODE)
        if not match:
            return None

        prefix = match.group(1).lower()
        building_num = match.group(2) or ""
        room_num = match.group(3)

        if prefix not in self.CAMPUS_PREFIX:
            return None

        campus, building_template = self.CAMPUS_PREFIX[prefix]

        # 构建楼栋名称和 pid
        if prefix == "cy":
            # 茶园校区: pid 包含楼栋号
            building_name = building_template.format(building=building_num)
            pid = f"{building_num}-{room_num}"
        elif prefix == "yjs":
            # 研究生公寓: 没有楼栋号
            building_name = "研究生公寓"
            pid = room_num
        else:
            # 其他校区: pid 只有房间号
            building_name = building_template.format(building=building_num.upper())
            pid = room_num

        return (campus, building_name, pid, room_id)

    def _build_url(self, room_id: str) -> str | None:
        """根据房间号构建查询 URL"""
        parsed = self._parse_room_id(room_id)
        if not parsed:
            return None

        campus, building_name, pid, _ = parsed
        encoded_building = quote(building_name)
        return f"{self.base_url}?test=lastlist&pid={pid}&dyid={encoded_building}"

    async def _fetch_elect_data(self, room_id: str) -> dict | None:
        """
        访问电费查询接口获取数据
        :param room_id: 房间号，格式如 cy10-101
        :return: 解析后的字典
        """
        url = self._build_url(room_id)
        if not url:
            return None

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json(content_type=None)
                        if data and len(data) > 0 and len(data[0]) >= 4:
                            room_info = data[0]
                            return {
                                "room_id": room_id,
                                "pid": room_info[0],
                                "remaining": float(room_info[1]),
                                "update_time": room_info[2],
                                "total_used": room_info[3]
                            }
                        else:
                            logger.warning(f"电费数据格式异常: {data}")
                            return None
                    else:
                        logger.error(f"电费接口返回状态码: {response.status}")
                        return None
        except asyncio.TimeoutError:
            logger.error("电费接口请求超时")
            return None
        except Exception as e:
            logger.error(f"获取电费数据失败: {e}")
            return None

    def _format_elect_message(self, data: dict, threshold: float = None) -> str:
        """
        格式化电费信息
        :param data: 电费数据
        :param threshold: 低余额阈值，低于此值时显示自助缴费系统链接
        """
        if threshold is None:
            threshold = self.default_threshold

        room_id = data["room_id"]
        parsed = self._parse_room_id(room_id)
        if not parsed:
            return "数据解析失败"

        campus, building_name, pid, _ = parsed
        remaining = data["remaining"]

        # 基本信息
        message = (
            f"电费查询结果\n"
            f"━━━━━━━━━━━━━━\n"
            f"位置: {campus} {building_name} {pid}室\n"
            f"余额: {remaining} 元\n"
            f"累耗: {data['total_used']} 元\n"
            f"结算: {data['update_time']}"
        )

        # 低余额提醒和自助缴费系统链接
        if remaining < threshold:
            message += (
                f"\n\n[!] 余额不足 {threshold} 元，请尽快充值！\n"
                f"━━━━━━━━━━━━━━\n"
                f"自助缴费系统:\n{self.pay_url}"
            )

        return message

    def _extract_viewstate(self, html: str) -> str | None:
        """提取 ASP.NET 页面令牌 __VIEWSTATE"""
        pattern = r'name="__VIEWSTATE"[^>]*value="([^"]*)"'
        match = re.search(pattern, html, re.I)
        return match.group(1) if match else None

    def _validate_charge(self, balance: float, amount: float) -> tuple[bool, str]:
        """
        校验充值金额
        :return: (是否有效, 错误信息)
        """
        if amount <= 0:
            return False, "充值金额必须大于 0"
        if balance < 0 and amount < abs(balance):
            return False, f"充值金额不足: 当前欠费 {abs(balance):.2f} 元，需充值至少 {abs(balance):.2f} 元"
        return True, ""

    async def _get_payment_link(self, room_id: str, amount: float) -> dict:
        """
        获取电费充值支付链接
        :param room_id: 房间号（格式如 cy10-101）
        :param amount: 充值金额（元）
        :return: {"success": bool, "message": str, "pay_url": str|None, "balance": float|None}
        """
        parsed = self._parse_room_id(room_id)
        if not parsed:
            return {"success": False, "message": "房间号格式错误", "pay_url": None, "balance": None}

        campus, building_name, pid, _ = parsed
        base_url = "https://hqpay.ctbu.edu.cn"
        timeout = aiohttp.ClientTimeout(total=15)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        }

        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                # 设置用户信息 Cookie
                session.cookie_jar.update_cookies({
                    "schoolname": quote(campus, safe=''),
                    "dyname": quote(building_name, safe=''),
                    "mphname": quote(pid, safe=''),
                })

                # Step 1: 获取支付页面并提取 __VIEWSTATE
                page_url = f"{base_url}/weixin/WebPay.aspx"
                async with session.get(page_url, headers=headers) as resp:
                    if resp.status != 200:
                        return {"success": False, "message": f"获取支付页面失败 (状态码: {resp.status})", "pay_url": None, "balance": None}
                    html = await resp.text()

                viewstate = self._extract_viewstate(html)
                if not viewstate:
                    return {"success": False, "message": "页面令牌提取失败，请稍后重试", "pay_url": None, "balance": None}

                # Step 2: 查询余额
                balance_url = f"{base_url}/weixin/ashx/frmuser.ashx"
                balance_params = {"test": "lastlist", "pid": pid, "dyid": building_name}
                balance_headers = {**headers, "X-Requested-With": "XMLHttpRequest"}

                async with session.get(balance_url, params=balance_params, headers=balance_headers) as resp:
                    if resp.status != 200:
                        return {"success": False, "message": "余额查询失败", "pay_url": None, "balance": None}
                    data = await resp.json(content_type=None)
                    if not data or not isinstance(data, list) or len(data[0]) < 2:
                        return {"success": False, "message": "余额数据解析失败", "pay_url": None, "balance": None}
                    balance = float(data[0][1])

                # Step 3: 校验充值金额
                valid, err_msg = self._validate_charge(balance, amount)
                if not valid:
                    return {"success": False, "message": err_msg, "pay_url": None, "balance": balance}

                # Step 4: 提交充值表单
                form_data = {
                    "__VIEWSTATE": viewstate,
                    "schoolname": campus,
                    "dyname": building_name,
                    "mphname": pid,
                    "moninfo": str(balance),
                    "hidBill": "",
                    "jrtxt": str(int(amount)),
                    "Button1": "提交",
                }
                submit_headers = {**headers, "Referer": base_url}

                async with session.post(page_url, headers=submit_headers, data=form_data, allow_redirects=False) as resp:
                    if resp.status == 302 and resp.headers.get("Location"):
                        pay_link = resp.headers["Location"]
                        if pay_link.startswith("/"):
                            pay_link = f"{base_url}{pay_link}"
                        # 安全检测：验证支付链接域名
                        parsed_url = urlparse(pay_link)
                        if parsed_url.netloc != "cwxsjf.ctbu.edu.cn":
                            logger.warning(f"支付链接域名异常: {parsed_url.netloc}")
                            return {"success": False, "message": "安全警告：支付链接域名异常，请注意自查来源是否被篡改", "pay_url": None, "balance": balance}
                        return {"success": True, "message": "充值请求成功", "pay_url": pay_link, "balance": balance}
                    else:
                        return {"success": False, "message": "充值请求未返回支付链接，请检查房间信息", "pay_url": None, "balance": balance}

        except asyncio.TimeoutError:
            return {"success": False, "message": "请求超时，请稍后重试", "pay_url": None, "balance": None}
        except Exception as e:
            logger.error(f"获取支付链接失败: {e}")
            return {"success": False, "message": f"请求异常: {str(e)}", "pay_url": None, "balance": None}

    async def _render_elect_image(self, data: dict, threshold: float = None, prefix: str = "") -> str:
        """
        使用文转图方式渲染电费信息
        :param data: 电费数据
        :param threshold: 低余额阈值
        :param prefix: 可选的前缀文本（如 "[每日电费推送]"）
        :return: 图片 URL
        """
        if threshold is None:
            threshold = self.default_threshold

        room_id = data["room_id"]
        parsed = self._parse_room_id(room_id)
        if not parsed:
            return None

        campus, building_name, pid, _ = parsed

        # 准备渲染数据
        render_data = {
            "campus": campus,
            "building_name": building_name,
            "pid": pid,
            "remaining": data["remaining"],
            "total_used": data["total_used"],
            "update_time": data["update_time"],
            "threshold": threshold,
            "prefix": prefix
        }

        # 渲染配置
        options = {
            "type": "jpeg",
            "quality": 95,
            "full_page": True,
            "scale": "device",
            "timeout": 10000,
             "clip": {
                "x": 0,
                "y": 0,
                "width": 680,
                "height":2000
            }
            
        }
        

        # 使用 html_render 生成图片
        try:
            url = await self.html_render(ELECT_HTML_TEMPLATE, render_data, return_url=True, options=options)
            logger.info(f"文转图渲染成功: {url}")
            return url
        except Exception as e:
            logger.error(f"文转图渲染失败: {e}")
            return None

    def _get_help_message(self) -> str:
        """获取帮助信息"""
        return (
            "CTBU 电费查询插件帮助\n"
            "━━━━━━━━━━━━━━\n\n"
            "房间号格式\n"
            "格式: 校区前缀 + 楼栋号 + - + 房间号\n"
            "例如: cy10-101、lhh1-203、bq5-305\n\n"
            "校区前缀:\n"
            "  cy  - 茶园校区 (10-19栋)\n"
            "  lhh - 兰花湖校区 (1-16舍)\n"
            "  bq  - 南岸北区 (1-24舍)\n"
            "  nq  - 南岸南区 (1-16舍)\n"
            "  yjs - 研究生公寓\n\n"
            "常用命令\n"
            "━━━━━━━━━━━━━━\n"
            "查询电费:\n"
            "  /电费 cy10-101    查询指定房间\n"
            "  /电费            查询已绑定房间\n\n"
            "绑定房间:\n"
            "  /订阅电费 cy10-101      绑定并设置默认阈值\n"
            "  /订阅电费 cy10-101 15   绑定并设置自定义阈值\n"
            "  /取消订阅电费           取消绑定\n\n"
            "定时推送:\n"
            "  /开启推送             开启定时推送\n"
            "  /关闭推送             关闭定时推送\n"
            "  /设置推送时间 10       设置推送时间(默认10点)\n\n"
            "低余额推送:\n"
            "  /开启低余额推送        余额不足自动提醒\n"
            "  /关闭低余额推送        关闭低余额提醒\n\n"
            "其他设置:\n"
            "  /设置阈值 15           设置低余额阈值\n"
            "  /设置轮询间隔 0        设置轮询间隔(0=整点)\n"
            "  /我的订阅              查看当前配置\n"
            "  /缴费                 跳转自助查询缴费系统\n"
            "  /快捷充值 50           一键充值(实验性,上限100)\n"
            "  /确认充值免责          首次充值需确认免责\n\n"
            "使用建议\n"
            "━━━━━━━━━━━━━━\n"
            "1. 首次使用: /订阅电费 <房间号>\n"
            "2. 开启定时推送: /开启推送\n"
            "3. 开启低余额推送: /开启低余额推送\n"
            "4. 设置推送时间: /设置推送时间 <小时>\n"
            "5. 快捷充值(实验性): /快捷充值 <金额>\n"
            "   (首次需 /确认充值免责，上限100元)\n"
            "6. 两种推送可独立开关，互不影响\n"
            "7. 所有时间均为东八区 (UTC+8)"
        )

    async def _get_user_threshold(self, umo: str) -> float:
        """获取用户设置的阈值"""
        if umo in self.subscribers:
            return self.subscribers[umo].get("threshold", self.default_threshold)
        return self.default_threshold

    @filter.command("电费", alias={"df", "查电费", "elect"})
    async def query_elect(self, event: AstrMessageEvent, room_id: str = ""):
        """查询电费余额"""
        umo = event.unified_msg_origin

        # 如果未指定房间号，尝试使用绑定的房间
        if not room_id:
            if umo in self.subscribers:
                room_id = self.subscribers[umo]["room_id"]
            else:
                # 未绑定房间，提示用户
                yield event.plain_result(
                    "[提示] 您还未绑定房间\n\n"
                    "请使用以下方式查询:\n"
                    "1. 直接查询: /电费 <房间号>\n"
                    "   示例: /电费 cy10-101\n\n"
                    "2. 订阅后查询: /订阅电费 <房间号>\n"
                    "   订阅后可直接使用 /电费 查询\n\n"
                    "输入 /电费帮助 查看更多信息"
                )
                return

        # 验证房间号格式
        if not self._parse_room_id(room_id):
            yield event.plain_result(
                "[错误] 房间号格式错误\n\n" + self._get_help_message()
            )
            return

        yield event.plain_result(f"正在查询 {room_id} ...")

        data = await self._fetch_elect_data(room_id)
        if data:
            threshold = await self._get_user_threshold(umo)

            # 根据 render_mode 决定输出方式
            if self.render_mode:
                # 文转图模式
                image_url = await self._render_elect_image(data, threshold)
                if image_url:
                    yield event.image_result(image_url)
                    # 低余额时额外发送自助缴费系统链接
                    if data["remaining"] < threshold:
                        yield event.plain_result(
                            f"━━━━━━━━━━━━━━\n"
                            f"自助缴费系统:\n{self.pay_url}"
                        )
                else:
                    # 渲染失败，降级为纯文本
                    message = self._format_elect_message(data, threshold)
                    yield event.plain_result(message)
            else:
                # 纯文本模式
                message = self._format_elect_message(data, threshold)
                yield event.plain_result(message)
        else:
            yield event.plain_result(
                f"[错误] 查询失败\n"
                f"房间: {room_id}\n"
                f"原因: 房间号不存在或网络异常"
            )

    @filter.command("电费帮助", alias={"dfhelp", "elect_help"})
    async def elect_help(self, event: AstrMessageEvent):
        """显示电费查询帮助"""
        yield event.plain_result(self._get_help_message())

    @filter.command("订阅电费", alias={"订阅", "subscribe_elect"})
    async def subscribe_elect(self, event: AstrMessageEvent, room_id: str = "", threshold: str = ""):
        """
        订阅电费自动推送
        :param room_id: 房间号
        :param threshold: 低余额阈值（可选）
        """
        if not room_id:
            umo = event.unified_msg_origin
            if umo in self.subscribers:
                # 已订阅用户可以不传房间号（保持原有绑定）
                room_id = self.subscribers[umo]["room_id"]
            else:
                # 新用户必须提供房间号
                yield event.plain_result(
                    "[错误] 首次订阅需要指定房间号\n\n"
                    "使用方法:\n"
                    "/订阅电费 <房间号> [阈值]\n\n"
                    "示例:\n"
                    "/订阅电费 cy10-101\n"
                    "/订阅电费 cy10-101 15\n\n"
                    "输入 /电费帮助 查看房间号格式"
                )
                return

        if not self._parse_room_id(room_id):
            yield event.plain_result(
                "[错误] 房间号格式错误\n\n" + self._get_help_message()
            )
            return

        # 解析阈值
        threshold_value = self.default_threshold
        if threshold:
            try:
                threshold_value = float(threshold)
                if threshold_value <= 0:
                    yield event.plain_result("[错误] 阈值必须大于 0")
                    return
            except ValueError:
                yield event.plain_result("[错误] 阈值必须是有效的数字")
                return

        umo = event.unified_msg_origin
        existing = self.subscribers.get(umo)
        if existing:
            # 已订阅用户：更新房间号和阈值
            old_room_id = existing.get("room_id")
            existing["room_id"] = room_id
            existing["threshold"] = threshold_value
            # 更换房间时，重置免责确认状态，需要重新阅读并确认
            if old_room_id != room_id:
                existing["recharge_disclaimer_confirmed"] = False
                existing["recharge_disclaimer_shown"] = False
        else:
            self.subscribers[umo] = {
                "room_id": room_id,
                "threshold": threshold_value,
                "push_enabled": False,
                "push_time": self.default_push_time,
                "low_balance_push_enabled": False
            }

        # 保存到 KV 存储
        await self.put_kv_data("subscribers", self.subscribers)

        user_data = self.subscribers[umo]
        push_enabled = user_data.get("push_enabled", False)
        push_time = user_data.get("push_time", self.default_push_time)
        push_status = f"已开启 (每天 {push_time}:00)" if push_enabled else "已关闭"
        low_balance_status = "已开启" if user_data.get("low_balance_push_enabled", False) else "已关闭"

        yield event.plain_result(
            f"绑定成功\n"
            f"━━━━━━━━━━━━━━\n"
            f"房间: {room_id}\n"
            f"阈值: {threshold_value} 元\n"
            f"定时推送: {push_status}\n"
            f"低余额推送: {low_balance_status}\n\n"
            f"提示:\n"
            f"{'关闭定时推送: /关闭推送' if push_enabled else '开启定时推送: /开启推送'}\n"
            f"{'关闭低余额推送: /关闭低余额推送' if user_data.get('low_balance_push_enabled', False) else '开启低余额推送: /开启低余额推送'}\n"
            f"设置推送时间: /设置推送时间 <小时>\n"
            f"修改阈值: /设置阈值 <金额>\n"
            f"取消绑定: /取消订阅电费"
        )

    @filter.command("取消订阅电费", alias={"取消订阅", "unsubscribe_elect"})
    async def unsubscribe_elect(self, event: AstrMessageEvent):
        """取消订阅电费推送"""
        umo = event.unified_msg_origin
        if umo in self.subscribers:
            user_data = self.subscribers.pop(umo)
            await self.put_kv_data("subscribers", self.subscribers)
            yield event.plain_result(f"已取消 {user_data['room_id']} 的订阅")
        else:
            yield event.plain_result("[错误] 您还没有订阅电费推送")

    @filter.command("设置阈值", alias={"阈值", "set_threshold"})
    async def set_threshold(self, event: AstrMessageEvent, threshold: str = ""):
        """
        设置低余额提醒阈值
        :param threshold: 阈值金额（元）
        """
        umo = event.unified_msg_origin

        if not threshold:
            # 显示当前阈值
            current = await self._get_user_threshold(umo)
            yield event.plain_result(
                f"当前低余额阈值: {current} 元\n\n"
                f"使用方法: /设置阈值 <金额>\n"
                f"示例: /设置阈值 15"
            )
            return

        try:
            threshold_value = float(threshold)
            if threshold_value <= 0:
                yield event.plain_result("[错误] 阈值必须大于 0")
                return
        except ValueError:
            yield event.plain_result("[错误] 请输入有效的数字")
            return

        # 如果用户已订阅，更新阈值；否则需要先订阅
        if umo in self.subscribers:
            self.subscribers[umo]["threshold"] = threshold_value
            await self.put_kv_data("subscribers", self.subscribers)
            yield event.plain_result(
                f"阈值已更新\n"
                f"━━━━━━━━━━━━━━\n"
                f"房间: {self.subscribers[umo]['room_id']}\n"
                f"新阈值: {threshold_value} 元\n"
                f"余额低于此值时将自动显示自助缴费系统链接"
            )
        else:
            yield event.plain_result(
                f"[提示] 您还未订阅电费推送\n\n"
                f"请先使用以下命令订阅:\n"
                f"/订阅电费 <房间号> {threshold_value}\n\n"
                f"示例: /订阅电费 cy10-101 {threshold_value}"
            )

    @filter.command("开启推送", alias={"启用推送", "enable_push"})
    async def enable_push(self, event: AstrMessageEvent):
        """开启电费自动推送"""
        umo = event.unified_msg_origin
        if umo not in self.subscribers:
            yield event.plain_result(
                "[提示] 您还未绑定房间\n\n"
                "请先使用 /订阅电费 <房间号> 绑定房间"
            )
            return

        if self.subscribers[umo].get("push_enabled", False):
            push_time = self.subscribers[umo].get("push_time", self.default_push_time)
            yield event.plain_result(
                f"[提示] 推送已经是开启状态\n\n"
                f"当前推送时间: 每天 {push_time}:00\n"
                f"修改时间: /设置推送时间 <小时>"
            )
            return

        self.subscribers[umo]["push_enabled"] = True
        await self.put_kv_data("subscribers", self.subscribers)

        push_time = self.subscribers[umo].get("push_time", self.default_push_time)
        yield event.plain_result(
            f"推送已开启\n"
            f"━━━━━━━━━━━━━━\n"
            f"房间: {self.subscribers[umo]['room_id']}\n"
            f"推送时间: 每天 {push_time}:00\n\n"
            f"修改推送时间: /设置推送时间 <小时>\n"
            f"关闭推送: /关闭推送"
        )

    @filter.command("关闭推送", alias={"禁用推送", "disable_push"})
    async def disable_push(self, event: AstrMessageEvent):
        """关闭电费自动推送"""
        umo = event.unified_msg_origin
        if umo not in self.subscribers:
            yield event.plain_result(
                "[提示] 您还未绑定房间\n\n"
                "请先使用 /订阅电费 <房间号> 绑定房间"
            )
            return

        if not self.subscribers[umo].get("push_enabled", False):
            yield event.plain_result("[提示] 推送已经是关闭状态")
            return

        self.subscribers[umo]["push_enabled"] = False
        await self.put_kv_data("subscribers", self.subscribers)

        yield event.plain_result(
            f"推送已关闭\n"
            f"━━━━━━━━━━━━━━\n"
            f"房间绑定仍然保留，您仍可使用 /电费 查询\n\n"
            f"重新开启: /开启推送"
        )

    @filter.command("开启低余额推送", alias={"启用低余额推送", "enable_low_balance_push"})
    async def enable_low_balance_push(self, event: AstrMessageEvent):
        """开启低余额自动推送"""
        umo = event.unified_msg_origin
        if umo not in self.subscribers:
            yield event.plain_result(
                "[提示] 您还未绑定房间\n\n"
                "请先使用 /订阅电费 <房间号> 绑定房间"
            )
            return

        if self.subscribers[umo].get("low_balance_push_enabled", False):
            threshold = self.subscribers[umo].get("threshold", self.default_threshold)
            yield event.plain_result(
                f"[提示] 低余额推送已经是开启状态\n\n"
                f"当前阈值: {threshold} 元\n"
                f"余额低于阈值时会自动推送提醒\n"
                f"修改阈值: /设置阈值 <金额>"
            )
            return

        self.subscribers[umo]["low_balance_push_enabled"] = True
        await self.put_kv_data("subscribers", self.subscribers)

        threshold = self.subscribers[umo].get("threshold", self.default_threshold)
        yield event.plain_result(
            f"低余额推送已开启\n"
            f"━━━━━━━━━━━━━━\n"
            f"房间: {self.subscribers[umo]['room_id']}\n"
            f"阈值: {threshold} 元\n"
            f"提醒: 余额低于阈值时自动推送\n\n"
            f"说明: 每小时检查一次，低于阈值立即提醒\n"
            f"修改阈值: /设置阈值 <金额>\n"
            f"关闭推送: /关闭低余额推送"
        )

    @filter.command("关闭低余额推送", alias={"禁用低余额推送", "disable_low_balance_push"})
    async def disable_low_balance_push(self, event: AstrMessageEvent):
        """关闭低余额自动推送"""
        umo = event.unified_msg_origin
        if umo not in self.subscribers:
            yield event.plain_result(
                "[提示] 您还未绑定房间\n\n"
                "请先使用 /订阅电费 <房间号> 绑定房间"
            )
            return

        if not self.subscribers[umo].get("low_balance_push_enabled", False):
            yield event.plain_result("[提示] 低余额推送已经是关闭状态")
            return

        self.subscribers[umo]["low_balance_push_enabled"] = False
        await self.put_kv_data("subscribers", self.subscribers)

        yield event.plain_result(
            f"低余额推送已关闭\n"
            f"━━━━━━━━━━━━━━\n"
            f"不再自动推送低余额提醒\n"
            f"仍可通过 /电费 命令手动查询\n\n"
            f"重新开启: /开启低余额推送"
        )

    @filter.command("设置推送时间", alias={"推送时间", "set_push_time"})
    async def set_push_time(self, event: AstrMessageEvent, hour: str = ""):
        """
        设置每日推送时间
        :param hour: 小时 (0-23)
        """
        umo = event.unified_msg_origin

        if umo not in self.subscribers:
            yield event.plain_result(
                "[提示] 您还未绑定房间\n\n"
                "请先使用 /订阅电费 <房间号> 绑定房间"
            )
            return

        if not hour:
            # 显示当前推送时间
            current_time = self.subscribers[umo].get("push_time", self.default_push_time)
            push_enabled = self.subscribers[umo].get("push_enabled", False)
            status = "已开启" if push_enabled else "已关闭"
            yield event.plain_result(
                f"推送设置\n"
                f"━━━━━━━━━━━━━━\n"
                f"推送时间: 每天 {current_time}:00\n"
                f"推送状态: {status}\n\n"
                f"修改时间: /设置推送时间 <小时>\n"
                f"示例: /设置推送时间 8"
            )
            return

        try:
            hour_value = int(hour)
            if hour_value < 0 or hour_value > 23:
                yield event.plain_result("[错误] 小时必须在 0-23 之间")
                return
        except ValueError:
            yield event.plain_result("[错误] 请输入有效的小时数 (0-23)")
            return

        self.subscribers[umo]["push_time"] = hour_value
        await self.put_kv_data("subscribers", self.subscribers)

        push_enabled = self.subscribers[umo].get("push_enabled", False)
        status_text = f"推送状态: 已开启\n推送将在每天 {hour_value}:00 进行" if push_enabled else f"推送状态: 已关闭\n开启后将在每天 {hour_value}:00 推送"

        yield event.plain_result(
            f"推送时间已更新\n"
            f"━━━━━━━━━━━━━━\n"
            f"新时间: 每天 {hour_value}:00\n"
            f"{status_text}\n\n"
            f"{'关闭推送: /关闭推送' if push_enabled else '开启推送: /开启推送'}"
        )

    @filter.command("设置轮询间隔", alias={"轮询间隔", "set_poll_interval"})
    async def set_poll_interval(self, event: AstrMessageEvent, minutes: str = ""):
        """
        设置后台订阅轮询间隔（管理员功能）
        :param minutes: 轮询间隔分钟数，0 = 每小时整点
        """
        if not minutes:
            interval_desc = f"{self.poll_interval} 分钟" if self.poll_interval > 0 else "每小时整点（默认）"
            yield event.plain_result(
                f"轮询间隔设置\n"
                f"━━━━━━━━━━━━━━\n"
                f"当前间隔: {interval_desc}\n"
                f"时区: UTC+8 (东八区)\n\n"
                f"修改方法: /设置轮询间隔 <分钟数>\n"
                f"示例:\n"
                f"  /设置轮询间隔 0    每小时整点检查（默认）\n"
                f"  /设置轮询间隔 30   每30分钟检查一次\n"
                f"  /设置轮询间隔 60   每60分钟检查一次"
            )
            return

        try:
            minutes_value = int(minutes)
            if minutes_value < 0:
                yield event.plain_result("[错误] 间隔分钟数不能为负数")
                return
            if minutes_value > 0 and minutes_value < 5:
                yield event.plain_result("[错误] 最小轮询间隔为 5 分钟")
                return
        except ValueError:
            yield event.plain_result("[错误] 请输入有效的整数（分钟数）")
            return

        self.poll_interval = minutes_value
        await self.put_kv_data("poll_interval", self.poll_interval)

        interval_desc = f"{minutes_value} 分钟" if minutes_value > 0 else "每小时整点"
        yield event.plain_result(
            f"轮询间隔已更新\n"
            f"━━━━━━━━━━━━━━\n"
            f"新间隔: {interval_desc}\n"
            f"时区: UTC+8 (东八区)\n\n"
            f"说明: 重启任务后生效，当前任务将在下次唤醒时采用新间隔"
        )

    @filter.command("缴费", alias={"pay_elect"})
    async def pay_elect(self, event: AstrMessageEvent):
        """跳转自助查询缴费系统"""
        yield event.plain_result(
            "自助查询缴费系统\n"
            "━━━━━━━━━━━━━━\n"
            "请点击以下链接跳转缴费系统:\n"
            f"{self.pay_url}\n\n"
        )

    @filter.command("快捷充值", alias={"一键充值", "充电费", "快速充值", "recharge"})
    async def quick_recharge(self, event: AstrMessageEvent, amount: str = ""):
        """
        快捷充值电费（一键获取支付链接）
        :param amount: 充值金额（元）
        """
        umo = event.unified_msg_origin

        # 检查是否已绑定房间
        if umo not in self.subscribers:
            yield event.plain_result(
                "[提示] 您还未绑定房间\n\n"
                "请先使用 /订阅电费 <房间号> 绑定房间\n"
                "示例: /订阅电费 cy10-101\n\n"
                "绑定后即可使用快捷充值功能"
            )
            return

        room_id = self.subscribers[umo]["room_id"]

        # 校验金额
        if not amount:
            yield event.plain_result(
                "快捷充值说明（实验性功能）\n"
                "━━━━━━━━━━━━━━\n"
                "使用方法: /快捷充值 <金额>\n"
                "示例: /快捷充值 100\n\n"
                f"当前绑定房间: {room_id}\n\n"
                "说明:\n"
                "1. 金额必须为正整数（1-100元）\n"
                "2. 如有欠费，充值金额需大于欠费额\n"
                "3. 获取链接后可进行支付\n"
                "4. 注意: 建议先以最低金额进行试探性充值\n"
                "   请务必确认房间和金额，避免错误。\n\n"
                "   [提示] 确认免责声明后，请使用 /确认免责声明 命令\n"
                "   [提示] 确认免责声明后，请使用 /快捷充值 <金额> 命令\n"
                "   [提示] 确认免责声明后，请使用 /查询电费 命令查询余额\n"
                "5. 充值成功后请务必使用 /查询电费 命令查询余额"
            )
            return

        # 检查是否已确认免责声明（首次使用需确认）
        if not self.subscribers[umo].get("recharge_disclaimer_confirmed", False):
            # 标记已显示免责声明（防止用户直接调用确认命令跳过阅读）
            self.subscribers[umo]["recharge_disclaimer_shown"] = True
            await self.put_kv_data("subscribers", self.subscribers)

            yield event.plain_result(
                "快捷充值服务免责声明（实验性功能）\n"
                "====================\n"
                "本工具仅作为重庆工商大学官方支付链接的技术中转服务，\n"
                "使用前请务必仔细阅读并同意以下条款：\n\n"
                "1. 本功能仅提供链接获取便利，\n"
                "   不担保链接的长期有效性与技术稳定性。\n"
                "2. 支付前请务必仔细核对\n"
                "   收款方信息、房间号及充值金额。\n"
                "3. 因用户个人操作失误导致的\n"
                "   资金损失，均由用户自行承担，\n"
                "   开发者对此不承担任何法律责任。\n"
                "4. 实际支付行为由学校官方收款平台\n"
                "   独立完成，本工具不接触任何资金。\n"
                "   请确保使用正规来源插件，警惕第三方\n"
                "   篡改链接风险，注意资金安全。\n"
                "5. 使用建议：首次使用或链接更新后，\n"
                "   建议先以最低金额进行试探性充值，\n"
                "   确认充值流程与余额查询正常后再进行大额操作。\n\n"
                "====================\n"
                f"当前绑定房间：{room_id}\n\n"
                "如已阅读并同意以上内容，请发送：\n"
                "/确认充值免责\n\n"
                "确认后即可正常使用快捷充值功能"
            )
            return

        try:
            amount_value = float(amount)
            if amount_value != int(amount_value) or amount_value <= 0:
                yield event.plain_result("[错误] 金额必须为正整数")
                return
            amount_value = int(amount_value)
            if amount_value > 100:
                yield event.plain_result("[错误] 单次充值金额不能超过 100 元（实验性功能限制）")
                return
        except ValueError:
            yield event.plain_result("[错误] 请输入有效的金额数字")
            return

        yield event.plain_result(f"正在获取 {room_id} 的支付链接，充值金额: {amount_value} 元...")

        result = await self._get_payment_link(room_id, amount_value)

        if result["success"]:
            balance = result["balance"]
            status = f"欠费 {abs(balance):.2f} 元" if balance < 0 else f"余额 {balance:.2f} 元"
            yield event.plain_result(
                "充值请求已提交（实验性功能）\n"
                "━━━━━━━━━━━━━━\n"
                f"房间: {room_id}\n"
                f"当前状态: {status}\n"
                f"充值金额: {amount_value} 元\n"
                "━━━━━━━━━━━━━━\n"
                "⚠️⚠️⚠️重要提示⚠️⚠️⚠️\n "
                "   支付前请务必仔细核对：\n"
                "   「收款方信息」「房间号」及「充值金额」。\n"
                "   因用户个人操作失误导致的\n"
                "   资金损失，均由用户自行承担，\n"
                "   开发者对此不承担任何法律责任。\n"
                f"支付链接:\n{result['pay_url']}\n\n"
                "请在5分钟内访问链接完成支付\n\n"
            )
        else:
            error_msg = f"[错误] {result['message']}"
            if result["balance"] is not None:
                balance = result["balance"]
                status = f"欠费 {abs(balance):.2f} 元" if balance < 0 else f"余额 {balance:.2f} 元"
                error_msg += f"\n当前状态: {status}"
            yield event.plain_result(error_msg)

    @filter.command("确认充值免责", alias={"同意充值免责", "confirm_recharge_disclaimer"})
    async def confirm_recharge_disclaimer(self, event: AstrMessageEvent):
        """确认快捷充值免责声明"""
        umo = event.unified_msg_origin

        if umo not in self.subscribers:
            yield event.plain_result(
                "[提示] 您还未绑定房间\n\n"
                "请先使用 /订阅电费 <房间号> 绑定房间"
            )
            return

        if self.subscribers[umo].get("recharge_disclaimer_confirmed", False):
            yield event.plain_result(
                "[提示] 您已确认过免责声明（实验性功能）\n\n"
                "可直接使用 /快捷充值 <金额> 进行充值\n"
                "单次充值上限: 100 元"
            )
            return

        # 检查是否已经阅读过免责声明（防止跳过阅读直接确认）
        if not self.subscribers[umo].get("recharge_disclaimer_shown", False):
            yield event.plain_result(
                "[提示] 请先阅读免责声明\n\n"
                "请使用 /快捷充值 <金额> 查看免责声明内容\n"
                "阅读后方可确认"
            )
            return

        self.subscribers[umo]["recharge_disclaimer_confirmed"] = True
        await self.put_kv_data("subscribers", self.subscribers)

        room_id = self.subscribers[umo]["room_id"]
        yield event.plain_result(
            "免责声明已确认（实验性功能）\n"
            "━━━━━━━━━━━━━━\n"
            f"绑定房间: {room_id}\n\n"
            "现在可以使用快捷充值功能:\n"
            "/快捷充值 <金额>\n"
            "示例: /快捷充值 100\n"
            "单次充值上限: 100 元\n\n"
            "⚠️ 每次付款前请务必核对收款方信息、房间号和金额"
        )

    @filter.command("我的订阅", alias={"查看订阅", "subscription"})
    async def view_subscription(self, event: AstrMessageEvent):
        """查看当前订阅信息"""
        umo = event.unified_msg_origin
        if umo in self.subscribers:
            user_data = self.subscribers[umo]
            push_enabled = user_data.get("push_enabled", False)
            push_time = user_data.get("push_time", self.default_push_time)
            push_status = f"已开启 (每天 {push_time}:00)" if push_enabled else "已关闭"

            low_balance_push_enabled = user_data.get("low_balance_push_enabled", False)
            low_balance_status = "已开启" if low_balance_push_enabled else "已关闭"

            yield event.plain_result(
                f"订阅信息\n"
                f"━━━━━━━━━━━━━━\n"
                f"房间: {user_data['room_id']}\n"
                f"阈值: {user_data['threshold']} 元\n"
                f"定时推送: {push_status}\n"
                f"低余额推送: {low_balance_status}\n"
                f"绑定状态: 已绑定\n\n"
                f"快速操作:\n"
                f"{'关闭定时推送: /关闭推送\n' if push_enabled else '开启定时推送: /开启推送\n'}"
                f"{'关闭低余额推送: /关闭低余额推送' if low_balance_push_enabled else '开启低余额推送: /开启低余额推送'}"
            )
        else:
            yield event.plain_result(
                "[提示] 您还未绑定房间\n\n"
                "使用 /订阅电费 <房间号> 绑定房间"
            )

    async def _auto_push_task(self):
        """定时推送任务（时区: UTC+8）"""
        from astrbot.api.event import MessageChain

        # 记录已推送定时消息的用户（避免一天内重复推送）：{umo: date}
        pushed_users: dict[str, object] = {}
        # 记录已推送低余额提醒的用户（避免一天内重复推送）：{umo: date}
        low_balance_pushed_users: dict[str, object] = {}

        while True:
            try:
                now = datetime.now(tz=CST)

                # ── 计算下次唤醒时间 ──────────────────────────────────────
                if self.poll_interval > 0:
                    # 自定义间隔：直接等待指定分钟数
                    wait_seconds = self.poll_interval * 60
                    next_desc = f"{self.poll_interval} 分钟后"
                else:
                    # 默认：对齐到下一个整点
                    if now.minute == 0 and now.second < 30:
                        # 当前已在整点30秒内，直接执行（wait=0）
                        wait_seconds = 0
                    else:
                        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                        wait_seconds = (next_hour - now).total_seconds()
                    next_desc = f"下一整点 {(now + timedelta(seconds=wait_seconds)).strftime('%H:%M')} (CST)"

                if wait_seconds > 0:
                    logger.info(f"电费推送任务将在 {next_desc} 后执行")
                    await asyncio.sleep(wait_seconds)

                # ── 执行本轮检查 ─────────────────────────────────────────
                now = datetime.now(tz=CST)
                current_hour = now.hour
                current_date = now.date()

                # 清理过期推送记录（非今日）
                pushed_users = {k: v for k, v in pushed_users.items() if v == current_date}
                low_balance_pushed_users = {k: v for k, v in low_balance_pushed_users.items() if v == current_date}

                scheduled_push_count = 0
                low_balance_push_count = 0

                if self.subscribers:
                    for umo, user_data in list(self.subscribers.items()):
                        try:
                            room_id = user_data["room_id"]
                            threshold = user_data.get("threshold", self.default_threshold)
                            need_fetch = (
                                user_data.get("push_enabled", False) or
                                user_data.get("low_balance_push_enabled", False)
                            )
                            data = await self._fetch_elect_data(room_id) if need_fetch else None

                            # 1. 定时推送
                            if user_data.get("push_enabled", False):
                                push_time = user_data.get("push_time", self.default_push_time)
                                if push_time == current_hour:
                                    if umo not in pushed_users or pushed_users[umo] != current_date:
                                        if data:
                                            # 根据 render_mode 选择推送方式
                                            if self.render_mode:
                                                # 文转图模式
                                                image_url = await self._render_elect_image(data, threshold, "[每日电费推送]")
                                                if image_url:
                                                    chain = MessageChain().url_image(image_url)
                                                    # 低余额时额外发送缴费链接
                                                    if data.get("remaining", 0) < threshold:
                                                        chain.message(f"\n━━━━━━━━━━━━━━\n自助缴费系统:\n{self.pay_url}")
                                                    await self.context.send_message(umo, chain)
                                                else:
                                                    # 渲染失败，降级为纯文本
                                                    msg = "[每日电费推送]\n" + self._format_elect_message(data, threshold)
                                                    await self.context.send_message(umo, MessageChain().message(msg))
                                            else:
                                                # 纯文本模式
                                                msg = "[每日电费推送]\n" + self._format_elect_message(data, threshold)
                                                await self.context.send_message(umo, MessageChain().message(msg))

                                            pushed_users[umo] = current_date
                                            scheduled_push_count += 1
                                            logger.info(f"定时推送: {umo} -> {room_id} ({push_time}:00 CST)")
                                        else:
                                            logger.warning(f"定时推送获取数据失败: {room_id}")

                            # 2. 低余额推送
                            if user_data.get("low_balance_push_enabled", False):
                                if data:
                                    remaining = data.get("remaining", 0)
                                    if remaining < threshold:
                                        if umo not in low_balance_pushed_users or low_balance_pushed_users[umo] != current_date:
                                            # 根据 render_mode 选择推送方式
                                            if self.render_mode:
                                                # 文转图模式
                                                image_url = await self._render_elect_image(data, threshold, "[低余额提醒]")
                                                if image_url:
                                                    chain = MessageChain().url_image(image_url)
                                                    # 额外发送缴费链接
                                                    chain.message(f"\n━━━━━━━━━━━━━━\n自助缴费系统:\n{self.pay_url}")
                                                    await self.context.send_message(umo, chain)
                                                else:
                                                    # 渲染失败，降级为纯文本
                                                    msg = "[低余额提醒]\n" + self._format_elect_message(data, threshold)
                                                    await self.context.send_message(umo, MessageChain().message(msg))
                                            else:
                                                # 纯文本模式
                                                msg = "[低余额提醒]\n" + self._format_elect_message(data, threshold)
                                                await self.context.send_message(umo, MessageChain().message(msg))

                                            low_balance_pushed_users[umo] = current_date
                                            low_balance_push_count += 1
                                            logger.info(f"低余额推送: {umo} -> {room_id} (余额 {remaining}元 < 阈值 {threshold}元)")
                                    else:
                                        # 余额恢复，重置当日提醒状态
                                        low_balance_pushed_users.pop(umo, None)
                                else:
                                    logger.warning(f"低余额检查获取数据失败: {room_id}")

                        except Exception as e:
                            logger.error(f"推送失败 ({umo}): {e}")

                if scheduled_push_count > 0 or low_balance_push_count > 0:
                    logger.info(
                        f"推送完成 [{now.strftime('%H:%M CST')}] - "
                        f"定时: {scheduled_push_count}人, 低余额: {low_balance_push_count}人"
                    )

                # 自定义间隔时无需额外等待；整点对齐时补一个短延迟防止重入
                if self.poll_interval == 0:
                    await asyncio.sleep(65)

            except asyncio.CancelledError:
                logger.info("电费定时推送任务已取消")
                break
            except Exception as e:
                logger.error(f"电费定时推送任务出错: {e}")
                await asyncio.sleep(60)
