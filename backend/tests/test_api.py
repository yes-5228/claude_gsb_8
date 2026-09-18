"""接口级测试：覆盖台账、巡查、问题整改与统计看板。"""

from datetime import datetime, timedelta

from tests.conftest import full_items


def test_health_and_dictionaries(client):
    assert client.get("/health").json()["status"] == "ok"
    payload = client.get("/api/v1/meta/dictionaries").json()
    assert "待整改" in payload["issue_status"]
    assert len(payload["inspection_check_items"]) == 8
    assert payload["issue_transitions"]["待整改"] == ["整改中", "已关闭"]


def test_restroom_crud_and_delete_guard(client, restroom):
    assert restroom["code"].startswith("WC-")

    listed = client.get("/api/v1/restrooms", params={"district": "测试区"}).json()
    assert listed["meta"]["total"] >= 1

    detail = client.get(f"/api/v1/restrooms/{restroom['id']}").json()
    assert detail["inspection_count"] == 0
    assert detail["open_issue_count"] == 0

    updated = client.patch(
        f"/api/v1/restrooms/{restroom['id']}", json={"status": "维修中", "manager": "新责任人"}
    ).json()
    assert updated["status"] == "维修中"
    assert updated["manager"] == "新责任人"

    # 存在关联数据时不允许直接删除
    client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "测试巡查员",
            "shift": "早班",
            "items": full_items(9),
        },
    )
    blocked = client.delete(f"/api/v1/restrooms/{restroom['id']}")
    assert blocked.status_code == 409

    ok = client.delete(f"/api/v1/restrooms/{restroom['id']}", params={"force": "true"})
    assert ok.status_code == 200
    assert client.get(f"/api/v1/restrooms/{restroom['id']}").status_code == 404


def test_inspection_scoring_and_filter(client, restroom):
    good = client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "李巡查",
            "shift": "中班",
            "items": full_items(9),
            "remark": "整体良好",
        },
    ).json()
    assert good["score"] == 90.0
    assert good["grade"] == "优秀"
    assert good["result"] == "正常"

    bad_items = full_items(9)
    bad_items[0]["score"] = 3
    bad_items[0]["remark"] = "地面污渍"
    bad = client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "李巡查",
            "shift": "晚班",
            "items": bad_items,
        },
    ).json()
    assert bad["result"] == "发现问题"
    assert bad["score"] < 90

    filtered = client.get(
        "/api/v1/inspections", params={"result": "发现问题", "restroom_id": restroom["id"]}
    ).json()
    assert filtered["meta"]["total"] == 1
    assert filtered["items"][0]["id"] == bad["id"]
    assert filtered["items"][0]["restroom"]["name"] == restroom["name"]

    today = datetime.now().date().isoformat()
    ranged = client.get(
        "/api/v1/inspections", params={"date_from": today, "date_to": today}
    ).json()
    assert ranged["meta"]["total"] == 2

    duplicate = full_items(5) + [{"name": "地面与台阶清洁", "score": 4}]
    rejected = client.post(
        "/api/v1/inspections",
        json={"restroom_id": restroom["id"], "inspector": "李巡查", "items": duplicate},
    )
    assert rejected.status_code == 400

    empty = client.post(
        "/api/v1/inspections",
        json={"restroom_id": restroom["id"], "inspector": "李巡查", "items": []},
    )
    assert empty.status_code == 422


def test_issue_lifecycle(client, restroom):
    inspection = client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "王巡查",
            "items": full_items(4),
        },
    ).json()

    issue = client.post(
        "/api/v1/issues",
        json={
            "restroom_id": restroom["id"],
            "inspection_id": inspection["id"],
            "title": "地面污渍未清理",
            "description": "巡查发现地面有明显污渍",
            "category": "保洁不到位",
            "severity": "严重",
            "reporter": "王巡查",
            "assignee": "保洁班组",
            "deadline": (datetime.now() - timedelta(days=1)).isoformat(),
        },
    ).json()
    assert issue["status"] == "待整改"
    assert len(issue["records"]) == 1
    assert issue["records"][0]["action"] == "上报问题"

    # 越级流转被拒绝：待整改 -> 已完成
    invalid = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "已完成", "operator": "值班长"},
    )
    assert invalid.status_code == 400
    assert "不允许流转" in invalid.json()["detail"]

    options = client.get(f"/api/v1/issues/{issue['id']}/transitions").json()
    assert {option["status"] for option in options} == {"整改中", "已关闭"}

    processing = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "整改中", "operator": "保洁班组张伟", "remark": "已安排清洗"},
    ).json()
    assert processing["status"] == "整改中"
    assert processing["assignee"] == "保洁班组"

    reviewing = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "待验收", "operator": "保洁班组张伟", "remark": "整改完成待验收"},
    ).json()
    assert reviewing["status"] == "待验收"

    # 验收驳回回到整改中
    rejected = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "整改中", "operator": "王巡查", "remark": "角落仍有残留"},
    ).json()
    assert rejected["status"] == "整改中"
    assert rejected["records"][-1]["action"] == "验收驳回"

    for target in ("待验收", "已完成", "已关闭"):
        payload = {"to_status": target, "operator": "值班长", "remark": f"流转到{target}"}
        response = client.post(f"/api/v1/issues/{issue['id']}/transitions", json=payload)
        assert response.status_code == 200, response.text
    final = response.json()
    assert final["status"] == "已关闭"
    assert final["closed_at"] is not None
    assert [record["to_status"] for record in final["records"]][-1] == "已关闭"

    closed_record = client.post(
        f"/api/v1/issues/{issue['id']}/records",
        json={"action": "整改进度", "operator": "值班长", "remark": "补充说明"},
    )
    assert closed_record.status_code == 400

    overdue = client.get("/api/v1/issues", params={"overdue": "true"}).json()
    assert overdue["meta"]["total"] == 0

    # 巡查记录可反查关联问题数量
    detail = client.get(f"/api/v1/inspections/{inspection['id']}").json()
    assert detail["issue_count"] == 1


