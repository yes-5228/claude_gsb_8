import { useState } from 'react';
import { Link } from 'react-router-dom';

import { complaintApi } from '../../api/complaints.js';
import { restroomApi } from '../../api/restrooms.js';
import DataTable from '../../components/DataTable.jsx';
import Field from '../../components/Field.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import Pagination from '../../components/Pagination.jsx';
import { FollowDueTag, StatusTag } from '../../components/Tags.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { useListQuery } from '../../hooks/useListQuery.js';
import { formatDateTime } from '../../utils/format.js';
import ComplaintFormModal from './ComplaintFormModal.jsx';

const DEFAULT_FILTERS = {
  keyword: '',
  district: '',
  source: '',
  category: '',
  status: '',
  follow_due: '',
};

export default function ComplaintListPage() {
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const [showForm, setShowForm] = useState(false);

  const list = useListQuery((params) => complaintApi.list(params), DEFAULT_FILTERS, 10);
  const { data: districts } = useAsync(() => restroomApi.districts(), []);

  const remove = async (row) => {
    if (!window.confirm(`确认删除诉求「${row.code}」及其办理、回访记录？`)) return;
    try {
      await complaintApi.remove(row.id);
      toast.success('删除成功');
      list.reload();
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <>
      <PageHeader
        title="群众诉求受理"
        description="群众反映与热线转办统一受理：登记 → 分类 → 分派 → 办理 → 回访办结"
        actions={
          <button type="button" className="btn btn-primary" onClick={() => setShowForm(true)}>
            + 受理登记
          </button>
        }
      />
      <div className="content">
        <section className="card">
          <div className="filter-bar">
            <Field label="关键字" full>
              <input
                value={list.filters.keyword}
                placeholder="编号 / 内容 / 反映人 / 电话 / 处理人"
                onChange={(event) => list.updateFilter('keyword', event.target.value)}
              />
            </Field>
            <Field label="诉求来源">
              <select
                value={list.filters.source}
                onChange={(event) => list.updateFilter('source', event.target.value)}
              >
                <option value="">全部</option>
                {(dictionaries?.complaint_source || []).map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
            <Field label="诉求分类">
              <select
                value={list.filters.category}
                onChange={(event) => list.updateFilter('category', event.target.value)}
              >
                <option value="">全部</option>
                {(dictionaries?.complaint_category || []).map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
            <Field label="办理状态">
              <select
                value={list.filters.status}
                onChange={(event) => list.updateFilter('status', event.target.value)}
              >
                <option value="">全部</option>
                {(dictionaries?.complaint_status || []).map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
            <Field label="所属区域">
              <select
                value={list.filters.district}
                onChange={(event) => list.updateFilter('district', event.target.value)}
              >
                <option value="">全部</option>
                {(districts || []).map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
            <Field label="回访提醒">
              <select
                value={list.filters.follow_due}
                onChange={(event) => list.updateFilter('follow_due', event.target.value)}
              >
                <option value="">全部</option>
                <option value="true">已到时待再次回访</option>
              </select>
            </Field>
            <button type="button" className="btn" onClick={list.resetFilters}>
              重置
            </button>
          </div>
        </section>

        <section className="card">
          <DataTable
            loading={list.loading}
            error={list.error}
            rows={list.items}
            emptyText="暂无诉求记录"
            columns={[
              { key: 'code', title: '编号' },
              {
                key: 'content',
                title: '反映内容',
                wrap: true,
                render: (row) => (
                  <Link to={`/complaints/${row.id}`}>
                    {row.content.length > 32 ? `${row.content.slice(0, 32)}…` : row.content}
                  </Link>
                ),
              },
              { key: 'source', title: '来源' },
              { key: 'category', title: '分类' },
              {
                key: 'restroom',
                title: '涉及公厕',
                render: (row) =>
                  row.restroom ? (
                    <Link to={`/restrooms/${row.restroom.id}`}>{row.restroom.name}</Link>
                  ) : (
                    '-'
                  ),
              },
              {
                key: 'reporter',
                title: '反映人',
                render: (row) => (
                  <span>
                    {row.reporter_name || '匿名'}
                    <br />
                    <span className="muted">{row.reporter_phone}</span>
                  </span>
                ),
              },
              { key: 'handler', title: '处理人', render: (row) => row.handler || '未分派' },
              {
                key: 'status',
                title: '状态',
                render: (row) => (
                  <span className="inline">
                    <StatusTag status={row.status} />
                    <FollowDueTag nextFollowTime={row.next_follow_time} status={row.status} />
                  </span>
                ),
              },
              {
                key: 'received_at',
                title: '受理时间',
                render: (row) => formatDateTime(row.received_at),
              },
              {
                key: 'actions',
                title: '操作',
                render: (row) => (
                  <div className="inline">
                    <Link className="btn-link" to={`/complaints/${row.id}`}>
                      详情 / 办理
                    </Link>
                    <button type="button" className="btn-link danger" onClick={() => remove(row)}>
                      删除
                    </button>
                  </div>
                ),
              },
            ]}
          />
          <Pagination meta={list.meta} onPageChange={list.setPage} />
        </section>
      </div>

      {showForm ? (
        <ComplaintFormModal onClose={() => setShowForm(false)} onSaved={list.reload} />
      ) : null}
    </>
  );
}
