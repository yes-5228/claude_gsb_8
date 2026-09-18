import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { complaintApi } from '../../api/complaints.js';
import DataTable from '../../components/DataTable.jsx';
import DetailList from '../../components/DetailList.jsx';
import Field from '../../components/Field.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import { StatusTag } from '../../components/Tags.jsx';
import Timeline from '../../components/Timeline.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { formatDateTime, toDateTimeInput } from '../../utils/format.js';
import ComplaintActionModal from './ComplaintActionModal.jsx';
import ComplaintEditModal from './ComplaintEditModal.jsx';

const EMPTY_VISIT = { visitor: '', result: '联系上-满意', note: '', next_visit_at: '' };

export default function ComplaintDetailPage() {
  const { complaintId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { dictionaries } = useDictionaries();
  const [activeOption, setActiveOption] = useState(null);
  const [showEdit, setShowEdit] = useState(false);
  const [saving, setSaving] = useState(false);
  const [visit, setVisit] = useState(EMPTY_VISIT);
  const [visitError, setVisitError] = useState(null);

  const {
    data: complaint,
    loading,
    error,
    reload,
  } = useAsync(() => complaintApi.detail(complaintId), [complaintId]);
  const { data: options, reload: reloadOptions } = useAsync(
    () => complaintApi.transitions(complaintId),
    [complaintId],
  );

  const refresh = () => {
    reload();
    reloadOptions();
  };

  const submitTransition = async (payload) => {
    setSaving(true);
    try {
      await complaintApi.changeStatus(complaintId, payload);
      toast.success('办理状态已更新');
      setActiveOption(null);
      refresh();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const submitVisit = async (event) => {
    event.preventDefault();
    if (!visit.visitor.trim()) {
      setVisitError('请填写回访人');
      return;
    }
    if (visit.result === '未联系上' && !visit.next_visit_at) {
      setVisitError('未联系上反映人，请约定再次回访时间');
      return;
    }
    setVisitError(null);
    try {
      await complaintApi.addVisit(complaintId, {
        visitor: visit.visitor.trim(),
        result: visit.result,
        note: visit.note || null,
        next_visit_at:
          visit.result === '未联系上' && visit.next_visit_at
            ? new Date(visit.next_visit_at).toISOString()
            : null,
      });
      toast.success(
        visit.result === '未联系上' ? '已登记，等待再次回访' : '回访结果已登记',
      );
      setVisit(EMPTY_VISIT);
      refresh();
    } catch (err) {
      setVisitError(err.message);
    }
  };

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

  return (
    <>
      <PageHeader
        title={complaint ? `诉求 ${complaint.code}` : '诉求详情'}
        description={complaint ? `${complaint.source} · ${complaint.category}` : ''}
        actions={
          <>
            <Link className="btn" to="/complaints">
              返回列表
            </Link>
            <button type="button" className="btn" onClick={() => setShowEdit(true)}>
              编辑信息
            </button>
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
                  { label: '反映来源', value: complaint.source },
                  {
                    label: '反映人 / 联系方式',
                    value: `${complaint.contact_name || '匿名'} · ${complaint.contact_phone || '未留'}`,
                  },
                  { label: '处理人', value: complaint.assignee || '未分派' },
                  { label: '登记时间', value: formatDateTime(complaint.received_at) },
                  { label: '办结时间', value: formatDateTime(complaint.handled_at) },
                  {
                    label: '下次回访',
                    value:
                      complaint.status === '待回访'
                        ? formatDateTime(complaint.next_visit_at)
                        : '-',
                  },
                  { label: '关闭时间', value: formatDateTime(complaint.closed_at) },
                  { label: '反映内容', value: complaint.content },
                  { label: '处理结果', value: complaint.result || '尚未办结' },
                ]}
              />
            </section>

            <section className="card">
              <div className="card-title">
                <h3>办理流转</h3>
                <span className="hint">受理分派 → 处理 → 办结待回访 → 回访闭环</span>
              </div>
              {options?.length ? (
                <div className="action-group">
                  {options.map((option) => (
                    <button
                      key={option.status}
                      type="button"
                      className={`btn${option.status === '待回访' ? ' btn-primary' : ''}`}
                      onClick={() => setActiveOption(option)}
                    >
                      {option.action}（变更为「{option.status}」）
                    </button>
                  ))}
                </div>
              ) : (
                <div className="alert alert-info">
                  {complaint.status === '待回访'
                    ? '等待回访反映人，请在下方登记回访结果。'
                    : '该诉求已关闭，办理流程结束。'}
                </div>
              )}

              {complaint.status === '待回访' ? (
                <form className="form-grid" style={{ marginTop: 18 }} onSubmit={submitVisit}>
                  <Field label="回访人 *">
                    <input
                      value={visit.visitor}
                      onChange={(event) =>
                        setVisit((prev) => ({ ...prev, visitor: event.target.value }))
                      }
                      placeholder="如：值班员小赵"
                    />
                  </Field>
                  <Field label="回访结果">
                    <select
                      value={visit.result}
                      onChange={(event) =>
                        setVisit((prev) => ({ ...prev, result: event.target.value }))
                      }
                    >
                      {(dictionaries?.complaint_visit_result || []).map((item) => (
                        <option key={item}>{item}</option>
                      ))}
                    </select>
                  </Field>
                  {visit.result === '未联系上' ? (
                    <Field label="再次回访时间 *" hint="到点后出现在「当前需回访」列表">
                      <input
                        type="datetime-local"
                        value={visit.next_visit_at}
                        min={toDateTimeInput(new Date())}
                        onChange={(event) =>
                          setVisit((prev) => ({ ...prev, next_visit_at: event.target.value }))
                        }
                      />
                    </Field>
                  ) : null}
                  <Field label="回访说明" full>
                    <textarea
                      rows="2"
                      value={visit.note}
                      onChange={(event) =>
                        setVisit((prev) => ({ ...prev, note: event.target.value }))
                      }
                      placeholder={
                        visit.result === '未联系上'
                          ? '如：两次拨打电话无人接听'
                          : '记录反映人的反馈意见'
                      }
                    />
                  </Field>
                  {visitError ? <div className="alert alert-error full">{visitError}</div> : null}
                  <div className="full">
                    <button type="submit" className="btn btn-primary">
                      登记回访结果
                    </button>
                    <span className="hint" style={{ marginLeft: 12 }}>
                      满意办结归档，不满意退回重新处理，未联系上安排再次回访
                    </span>
                  </div>
                </form>
              ) : null}
            </section>

            <section className="card">
              <div className="card-title">
                <h3>回访记录</h3>
                <span className="hint">共 {complaint.visits.length} 次回访</span>
              </div>
              <DataTable
                rows={complaint.visits}
                emptyText="暂无回访记录"
                columns={[
                  {
                    key: 'visit_time',
                    title: '回访时间',
                    render: (row) => formatDateTime(row.visit_time),
                  },
                  { key: 'visitor', title: '回访人' },
                  {
                    key: 'result',
                    title: '结果',
                    render: (row) => <StatusTag status={row.result} />,
                  },
                  { key: 'note', title: '回访说明', wrap: true, render: (row) => row.note || '-' },
                  {
                    key: 'next_visit_at',
                    title: '再次回访安排',
                    render: (row) => formatDateTime(row.next_visit_at),
                  },
                ]}
              />
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

      {activeOption && complaint ? (
        <ComplaintActionModal
          option={activeOption}
          complaint={complaint}
          saving={saving}
          onClose={() => setActiveOption(null)}
          onSubmit={submitTransition}
        />
      ) : null}

      {showEdit && complaint ? (
        <ComplaintEditModal
          complaint={complaint}
          onClose={() => setShowEdit(false)}
          onSaved={refresh}
        />
      ) : null}
    </>
  );
}
