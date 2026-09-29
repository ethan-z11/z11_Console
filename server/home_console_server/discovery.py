"""从 HA 自动发现控制台要显示的实体，并按设置中的黑名单 / 白名单过滤。

- 房间不再取自 HA 区域：房间由控制台设置完全手动维护（见 store.py 的 custom.json），设备手动加入房间；
  未加入任何房间的设备不在页面显示。实体上仍保留 areaId 仅作设置页参考。
- 收录灯、温控、播放器、风扇（fan，含新风机 / 浴霸换气）、窗帘（cover）、场景类实体
  （scene / script / button / input_button / automation）、人员，以及
  温度 / 湿度 / 电池 / 农历传感器和门窗 / 人体 / 水浸 / 烟雾类二元传感器。场景类实体只用于“情景模式”按钮，
  不生成设备卡，也不参与黑白名单（不少家庭的情景实际是无线开关的 button 实体或自动化）。
- 每个实体附带 HA 标签（label_registry + 实体注册表 labels），设置页选择器按标签名称分组与筛选。
- 在 HA 中被禁用、隐藏或属于配置 / 诊断类别的实体不参与发现；需要隐藏某个设备时也可以直接在 HA 里隐藏。
"""

from __future__ import annotations

from typing import Any

SENSOR_CLASSES = {"temperature", "humidity", "battery"}
BINARY_CLASSES = {
    "door", "window", "opening", "garage_door",
    "motion", "occupancy", "presence",
    "moisture",
    "smoke", "gas", "carbon_monoxide",
}
CONTROL_DOMAINS = {"light", "climate", "media_player", "fan", "cover"}
# 情景模式按钮可指向的“一键执行”类实体域：
# scene / script 用 turn_on，button / input_button 用 press，automation 用 trigger。
SCENE_DOMAINS = {"scene", "script", "button", "input_button", "automation"}
NAME_SEPARATORS = " -－—_·:："
# 第三方农历集成的实体 id 常见写法；中文名称中带“农历”的也按农历实体识别。
LUNAR_ID_KEYWORDS = ("lunar", "nongli")
LUNAR_NAME_KEYWORD = "农历"


def is_lunar_entity(domain: str, entity_id: str, friendly_name: str) -> bool:
    """识别农历传感器：名称含“农历”，或实体 id 含 lunar/nongli。它的 state 直接显示在我的家庭页副标题。"""
    if domain != "sensor":
        return False
    lowered = entity_id.lower()
    return LUNAR_NAME_KEYWORD in friendly_name or any(keyword in lowered for keyword in LUNAR_ID_KEYWORDS)


def relevant(domain: str, device_class: str | None) -> bool:
    if domain in CONTROL_DOMAINS or domain in SCENE_DOMAINS or domain == "person":
        return True
    if domain == "sensor":
        return device_class in SENSOR_CLASSES
    if domain == "binary_sensor":
        return device_class in BINARY_CLASSES
    return False


def display_name(friendly_name: str, area_name: str | None) -> str:
    """去掉名称开头重复的区域名，例如“客厅-背景灯”在客厅中显示为“背景灯”。"""
    if area_name and friendly_name.startswith(area_name):
        rest = friendly_name[len(area_name):].lstrip(NAME_SEPARATORS)
        if rest:
            return rest
    return friendly_name


def area_from_name(friendly_name: str, areas: list[dict[str, Any]]) -> str | None:
    """按“区域-设备”命名取最长匹配的区域名。"""
    matches = [area for area in areas if area["name"] and friendly_name.startswith(area["name"])]
    return max(matches, key=lambda area: len(area["name"]))["area_id"] if matches else None


def display_precision(entry: dict[str, Any]) -> int | None:
    """HA 中传感器的显示小数位：用户在 HA 设置的优先，其次集成建议的；原始状态可能带浮点误差（如 27.700006）。"""
    options = (entry.get("options") or {}).get("sensor") or {}
    for key in ("display_precision", "suggested_display_precision"):
        value = options.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 6:
            return value
    return None


def build_catalogue(areas: list[dict[str, Any]], devices: list[dict[str, Any]], registry: list[dict[str, Any]],
                    labels: list[dict[str, Any]], states: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """返回全部发现结果：labels 为标签表，rooms 为 HA 区域（仅参考），entities 为可显示的实体（不含过滤）。"""
    entries = {entry["entity_id"]: entry for entry in registry}
    device_area = {device["id"]: device.get("area_id") for device in devices}
    area_names = {area["area_id"]: area["name"] for area in areas}
    label_names = {label["label_id"]: label.get("name") or label["label_id"] for label in labels}
    entities: list[dict[str, Any]] = []
    for entity_id, state in states.items():
        domain = entity_id.split(".")[0]
        attributes = state.get("attributes") or {}
        entry = entries.get(entity_id) or {}
        if entry.get("disabled_by") or entry.get("hidden_by") or entry.get("entity_category"):
            continue
        device_class = attributes.get("device_class") or entry.get("device_class") or entry.get("original_device_class")
        friendly = str(attributes.get("friendly_name") or entry.get("name") or entry.get("original_name") or entity_id)
        lunar = is_lunar_entity(domain, entity_id, friendly)
        if not lunar and not relevant(domain, device_class):
            continue
        area_id = entry.get("area_id") or device_area.get(entry.get("device_id"))
        if area_id not in area_names:
            area_id = area_from_name(friendly, areas)
        entity_labels = [
            {"id": label_id, "name": label_names.get(label_id, label_id)}
            for label_id in (entry.get("labels") or [])
            if isinstance(label_id, str) and label_id in label_names
        ]
        entity = {
            "id": entity_id,
            "domain": domain,
            "deviceClass": "lunar" if lunar else device_class,
            "areaId": area_id,
            "name": display_name(friendly, area_names.get(area_id)),
            "labels": entity_labels,
        }
        if not lunar and domain == "sensor" and (precision := display_precision(entry)) is not None:
            entity["precision"] = precision
        entities.append(entity)
    used = {entity["areaId"] for entity in entities}
    rooms = [{"id": area["area_id"], "name": area["name"]} for area in areas if area["area_id"] in used]
    return {
        "labels": [{"id": label["label_id"], "name": label.get("name") or label["label_id"]} for label in labels],
        "rooms": rooms,
        "entities": entities,
    }


def visible_ids(catalogue: dict[str, Any], mode: str, blacklist: list[str], whitelist: list[str]) -> set[str]:
    """黑白名单只管设备卡类实体；场景 / 脚本由情景按钮配置决定，不能在这里被过滤掉。"""
    ids = {entity["id"] for entity in catalogue["entities"] if entity["domain"] not in SCENE_DOMAINS}
    if mode == "whitelist":
        return ids & set(whitelist)
    return ids - set(blacklist)


def filtered(catalogue: dict[str, Any], ids: set[str]) -> dict[str, Any]:
    """页面用的目录：场景 / 脚本始终保留（情景选择器需要），其余实体只含可见的。"""
    entities = [entity for entity in catalogue["entities"]
                if entity["domain"] in SCENE_DOMAINS or entity["id"] in ids]
    used = {entity["areaId"] for entity in entities if entity["domain"] not in SCENE_DOMAINS}
    return {"labels": catalogue.get("labels", []), "rooms": [room for room in catalogue["rooms"] if room["id"] in used], "entities": entities}
