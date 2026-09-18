import { useState } from 'react';

import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { formatDateTime, toDateTimeInput } from '../../utils/format.js';

/** 回访登记：联系上则办结；未联系上需约定下次回访时间，安排再次回访。 */
export default function ComplaintFollowUpModal({ complaint, saving, onClose, onSubmit }) {
  const { dictionaries } = useDictionaries();
  const [form, setForm] = useState({
    result: '已联系上',
    satisfaction: '满意',
    next_follow_time: '',
    operator: '',
    remark: '',
  });
  const [error, setError] = useState(null);

  const setValue = (key) => (event) =>
    setForm((prev) => ({ ...prev, [key]: event.target.value }));

  const reached = form.result === '已联系上';

  const submit = (event) => {
    event.preventDefault();
    if (!operatorValid()) return;
    if (!reached && !form.next_follow_time) {
      setError('未联系上反映人，请约定下次回访时间以安排再次回访');
      return;
    }
    setError(null);
    onSubmit({
      result: form.result,
      satisfaction: reached ? form.satisfaction : null,
      next_follow_time:
        !reached && form.next_follow_time ? new Date(form.next_follow_time).toISOString() : null,
      operator: form.operator.trim(),
      remark: form.remark.trim() || null,
    });
  };

  const operatorValid = () => {
    if (!form.operator.trim()) {
      setError('请填写回访人');
      return false;
    }
    return true;
  };

  return (
    <Modal
      title={`回访登记 - ${complaint.code}`}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button type="submit" form="complaint-follow-up" className="btn btn-primary" disabled={saving}>
            {saving ? '提交中...' : '提交回访结果'}
          </button>
        </>
      }
    >
      <div className="alert alert-info">
        回访对象：{complaint.reporter_name || '匿名'}（{complaint.reporter_phone}）
        {complaint.next_follow_time
          ? ` · 约定再次回访：${formatDateTime(complaint.next_follow_time)}`
          : ''}
      </div>
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="complaint-follow-up" className="form-grid" onSubmit={submit}>
        <Field label="回访结果 *">
          <select value={form.result} onChange={setValue('result')}>
            {(dictionaries?.follow_up_result || []).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        {reached ? (
          <Field label="反映人满意度">
            <select value={form.satisfaction} onChange={setValue('satisfaction')}>
              {(dictionaries?.follow_up_satisfaction || []).map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </Field>
        ) : (
          <Field label="下次回访时间 *" hint="登记后将安排再次回访">
            <input
              type="datetime-local"
              value={form.next_follow_time}
              min={toDateTimeInput(new Date())}
              onChange={setValue('next_follow_time')}
            />
          </Field>
        )}
        <Field label="回访人 *">
          <input
            value={form.operator}
            onChange={setValue('operator')}
            placeholder="如：回访员小周"
          />
        </Field>
        <Field label="回访备注" full>
          <textarea
            rows="2"
            value={form.remark}
            onChange={setValue('remark')}
            placeholder={
              reached ? '如：反映人确认问题已解决' : '如：电话无人接听，约定明日再次联系'
            }
          />
        </Field>
      </form>
    </Modal>
  );
}
