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


def test_complaint_classify(client):
    payload = client.post(
        "/api/v1/complaints/classify", json={"content": "水龙头损坏漏水，冲水设备故障"}
    ).json()
    assert payload["category"] == "设施损坏"
    assert "漏水" in payload["matched"]

    odor = client.post("/api/v1/complaints/classify", json={"content": "厕内臭味刺鼻"}).json()
    assert odor["category"] == "异味扰民"

    unknown = client.post("/api/v1/complaints/classify", json={"content": "随便问问"}).json()
    assert unknown["category"] == "其他"


def test_complaint_lifecycle(client, restroom):
    # 登记受理：不填分类时按内容自动判定
    complaint = client.post(
        "/api/v1/complaints",
        json={
            "restroom_id": restroom["id"],
            "source": "12345转办",
            "content": "群众反映厕纸长时间未补充，洗手液也空了",
            "contact_name": "张先生",
            "contact_phone": "13800000000",
        },
    )
    assert complaint.status_code == 201, complaint.text
    complaint = complaint.json()
    assert complaint["status"] == "待受理"
    assert complaint["category"] == "耗材缺失"
    assert complaint["code"].startswith("FS-")
    assert complaint["records"][0]["action"] == "登记受理"

    # 越级流转被拒绝：待受理 -> 待回访
    invalid = client.post(
        f"/api/v1/complaints/{complaint['id']}/transitions",
        json={"to_status": "待回访", "operator": "值班长", "result": "已处理"},
    )
    assert invalid.status_code == 400

    # 受理分派：处理人随流转登记
    accepted = client.post(
        f"/api/v1/complaints/{complaint['id']}/transitions",
        json={"to_status": "处理中", "operator": "街办保洁队", "remark": "已分派核实"},
    ).json()
    assert accepted["status"] == "处理中"
    assert accepted["assignee"] == "街办保洁队"

    # 办结必须填写处理结果
    missing_result = client.post(
        f"/api/v1/complaints/{complaint['id']}/transitions",
        json={"to_status": "待回访", "operator": "街办保洁队"},
    )
    assert missing_result.status_code == 400
    assert "处理结果" in missing_result.json()["detail"]

    handled = client.post(
        f"/api/v1/complaints/{complaint['id']}/transitions",
        json={
            "to_status": "待回访",
            "operator": "街办保洁队",
            "result": "已补充厕纸与洗手液，现场复查合格",
        },
    ).json()
    assert handled["status"] == "待回访"
    assert handled["handled_at"] is not None

    # 未联系上必须约定再次回访时间
    no_schedule = client.post(
        f"/api/v1/complaints/{complaint['id']}/visits",
        json={"visitor": "值班员", "result": "未联系上"},
    )
    assert no_schedule.status_code == 400

    retry_at = (datetime.now() + timedelta(days=1)).isoformat()
    unreachable = client.post(
        f"/api/v1/complaints/{complaint['id']}/visits",
        json={
            "visitor": "值班员",
            "result": "未联系上",
            "note": "电话无人接听",
            "next_visit_at": retry_at,
        },
    ).json()
    assert unreachable["status"] == "待回访"
    assert unreachable["next_visit_at"] is not None
    assert unreachable["visits"][-1]["result"] == "未联系上"
    assert unreachable["records"][-1]["action"] == "回访未联系上"

    # 再次回访联系上但不满意 -> 退回处理中
    returned = client.post(
        f"/api/v1/complaints/{complaint['id']}/visits",
        json={"visitor": "值班员", "result": "联系上-不满意", "note": "反映人称耗材又断了"},
    ).json()
    assert returned["status"] == "处理中"

    # 重新办结后回访满意 -> 已办结 -> 归档关闭
    client.post(
        f"/api/v1/complaints/{complaint['id']}/transitions",
        json={"to_status": "待回访", "operator": "街办保洁队", "result": "已建立每日补充机制"},
    )
    done = client.post(
        f"/api/v1/complaints/{complaint['id']}/visits",
        json={"visitor": "值班员", "result": "联系上-满意", "note": "反映人表示满意"},
    ).json()
    assert done["status"] == "已办结"
    assert done["next_visit_at"] is None

    closed = client.post(
        f"/api/v1/complaints/{complaint['id']}/transitions",
        json={"to_status": "已关闭", "operator": "值班长", "remark": "归档"},
    ).json()
    assert closed["status"] == "已关闭"
    assert closed["closed_at"] is not None

    # 已关闭后不能再登记回访
    rejected_visit = client.post(
        f"/api/v1/complaints/{complaint['id']}/visits",
        json={"visitor": "值班员", "result": "联系上-满意"},
    )
    assert rejected_visit.status_code == 400

    # 列表筛选：来源 / 关键字 / 状态
    by_source = client.get("/api/v1/complaints", params={"source": "12345转办"}).json()
    assert by_source["meta"]["total"] >= 1
    by_keyword = client.get("/api/v1/complaints", params={"keyword": "13800000000"}).json()
    assert by_keyword["meta"]["total"] == 1
    open_only = client.get("/api/v1/complaints", params={"open_only": "true"}).json()
    assert all(item["status"] != "已关闭" for item in open_only["items"])

    # 存在群众反映记录的公厕不允许直接删除
    blocked = client.delete(f"/api/v1/restrooms/{restroom['id']}")
    assert blocked.status_code == 409
    assert "群众反映" in blocked.json()["detail"]


def test_complaint_visit_due_filter(client, restroom):
    complaint = client.post(
        "/api/v1/complaints",
        json={
            "restroom_id": restroom["id"],
            "source": "热线电话",
            "content": "厕内异味明显，希望加强通风",
            "contact_name": "李女士",
        },
    ).json()
    client.post(
        f"/api/v1/complaints/{complaint['id']}/transitions",
        json={"to_status": "处理中", "operator": "片区管理员"},
    )
    client.post(
        f"/api/v1/complaints/{complaint['id']}/transitions",
        json={"to_status": "待回访", "operator": "片区管理员", "result": "已加强通风除臭"},
    )
    due = client.get("/api/v1/complaints", params={"visit_due": "true"}).json()
    assert any(item["id"] == complaint["id"] for item in due["items"])

    # 约了未来再次回访时间的，不出现在“当前需回访”列表
    client.post(
        f"/api/v1/complaints/{complaint['id']}/visits",
        json={
            "visitor": "值班员",
            "result": "未联系上",
            "next_visit_at": (datetime.now() + timedelta(days=2)).isoformat(),
        },
    )
    due_after = client.get("/api/v1/complaints", params={"visit_due": "true"}).json()
    assert all(item["id"] != complaint["id"] for item in due_after["items"])