def test_issue_requires_matching_restroom(client, restroom):
    other = client.post(
        "/api/v1/restrooms",
        json={"name": "另一座公厕", "district": "测试区", "address": "测试路 2 号"},
    ).json()
    inspection = client.post(
        "/api/v1/inspections",
        json={"restroom_id": other["id"], "inspector": "周巡查", "items": full_items(9)},
    ).json()
    mismatch = client.post(
        "/api/v1/issues",
        json={
            "restroom_id": restroom["id"],
            "inspection_id": inspection["id"],
            "title": "关联错误",
        },
    )
    assert mismatch.status_code == 400
    assert "不一致" in mismatch.json()["detail"]


def test_dashboard_stats(client, restroom):
    payload = client.get("/api/v1/stats/dashboard", params={"trend_days": 7}).json()
    overview = payload["overview"]
    assert overview["restroom_total"] >= 1
    assert overview["inspection_total"] >= 1
    assert len(payload["inspection_trend"]) == 7
    assert {item["name"] for item in payload["issue_by_status"]} == {
        "待整改",
        "整改中",
        "待验收",
        "已完成",
        "已关闭",
    }
    assert payload["top_restrooms"]
    assert "rectification_rate" in overview


def test_complaint_lifecycle(client, restroom):
    # 受理登记：分类留空，按内容自动判定
    created = client.post(
        "/api/v1/complaints",
        json={
            "restroom_id": restroom["id"],
            "source": "热线转办",
            "content": "市民来电反映水龙头损坏漏水，请尽快维修",
            "reporter_name": "王先生",
            "reporter_phone": "13800000000",
            "receiver": "坐席员小陈",
        },
    )
    assert created.status_code == 201, created.text
    complaint = created.json()
    assert complaint["code"].startswith("SQ-")
    assert complaint["category"] == "设施损坏"
    assert complaint["status"] == "待分派"
    assert complaint["records"][0]["action"] == "受理登记"

    # 未分派前不能登记处理结果
    early = client.post(
        f"/api/v1/complaints/{complaint['id']}/finish",
        json={"result": "已维修", "operator": "李维修"},
    )
    assert early.status_code == 400

    # 分派处理人
    assigned = client.post(
        f"/api/v1/complaints/{complaint['id']}/assign",
        json={"handler": "李维修", "operator": "值班长"},
    ).json()
    assert assigned["status"] == "处理中"
    assert assigned["handler"] == "李维修"
    assert assigned["records"][-1]["action"] == "分派处理人"

    # 处理完成，登记结果
    finished = client.post(
        f"/api/v1/complaints/{complaint['id']}/finish",
        json={"result": "已更换阀芯，供水恢复正常", "operator": "李维修"},
    ).json()
    assert finished["status"] == "待回访"
    assert finished["result"] == "已更换阀芯，供水恢复正常"

    # 未联系上时必须约定下次回访时间
    missing = client.post(
        f"/api/v1/complaints/{complaint['id']}/follow-ups",
        json={"result": "未联系上", "operator": "回访员小周"},
    )
    assert missing.status_code == 400

    # 回访未联系上：保持待回访并安排再次回访
    next_time = (datetime.now() + timedelta(days=1)).isoformat()
    unreachable = client.post(
        f"/api/v1/complaints/{complaint['id']}/follow-ups",
        json={
            "result": "未联系上",
            "operator": "回访员小周",
            "next_follow_time": next_time,
            "remark": "电话无人接听",
        },
    ).json()
    assert unreachable["status"] == "待回访"
    assert unreachable["next_follow_time"] is not None
    assert unreachable["follow_ups"][0]["result"] == "未联系上"
    assert unreachable["records"][-1]["action"] == "回访未联系上"

    # 再次回访联系上：办结并清空下次回访时间
    reached = client.post(
        f"/api/v1/complaints/{complaint['id']}/follow-ups",
        json={"result": "已联系上", "satisfaction": "满意", "operator": "回访员小周"},
    ).json()
    assert reached["status"] == "已办结"
    assert reached["next_follow_time"] is None
    assert len(reached["follow_ups"]) == 2
    assert reached["follow_ups"][1]["satisfaction"] == "满意"

    # 办结后不能再回访
    late = client.post(
        f"/api/v1/complaints/{complaint['id']}/follow-ups",
        json={"result": "已联系上", "operator": "回访员小周"},
    )
    assert late.status_code == 400


