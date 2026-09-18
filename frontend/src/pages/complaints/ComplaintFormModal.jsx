import { useEffect, useRef, useState } from 'react';

import { complaintApi } from '../../api/complaints.js';
import { metaApi } from '../../api/meta.js';
import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { toDateTimeInput } from '../../utils/format.js';

const AUTO_CATEGORY = '';

export default function ComplaintFormModal({ complaint, onClose, onSaved }) {
  const editing = Boolean(complaint);
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const [restrooms, setRestrooms] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [autoCategory, setAutoCategory] = useState(null);
  const [form, setForm] = useState({
    restroom_id: complaint?.restroom_id ?? '',
    source: complaint?.source ?? '群众反映',
    content: complaint?.content ?? '',
    category: complaint?.category ?? AUTO_CATEGORY,
    reporter_name: complaint?.reporter_name ?? '',
    reporter_phone: complaint?.reporter_phone ?? '',
    receiver: complaint?.receiver ?? '',
    received_at: complaint ? toDateTimeInput(complaint.received_at) : toDateTimeInput(new Date()),
    initial_remark: '',
  });
  const classifyTimer = useRef(null);

  useEffect(() => {
    metaApi
      .restroomOptions()
      .then(setRestrooms)
      .catch((err) => setError(err.message));
  }, []);

  // 分类选择「自动判定」时，根据反映内容实时预判分类（防抖 400ms）
  useEffect(() => {
    if (editing || form.category !== AUTO_CATEGORY || !form.content.trim()) {
      setAutoCategory(null);
      return undefined;
    }
    classifyTimer.current = setTimeout(() => {
      complaintApi
        .classify(form.content.trim())
        .then((data) => setAutoCategory(data.category))
        .catch(() => setAutoCategory(null));
    }, 400);
    return () => clearTimeout(classifyTimer.current);
  }, [form.content, form.category, editing]);

  const setValue = (key) => (event) =>
    setForm((prev) => ({ ...prev, [key]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    if (!form.content.trim()) {
      setError('请填写反映内容');
      return;
    }
    if (!form.reporter_phone.trim()) {
      setError('请填写联系方式，便于办结后回访');
      return;
    }
    if (!editing && !form.restroom_id) {
      setError('请选择涉及公厕');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (editing) {
        await complaintApi.update(complaint.id, {
          source: form.source,
          content: form.content.trim(),
          category: form.category || null,
          reporter_name: form.reporter_name.trim(),
          reporter_phone: form.reporter_phone.trim(),
          receiver: form.receiver.trim(),
        });
        toast.success('登记信息已更新');
      } else {
        await complaintApi.create({
          restroom_id: Number(form.restroom_id),
          source: form.source,
          content: form.content.trim(),
          category: form.category || null,
          reporter_name: form.reporter_name.trim(),
          reporter_phone: form.reporter_phone.trim(),
          receiver: form.receiver.trim(),
          received_at: form.received_at ? new Date(form.received_at).toISOString() : null,
          initial_remark: form.initial_remark || null,
        });
        toast.success('诉求已受理登记，等待分派处理');
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title={editing ? `补正登记信息 - ${complaint.code}` : '诉求受理登记'}
      onClose={onClose}
      width={780}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button type="submit" form="complaint-form" className="btn btn-primary" disabled={saving}>
            {saving ? '提交中...' : editing ? '保存修改' : '确认受理'}
          </button>
        </>
      }
    >
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="complaint-form" className="form-grid" onSubmit={submit}>
        <Field label="诉求来源 *">
          <select value={form.source} onChange={setValue('source')}>
            {(dictionaries?.complaint_source || []).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="受理时间">
          <input
            type="datetime-local"
            value={form.received_at}
            onChange={setValue('received_at')}
            disabled={editing}
          />
        </Field>
        {!editing ? (
          <Field label="涉及公厕 *" full>
            <select value={form.restroom_id} onChange={setValue('restroom_id')}>
              <option value="">请选择公厕</option>
              {restrooms.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.code} {item.name}（{item.district}）
                </option>
              ))}
            </select>
          </Field>
        ) : null}
        <Field label="反映内容 *" full>
          <textarea
            rows="3"
            value={form.content}
            onChange={setValue('content')}
            placeholder="如实记录群众反映的问题与诉求，分类将按内容自动判定"
          />
        </Field>
        <Field
          label="诉求分类"
          hint={
            !editing && form.category === AUTO_CATEGORY && autoCategory
              ? `按内容自动判定为「${autoCategory}」，可手动调整`
              : '留空则按反映内容自动判定'
          }
        >
          <select value={form.category} onChange={setValue('category')}>
            <option value={AUTO_CATEGORY}>自动判定（按内容）</option>
            {(dictionaries?.complaint_category || []).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="受理人">
          <input value={form.receiver} onChange={setValue('receiver')} placeholder="值班坐席 / 受理人员" />
        </Field>
        <Field label="反映人姓名">
          <input
            value={form.reporter_name}
            onChange={setValue('reporter_name')}
            placeholder="可匿名"
          />
        </Field>
        <Field label="联系方式 *" hint="用于办结后回访反映人">
          <input
            value={form.reporter_phone}
            onChange={setValue('reporter_phone')}
            placeholder="手机或座机号码"
          />
        </Field>
        {!editing ? (
          <Field label="受理备注" full>
            <textarea
              rows="2"
              value={form.initial_remark}
              onChange={setValue('initial_remark')}
              placeholder="将记录在办理轨迹的首条节点"
            />
          </Field>
        ) : null}
      </form>
    </Modal>
  );
}
