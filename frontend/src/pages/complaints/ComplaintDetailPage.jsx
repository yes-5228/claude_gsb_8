import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { complaintApi } from '../../api/complaints.js';
import DetailList from '../../components/DetailList.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import { FollowDueTag, FollowUpResultTag, StatusTag } from '../../components/Tags.jsx';
import Timeline from '../../components/Timeline.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { formatDateTime } from '../../utils/format.js';
import ComplaintActionModal from './ComplaintActionModal.jsx';
import ComplaintFollowUpModal from './ComplaintFollowUpModal.jsx';
import ComplaintFormModal from './ComplaintFormModal.jsx';

export default function ComplaintDetailPage() {
  const { complaintId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [action, setAction] = useState(null); // assign | reassign | finish | close
  const [showFollowUp, setShowFollowUp] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [saving, setSaving] = useState(false);

  const { data: complaint, loading, error, reload } = useAsync(
    () => complaintApi.detail(complaintId),
    [complaintId],
  );

  const runAction = async (request, successText) => {
    setSaving(true);
    try {
      await request();
      toast.success(successText);
      setAction(null);
      setShowFollowUp(false);
      reload();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const submitAction = (payload) => {
    if (action === 'assign' || action === 'reassign') {
      return runAction(
        () =>
          complaintApi.assign(complaintId, {
            handler: payload.handler,
            operator: payload.operator,
            remark: payload.remark,
          }),
        action === 'assign' ? '已分派处理人' : '已改派处理人',
      );
    }
    if (action === 'finish') {
      return runAction(
        () =>
          complaintApi.finish(complaintId, {
            result: payload.result,
            operator: payload.operator,
            remark: payload.remark,
          }),
        '处理结果已登记，进入回访环节',
      );
    }
    if (action === 'close') {
      return runAction(
        () =>
          complaintApi.close(complaintId, { operator: payload.operator, remark: payload.remark }),
        '诉求已作废关闭',
      );
    }
    return undefined;
  };

  const submitFollowUp = (payload) =>
    runAction(
      () => complaintApi.addFollowUp(complaintId, payload),
      payload.result === '已联系上' ? '回访完成，诉求已办结' : '已登记，将按约定时间再次回访',
    );

  const remove = async () => {
    if (!window.confirm('确认删除该诉求及其办理、回访记录？')) return;
    try {
      await complaintApi.remove(complaintId);
      toast.success('已删除');
      navigate('/complaints');
    } catch (err) {
      toast.error(err.message);
    }
  };

  const editable = complaint && !['已办结', '已关闭'].includes(complaint.status);

  return (
    <>
      <PageHeader
        title={complaint ? `诉求 ${complaint.code}` : '诉求详情'}
        description={complaint ? `${complaint.source} · ${complaint.category}` : '加载中…'}
        actions={
          <>
            <Link className="btn" to="/complaints">
              返回列表
            </Link>
            {editable ? (
              <button type="button" className="btn" onClick={() => setShowEdit(true)}>
                补正登记
              </button>
            ) : null}
            <button type="button" className="btn btn-danger" onClick={remove}>
              删除
            </button>
          </>
        }
      />
      <div className="content">
        {error ? <div className="alert alert-error">{error.message}</div> : null}
        {loading && !complaint ? <div className="loading-block">加载中...</div> : null}

        {complaint ? (
          <>
            <section className="card">
              <div className="card-title">
                <div className="inline">
                  <h3>{complaint.category}</h3>
                  <StatusTag status={complaint.status} />
                  <FollowDueTag
                    nextFollowTime={complaint.next_follow_time}
                    status={complaint.status}
                  />
                </div>
                <span className="hint">最后更新：{formatDateTime(complaint.updated_at)}</span>
              </div>
              <DetailList
                items={[
                  {
                    label: '涉及公厕',
                    value: complaint.restroom ? (
                      <Link to={`/restrooms/${complaint.restroom.id}`}>
                        {complaint.restroom.name}（{complaint.restroom.district}）
                      </Link>
                    ) : (
                      '-'
                    ),
                  },
                  { label: '诉求来源', value: complaint.source },
                  {
                    label: '反映人',
                    value: `${complaint.reporter_name || '匿名'} · ${complaint.reporter_phone}`,
                  },
                  {
                    label: '受理人 / 时间',
                    value: `${complaint.receiver || '-'} · ${formatDateTime(complaint.received_at)}`,
                  },
                  { label: '处理人', value: complaint.handler || '未分派' },
                  { label: '分派时间', value: formatDateTime(complaint.assigned_at) },
                  { label: '办结时间', value: formatDateTime(complaint.finished_at) },
                  {
                    label: '下次回访',
                    value: complaint.next_follow_time
                      ? formatDateTime(complaint.next_follow_time)
                      : '未安排',
                  },
                  { label: '反映内容', value: complaint.content },
                  { label: '处理结果', value: complaint.result || '待处理' },
                ]}
              />
            </section>

            <section className="card">
              <div className="card-title">
                <h3>办理操作</h3>
                <span className="hint">受理 → 分派 → 处理 → 回访，逐步推进</span>
              </div>
              {complaint.status === '待分派' ? (
                <div className="action-group">
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => setAction('assign')}
                  >
                    分派处理人
                  </button>
                  <button type="button" className="btn" onClick={() => setAction('close')}>
                    作废关闭
                  </button>
                </div>
              ) : null}
              {complaint.status === '处理中' ? (
                <div className="action-group">
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => setAction('finish')}
                  >
                    处理完成，登记结果
                  </button>
                  <button type="button" className="btn" onClick={() => setAction('reassign')}>
                    改派处理人
                  </button>
                  <button type="button" className="btn" onClick={() => setAction('close')}>
                    作废关闭
                  </button>
                </div>
              ) : null}
              {complaint.status === '待回访' ? (
                <>
                  <div className="action-group">
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={() => setShowFollowUp(true)}
                    >
                      登记回访
                    </button>
                  </div>
                  <div className="alert alert-info" style={{ marginTop: 12 }}>
                    请按联系方式回访反映人；若未联系上，可约定下次回访时间，系统将在列表中提醒再次回访。
                  </div>
                </>
              ) : null}
              {complaint.status === '已办结' ? (
                <div className="alert alert-info">该诉求已回访办结，流程结束。</div>
              ) : null}
              {complaint.status === '已关闭' ? (
                <div className="alert alert-info">该诉求已作废关闭。</div>
              ) : null}
            </section>

            <section className="card">
              <div className="card-title">
                <h3>回访记录</h3>
                <span className="hint">共 {complaint.follow_ups.length} 次回访</span>
              </div>
              {complaint.follow_ups.length ? (
                <ol className="timeline">
                  {complaint.follow_ups.map((item) => (
                    <li key={item.id}>
                      <div className="head">
                        <FollowUpResultTag result={item.result} />
                        {item.satisfaction ? (
                          <span className="tag tag-primary">满意度：{item.satisfaction}</span>
                        ) : null}
                        <span className="time">{formatDateTime(item.created_at)}</span>
                        <span className="muted">回访人：{item.operator}</span>
                      </div>
                      {item.remark ? <div className="remark">{item.remark}</div> : null}
                    </li>
                  ))}
                </ol>
              ) : (
                <div className="empty-block">处理完成并登记结果后即可开展回访</div>
              )}
            </section>

            <section className="card">
              <div className="card-title">
                <h3>办理轨迹</h3>
                <span className="hint">共 {complaint.records.length} 条记录</span>
              </div>
              <Timeline records={complaint.records} />
            </section>
          </>
        ) : null}
      </div>

      {action && complaint ? (
        <ComplaintActionModal
          mode={action}
          complaint={complaint}
          saving={saving}
          onClose={() => setAction(null)}
          onSubmit={submitAction}
        />
      ) : null}

      {showFollowUp && complaint ? (
        <ComplaintFollowUpModal
          complaint={complaint}
          saving={saving}
          onClose={() => setShowFollowUp(false)}
          onSubmit={submitFollowUp}
        />
      ) : null}

      {showEdit && complaint ? (
        <ComplaintFormModal
          complaint={complaint}
          onClose={() => setShowEdit(false)}
          onSaved={reload}
        />
      ) : null}
    </>
  );
}
