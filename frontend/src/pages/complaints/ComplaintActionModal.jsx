import { useState } from 'react';

import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { StatusTag } from '../../components/Tags.jsx';

const MODE_CONFIG = {
  assign: {
    title: '分派处理人',
    submitText: '确认分派',
    handlerLabel: '处理人 *',
    handlerPlaceholder: '如：保洁班组张伟',
    remarkPlaceholder: '填写分派说明，如：请今日内到场处理',
  },
  reassign: {
    title: '改派处理人',
    submitText: '确认改派',
    handlerLabel: '新处理人 *',
    handlerPlaceholder: '如：维修班李师傅',
    remarkPlaceholder: '填写改派原因',
  },
  finish: {
    title: '登记处理结果',
    submitText: '提交并转入回访',
    remarkPlaceholder: '补充说明，如：已联系配件商更换损坏部件',
  },
  close: {
    title: '作废关闭',
    submitText: '确认关闭',
    remarkPlaceholder: '填写关闭原因，如：重复反映，与 SQ-xxx 合并办理',
  },
};

/** 分派 / 改派 / 登记处理结果 / 作废关闭 共用的办理弹窗。 */
export default function ComplaintActionModal({ mode, complaint, saving, onClose, onSubmit }) {
  const config = MODE_CONFIG[mode];
  const [handler, setHandler] = useState(complaint.handler || '');
  const [result, setResult] = useState('');
  const [operator, setOperator] = useState('');
  const [remark, setRemark] = useState('');
  const [error, setError] = useState(null);

  const submit = (event) => {
    event.preventDefault();
    if ((mode === 'assign' || mode === 'reassign') && !handler.trim()) {
      setError('请填写处理人');
      return;
    }
    if (mode === 'finish' && !result.trim()) {
      setError('请填写处理结果');
      return;
    }
    if (!operator.trim()) {
      setError('请填写操作人');
      return;
    }
    setError(null);
    onSubmit({
      handler: handler.trim(),
      result: result.trim(),
      operator: operator.trim(),
      remark: remark.trim() || null,
    });
  };

  return (
    <Modal
      title={`${config.title} - ${complaint.code}`}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button
            type="submit"
            form="complaint-action"
            className={`btn${mode === 'close' ? ' btn-danger' : ' btn-primary'}`}
            disabled={saving}
          >
            {saving ? '提交中...' : config.submitText}
          </button>
        </>
      }
    >
      <div className="alert alert-info">
        当前状态 <StatusTag status={complaint.status} />
        {mode === 'assign' ? '，分派后进入「处理中」' : null}
        {mode === 'finish' ? '，登记结果后进入「待回访」' : null}
        {mode === 'close' ? '，关闭后流程终止，请谨慎操作' : null}
      </div>
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="complaint-action" className="form-grid" onSubmit={submit}>
        {mode === 'assign' || mode === 'reassign' ? (
          <Field label={config.handlerLabel}>
            <input
              value={handler}
              onChange={(event) => setHandler(event.target.value)}
              placeholder={config.handlerPlaceholder}
            />
          </Field>
        ) : null}
        {mode === 'finish' ? (
          <Field label="处理结果 *" full>
            <textarea
              rows="3"
              value={result}
              onChange={(event) => setResult(event.target.value)}
              placeholder="如：已更换损坏水龙头，现场恢复正常使用"
            />
          </Field>
        ) : null}
        <Field label="操作人 *">
          <input
            value={operator}
            onChange={(event) => setOperator(event.target.value)}
            placeholder="如：值班长 / 处理人姓名"
          />
        </Field>
        <Field label={mode === 'close' ? '关闭原因' : '办理说明'} full>
          <textarea
            rows="2"
            value={remark}
            onChange={(event) => setRemark(event.target.value)}
            placeholder={config.remarkPlaceholder}
          />
        </Field>
      </form>
    </Modal>
  );
}
