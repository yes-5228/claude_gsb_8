import { useState } from 'react';

import { complaintApi } from '../../api/complaints.js';
import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useDictionaries } from '../../hooks/useDictionaries.js';

export default function ComplaintEditModal({ complaint, onClose, onSaved }) {
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const [form, setForm] = useState({
    source: complaint.source,
    content: complaint.content,
    category: complaint.category,
    contact_name: complaint.contact_name || '',
    contact_phone: complaint.contact_phone || '',
    assignee: complaint.assignee || '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const setValue = (key) => (event) =>
    setForm((prev) => ({ ...prev, [key]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    if (!form.content.trim()) {
      setError('请填写反映内容');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await complaintApi.update(complaint.id, { ...form, content: form.content.trim() });
      toast.success('诉求信息已更新');
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
      title={`编辑诉求 - ${complaint.code}`}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button
            type="submit"
            form="complaint-edit"
            className="btn btn-primary"
            disabled={saving}
          >
            保存
          </button>
        </>
      }
    >
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="complaint-edit" className="form-grid" onSubmit={submit}>
        <Field label="反映来源">
          <select value={form.source} onChange={setValue('source')}>
            {(dictionaries?.complaint_source || []).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="诉求分类">
          <select value={form.category} onChange={setValue('category')}>
            {(dictionaries?.complaint_category || []).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="反映人">
          <input value={form.contact_name} onChange={setValue('contact_name')} />
        </Field>
        <Field label="联系方式">
          <input value={form.contact_phone} onChange={setValue('contact_phone')} />
        </Field>
        <Field label="处理人">
          <input value={form.assignee} onChange={setValue('assignee')} />
        </Field>
        <Field label="反映内容" full>
          <textarea rows="3" value={form.content} onChange={setValue('content')} />
        </Field>
      </form>
    </Modal>
  );
}
