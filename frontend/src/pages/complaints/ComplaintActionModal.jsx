import { useState } from 'react';

import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { StatusTag } from '../../components/Tags.jsx';

const PLACEHOLDER = {
  处理中: '填写分派安排，如：已分派街办保洁队现场核实',
  待回访: '填写办理情况说明，如：已现场处理完毕',
  已关闭: '填写关闭原因，如：重复反映，并入其他工单',
};

export default function ComplaintActionModal({ option, complaint, onClose, onSubmit, saving }) {
  const [operator, setOperator] = useState(complaint.assignee || '');
  const [remark, setRemark] = useState('');
  const [result, setResult] = useState(complaint.result || '');
  const [error, setError] = useState(null);

  // 办结待回访必须登记处理结果，供回访时向反映人反馈
  const needResult = option.status === '待回访';

  const submit = (event) => {
    event.preventDefault();
    if (!operator.trim()) return;
    if (needResult && !result.trim()) {
      setError('办结前请填写处理结果');
      return;
    }
    setError(null);
    onSubmit({
      to_status: option.status,
      operator: operator.trim(),
      remark: remark || null,
      result: needResult ? result.trim() : null,
    });
  };

  return (
    <Modal
      title={`办理 - ${option.action}`}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button
            type="submit"
            form="complaint-action"
            className="btn btn-primary"
            disabled={saving}
          >
            {saving ? '提交中...' : '确认提交'}
          </button>
        </>
      }
    >
      <div className="alert alert-info">
        当前状态 <StatusTag status={complaint.status} /> 变更为 <StatusTag status={option.status} />
      </div>
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="complaint-action" className="form-grid" onSubmit={submit}>
        <Field label="操作人 *">
          <input
            value={operator}
            onChange={(event) => setOperator(event.target.value)}
            placeholder="如：街办保洁队"
          />
        </Field>
        {needResult ? (
          <Field label="处理结果 *" full hint="办结后回访时将向反映人反馈该结果">
            <textarea
              rows="3"
              value={result}
              onChange={(event) => setResult(event.target.value)}
              placeholder="如：已补充厕纸与洗手液，现场复查合格"
            />
          </Field>
        ) : null}
        <Field label="办理说明" full>
          <textarea
            rows="3"
            value={remark}
            onChange={(event) => setRemark(event.target.value)}
            placeholder={PLACEHOLDER[option.status] || '填写本次办理说明'}
          />
        </Field>
      </form>
    </Modal>
  );
}