def test_complaint_classification_filters_and_close(client, restroom):
    # 分类预判接口
    odor = client.post("/api/v1/complaints/classify", json={"content": "里面异味很大，熏人"})
    assert odor.json()["category"] == "异味扰民"
    plain = client.post("/api/v1/complaints/classify", json={"content": "建议延长开放时间"})
    assert plain.json()["category"] == "其他"

    hotline = client.post(
        "/api/v1/complaints",
        json={
            "restroom_id": restroom["id"],
            "source": "热线转办",
            "content": "市民反映厕纸没有了",
            "reporter_phone": "13911111111",
        },
    ).json()
    assert hotline["category"] == "耗材缺失"
    public = client.post(
        "/api/v1/complaints",
        json={
            "restroom_id": restroom["id"],
            "source": "群众反映",
            "content": "建议增加指示牌",
            "reporter_phone": "13922222222",
        },
    ).json()

    # 按来源 / 状态筛选
    by_source = client.get("/api/v1/complaints", params={"source": "热线转办"}).json()
    assert by_source["meta"]["total"] >= 1
    assert all(item["source"] == "热线转办" for item in by_source["items"])
    by_keyword = client.get("/api/v1/complaints", params={"keyword": "13922222222"}).json()
    assert by_keyword["meta"]["total"] == 1

    # 待分派可直接作废关闭
    closed = client.post(
        f"/api/v1/complaints/{public['id']}/close",
        json={"operator": "值班长", "remark": "重复反映，合并办理"},
    ).json()
    assert closed["status"] == "已关闭"
    assert closed["closed_at"] is not None

    # 关闭后不允许再分派
    reassign = client.post(
        f"/api/v1/complaints/{public['id']}/assign",
        json={"handler": "张三", "operator": "值班长"},
    )
    assert reassign.status_code == 400

    # 处理中的诉求可以改派
    client.post(
        f"/api/v1/complaints/{hotline['id']}/assign",
        json={"handler": "刘桂芳", "operator": "值班长"},
    )
    changed = client.post(
        f"/api/v1/complaints/{hotline['id']}/assign",
        json={"handler": "孙鹏", "operator": "值班长", "remark": "调整责任区域"},
    ).json()
    assert changed["handler"] == "孙鹏"
    assert changed["records"][-1]["action"] == "改派处理人"

    # 回访提醒：finish 后登记一次未联系上且下次回访时间已过
    client.post(
        f"/api/v1/complaints/{hotline['id']}/finish",
        json={"result": "已补充厕纸", "operator": "孙鹏"},
    )
    client.post(
        f"/api/v1/complaints/{hotline['id']}/follow-ups",
        json={
            "result": "未联系上",
            "operator": "回访员小周",
            "next_follow_time": (datetime.now() - timedelta(hours=2)).isoformat(),
        },
    )
    due = client.get("/api/v1/complaints", params={"follow_due": "true"}).json()
    assert any(item["id"] == hotline["id"] for item in due["items"])

    # 字典包含诉求相关枚举
    dictionaries = client.get("/api/v1/meta/dictionaries").json()
    assert "待回访" in dictionaries["complaint_status"]
    assert "未联系上" in dictionaries["follow_up_result"]


def test_complaint_update_reclassifies(client, restroom):
    complaint = client.post(
        "/api/v1/complaints",
        json={
            "restroom_id": restroom["id"],
            "source": "群众反映",
            "content": "公厕内异味很大，希望加强通风",
            "reporter_phone": "13700000000",
        },
    ).json()
    assert complaint["category"] == "异味扰民"

    # 修改内容且分类置空：按新内容重新判定
    updated = client.patch(
        f"/api/v1/complaints/{complaint['id']}",
        json={"content": "水龙头损坏一直漏水", "category": None},
    ).json()
    assert updated["category"] == "设施损坏"

    # 显式指定分类时以指定为准
    manual = client.patch(
        f"/api/v1/complaints/{complaint['id']}", json={"category": "其他"}
    ).json()
    assert manual["category"] == "其他"

    # 办结/关闭后不允许再补正
    client.post(f"/api/v1/complaints/{complaint['id']}/close", json={"operator": "值班长"})
    blocked = client.patch(
        f"/api/v1/complaints/{complaint['id']}", json={"content": "试图修改"}
    )
    assert blocked.status_code == 400
