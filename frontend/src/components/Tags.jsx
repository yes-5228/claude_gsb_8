import { isFollowDue, isOverdue, scoreTone, severityTone, statusTone } from '../utils/format.js';

export function StatusTag({ status }) {
  return <span className={`tag ${statusTone(status)}`}>{status}</span>;
}

export function SeverityTag({ severity }) {
  return <span className={`tag ${severityTone(severity)}`}>{severity}</span>;
}

export function ScorePill({ score }) {
  return <span className={`score-pill ${scoreTone(score)}`}>{Number(score).toFixed(1)}</span>;
}

export function OverdueTag({ deadline, status }) {
  if (!isOverdue(deadline, status)) return null;
  return <span className="tag tag-danger">已超期</span>;
}

/** 到了约定的再次回访时间仍未回访的提醒标签。 */
export function FollowDueTag({ nextFollowTime, status }) {
  if (!isFollowDue(nextFollowTime, status)) return null;
  return <span className="tag tag-danger">待再次回访</span>;
}

export function FollowUpResultTag({ result }) {
  return (
    <span className={`tag ${result === '已联系上' ? 'tag-success' : 'tag-danger'}`}>{result}</span>
  );
}

export function GradeTag({ grade }) {
  const tone =
    grade === '优秀'
      ? 'tag-success'
      : grade === '良好'
        ? 'tag-primary'
        : grade === '合格'
          ? 'tag-warning'
          : 'tag-danger';
  return <span className={`tag ${tone}`}>{grade || '未评级'}</span>;
}
