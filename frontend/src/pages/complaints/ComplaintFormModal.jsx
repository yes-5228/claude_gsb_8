import { useEffect, useState } from 'react';

import { complaintApi } from '../../api/complaints.js';
import { metaApi } from '../../api/meta.js';
import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useDictionaries } from '../../hooks/useDictionaries.js';

export default function ComplaintFormModal({ onClose, onSaved }) {
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const [restrooms, setRestrooms] = useState([]);
  const [saving, setSaving] = useState(false);
  const [classifying, setClassifying] = useState(false);
  const [error, setError] = useState(null);
  const [matched, setMatched] = useState([]);
  // 用户手动改过分类后不再自动判定，避免覆盖人工选择
  const [categoryTouched, setCategoryTouched] = useState(false);
  const [form, setForm] = useState({
    restroom_id: '',
    source: '热线电话',
    content: '',
    category: '',
    contact_name: '',
    contact_phone: '',
    assignee: '',
    initial_remark: '',
  });

  useEffect(() => {
    metaApi
      .restroomOptions()
      .then(setRestrooms)
      .catch((err) => setError(err.message));
  }, []);

  const setValue = (key) => (event) =>
    setForm((prev) => ({ ...prev, [key]: event.target.value }));

  const classify = async (content) => {
    if (!content.trim()) return;
    setClassifying(true);
    try {
      const result = await complaintApi.classify(content.trim());
      setForm((prev) => ({ ...prev, category: result.category }));
      setMatched(result.matched || []);
    } catch {
      // 智能判定失败不阻塞登记，可手动选择分类
    } finally {
      setClassifying(false);
    }
  };

  // 内容填写完成（失焦）且未手动选过分类时，自动按内容判定
  const handleContentBlur = () => {
    if (!categoryTouched) classify(form.content);
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!form.restroom_id) {
      setError('请选择涉及公厕');
      return;
    }
    if (!form.content.trim()) {
      setError('请填写反映内容');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await complaintApi.create({
        restroom_id: Number(form.restroom_id),
        source: form.source,
        content: form.content.trim(),
        category: form.category || null,
        contact_name: form.contact_name.trim(),
        contact_phone: form.contact_phone.trim(),
        assignee: form.assignee.trim(),
        initial_remark: form.initial_remark.trim() || null,
      });
      toast.success('已受理登记，等待分派处理');
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
      title="群众反映受理登记"
      onClose={onClose}
      width={780}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button
            type="submit"
            form="complaint-form"
            className="btn btn-primary"
            disabled={saving}
          >
            {saving ? '提交中...' : '受理登记'}
          </button>
        </>
      }
    >
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="complaint-form" className="form-grid" onSubmit={submit}>
        <Field label="涉及公厕 *">
          <select value={form.restroom_id} onChange={setValue('restroom_id')}>
            <option value="">请选择公厕</option>
            {restrooms.map((item) => (
              <option key={item.id} value={item.id}>
                {item.code} {item.name}（{item.district}）
              </option>
            ))}
          </select>
        </Field>
        <Field label="反映来源">
          <select value={form.source} onChange={setValue('source')}>
            {(dictionaries?.complaint_source || []).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="反映内容 *" full hint="填写完成离开输入框后自动判定分类">
          <textarea
            rows="3"
            value={form.content}
            onChange={setValue('content')}
            onBlur={handleContentBlur}
            placeholder="如：群众反映厕内地面脏污、垃圾清运不及时"
          />
        </Field>
        <Field
          label="诉求分类"
          hint={matched.length ? `命中关键词：${matched.join('、')}` : '留空由系统按内容判定'}
        >
          <div className="inline">
            <select
              value={form.category}
              onChange={(event) => {
                setCategoryTouched(true);
                setValue('category')(event);
              }}
            >
              <option value="">自动判定</option>
              {(dictionaries?.complaint_category || []).map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
            <button
              type="button"
              className="btn btn-sm"
              disabled={classifying || !form.content.trim()}
              onClick={() => {
                setCategoryTouched(false);
                classify(form.content);
              }}
            >
              {classifying ? '判定中...' : '智能判定'}
            </button>
          </div>
        </Field>
        <Field label="处理人" hint="可先登记，受理分派时再指定">
          <input
            value={form.assignee}
            onChange={setValue('assignee')}
            placeholder="保洁班组 / 责任人"
          />
        </Field>
        <Field label="反映人">
          <input
            value={form.contact_name}
            onChange={setValue('contact_name')}
            placeholder="匿名可留空"
          />
        </Field>
        <Field label="联系方式" hint="用于办结后回访">
          <input
            value={form.contact_phone}
            onChange={setValue('contact_phone')}
            placeholder="电话 / 微信等"
          />
        </Field>
        <Field label="受理备注" full>
          <textarea
            rows="2"
            value={form.initial_remark}
            onChange={setValue('initial_remark')}
            placeholder="将记录在办理轨迹的首条节点"
          />
        </Field>
      </form>
    </Modal>
  );
}
